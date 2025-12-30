import asyncio
from typing import Dict, Any, List, Tuple
from .schemas import Workflow, NodeConfig, Edge

from .node_registry import registry
from pocketflow import Flow, Node
from .nodes.base import BasePlatformNode

class BranchNode(BasePlatformNode, Node):
    """
    A special node that executes multiple successor nodes in parallel.
    Used by the engine to support branching in PocketFlow.
    """
    NODE_TYPE = "branch_wrapper"
    
    def __init__(self, successors_list: List[Node]):
        super().__init__()
        self.nodes_to_run = successors_list
        self.name = "branch_wrapper"
        
    def prep(self, shared):
        return shared
        
    def exec(self, prep_res):
        # In a real parallel engine we might use threads, 
        # but for PocketFlow we can just run them sequentially 
        # as they share the same 'shared' state.
        for node in self.nodes_to_run:
            # We create a mini-flow for each branch to ensure 
            # its successors are also executed correctly.
            flow = Flow(node)
            flow.run(prep_res)
        return "branch_complete"

    def post(self, shared, prep_res, exec_res):
        # We don't want to store 'branch_complete' in results keys
        # as it's a wrapper.
        return None

def build_graph(workflow: Workflow, event_callback=None):
    # Mapping from Node ID (frontend) to PocketFlow Node instance
    pf_nodes = {}
    
    # 1. Instantiate Nodes
    for node_config in workflow.nodes:
        node_class = registry.get_node_class(node_config.type)
        if not node_class:
            print(f"Warning: Node type {node_config.type} not found.")
            continue
            
        pf_node = node_class()
        # Use .config to store static parameters
        pf_node.config = node_config.data 
        pf_node.name = node_config.label or node_config.id
        # Inject metadata for visualization
        pf_node.id = node_config.id 
        pf_node.on_event = event_callback
        
        print(f"DEBUG: Created node {pf_node.name} (ID: {node_config.id})")
        
        pf_nodes[node_config.id] = pf_node

    # Pre-collect successors to detect branching
    successors_map = {} # (source_id, edge_name) -> List[target_node]

    # 2. Collect Connection Info
    for edge in workflow.edges:
        source_node = pf_nodes.get(edge.source)
        target_node = pf_nodes.get(edge.target)
        
        if source_node and target_node:
            # Extract edge name from sourceHandle (format: "out-{edge_name}")
            edge_name = "default"
            if edge.sourceHandle and edge.sourceHandle.startswith("out-"):
                edge_name = edge.sourceHandle[4:]  # Remove "out-" prefix
            
            key = (edge.source, edge_name)
            if key not in successors_map:
                successors_map[key] = []
            successors_map[key].append(target_node)

            # Record handle mapping for the target node
            target_handle = edge.targetHandle or "in-default"
            if target_handle.startswith("in-"):
                target_handle = target_handle[3:] # Remove "in-" prefix
            
            if not hasattr(target_node, 'input_mapping'):
                target_node.input_mapping = {}
            target_node.input_mapping[target_handle] = source_node.name

    # 3. Apply Connections
    for (source_id, edge_name), targets in successors_map.items():
        source_node = pf_nodes[source_id]
        
        if len(targets) == 1:
            # Single successor - standard PocketFlow
            if edge_name == "default":
                source_node >> targets[0]
            else:
                (source_node - edge_name) >> targets[0]
        else:
            # Multiple successors - wrap in BranchNode
            branch_wrapper = BranchNode(targets)
            if edge_name == "default":
                source_node >> branch_wrapper
            else:
                (source_node - edge_name) >> branch_wrapper

    # Find roots
    in_degree = {uid: 0 for uid in pf_nodes}
    for edge in workflow.edges:
        if edge.target in in_degree:
            in_degree[edge.target] += 1
            
    roots = [pf_nodes[uid] for uid, deg in in_degree.items() if deg == 0]
    
    if not roots:
         return None, "No start node found (cyclic or empty?)"
         
    flow = Flow(roots[0] if len(roots) == 1 else roots)
    
    return flow, None

async def run_workflow(workflow: Workflow, event_callback=None):
    
    flow, error = build_graph(workflow, event_callback)
    if error:
        raise Exception(error)
    
    if not flow:
         raise Exception("Could not build flow")

    print(f"Running workflow with {len(workflow.nodes)} nodes")
    
    # Run sync for now
    try:
        shared_state = {}
        await asyncio.to_thread(flow.run, shared_state)
        
        results = shared_state.get("results", {})
        return {"status": "completed", "results": results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Execution Error: {e}")
        return {"status": "error", "error": str(e)}

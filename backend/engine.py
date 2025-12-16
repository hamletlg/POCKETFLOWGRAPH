import asyncio
from typing import Dict, Any, List, Tuple
from .schemas import Workflow, NodeConfig, Edge
from .node_registry import registry
from pocketflow import Flow

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
        pf_node.name = node_config.data.get("label", node_config.id)
        # Inject metadata for visualization
        pf_node.id = node_config.id 
        pf_node.on_event = event_callback
        
        print(f"DEBUG: Created node {pf_node.name} (ID: {node_config.id})")
        
        pf_nodes[node_config.id] = pf_node

    # 2. Connect Edges
    for edge in workflow.edges:
        source_node = pf_nodes.get(edge.source)
        target_node = pf_nodes.get(edge.target)
        
        if source_node and target_node:
            # Extract edge name from sourceHandle (format: "out-{edge_name}")
            edge_name = "default"
            if edge.sourceHandle and edge.sourceHandle.startswith("out-"):
                edge_name = edge.sourceHandle[4:]  # Remove "out-" prefix
            
            if edge_name == "default":
                source_node >> target_node
            else:
                # Use named transition: source_node - "edge_name" >> target_node
                (source_node - edge_name) >> target_node
            
            print(f"DEBUG: Connected {edge.source} --[{edge_name}]--> {edge.target}")
            
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

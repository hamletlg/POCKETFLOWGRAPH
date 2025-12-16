import asyncio
from typing import Dict, Any, List, Tuple
from .schemas import Workflow, NodeConfig, Edge
from .node_registry import registry

def build_graph(workflow: Workflow):
    # Mapping from Node ID (frontend) to PocketFlow Node instance
    pf_nodes = {}
    
    # 1. Instantiate Nodes
    for node_config in workflow.nodes:
        node_class = registry.get_node_class(node_config.type)
        if not node_class:
            print(f"Warning: Node type {node_config.type} not found.")
            continue
            
        # Instantiate
        # Note: PocketFlow nodes usually take (prep, exec, post) or are subclassed.
        # Our BasePlatformNode subclasses are proper Node subclasses.
        # We need to inject params. 
        # PocketFlow nodes don't typically take params in __init__ unless designed to.
        # Let's assume we pass params to the instance or set them.
        
        # Check if the class accepts params in init or we just set attribute
        # For now, let's assume we can set .params on the instance
        
        pf_node = node_class()
        # Use .config to store static parameters, as .params is overwritten by PocketFlow
        pf_node.config = node_config.data 
        pf_node.name = node_config.data.get("label", node_config.id)
        
        print(f"DEBUG: Created node {pf_node.name} (ID: {node_config.id}) with config: {pf_node.config}")
        
        pf_nodes[node_config.id] = pf_node

    # 2. Connect Edges
    # PocketFlow uses node1 >> node2 or node1.add_target(node2)
    # But wait, PocketFlow is usually functional: Flow(start_node)
    # We need to construct the flow.
    
    start_nodes = []
    
    for edge in workflow.edges:
        source_node = pf_nodes.get(edge.source)
        target_node = pf_nodes.get(edge.target)
        
        if source_node and target_node:
            # Connect
            # PocketFlow: source >> target
            source_node >> target_node
            
    # Identify connection-less nodes or explicit start nodes as flow starts?
    # For now, find nodes that are not targets?
    # Or just use "start" type nodes
    
    starts = [n for uid, n in pf_nodes.items() if workflow.nodes[int(uid.split('_')[-1]) if uid.startswith('dndnode_') else 0].type == 'start'] if any(n.type == 'start' for n in workflow.nodes) else []
    
    # If no explicit start node, maybe find roots (nodes with no incoming edges)
    # Calculate in-degrees
    in_degree = {uid: 0 for uid in pf_nodes}
    for edge in workflow.edges:
        if edge.target in in_degree:
            in_degree[edge.target] += 1
            
    roots = [pf_nodes[uid] for uid, deg in in_degree.items() if deg == 0]
    
    # Create Flow
    if not roots:
         return None, "No start node found (cyclic or empty?)"
         
    
    # Only use the first root for now, or Flow(roots)
    flow = Flow(roots[0] if len(roots) == 1 else roots)
    
    return flow, None

async def run_workflow(workflow: Workflow):
    
    flow, error = build_graph(workflow)
    if error:
        raise Exception(error)
    
    if not flow:
         raise Exception("Could not build flow")

    print(f"Running workflow with {len(workflow.nodes)} nodes")
    
    # Run sync for now
    try:
        # Run sync for now
        # flow.run returns the final shared state
        # Create shared state explicitly to retain reference if run returns None
        shared_state = {}
        # We don't rely on return value as much as the side effect on shared_state
        await asyncio.to_thread(flow.run, shared_state)
        
        results = shared_state.get("results", {})
        return {"status": "completed", "results": results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Execution Error: {e}")
        return {"status": "error", "error": str(e)}

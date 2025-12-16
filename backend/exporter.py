from .schemas import Workflow
from .node_registry import registry
import inspect

def generate_script(workflow: Workflow) -> str:
    # 1. Collect Imports
    # We need to import classes used in the workflow
    # registry.node_classes maps "type" -> Class
    
    used_types = set(n.type for n in workflow.nodes)
    imports = set()
    
    # Always import Flow
    imports.add("from pocketflow import Flow")
    
    for type_name in used_types:
        cls = registry.get_node_class(type_name)
        if cls:
            # Get the module name where cls is defined
            module = cls.__module__
            # If it's a builtin pocketflow node, module might be 'pocketflow.core...'
            # If it's our custom node, it's 'backend.nodes...'
            # User running the script might not have 'backend' package structure if they move the script.
            # But we are exporting for "standalone" execution assuming dependencies are met.
            # If we export to run *within* the project context, `from backend.nodes...` works.
            # If we want truly standalone, we assume they have the source code or installed package.
            # Let's assume they run it in the project root.
            name = cls.__name__
            imports.add(f"from {module} import {name}")
            
    script = []
    # Add Imports
    script.append("# Auto-generated PocketFlow Script")
    script.append("\n".join(sorted(list(imports))))
    script.append("\n")
    
    script.append("def main():")
    
    # 2. Instantiate Nodes
    # Map frontend ID to variable name
    id_to_var = {}
    
    for i, node in enumerate(workflow.nodes):
        var_name = f"node_{i}_{node.id.replace('-', '_')}"
        id_to_var[node.id] = var_name
        
        cls = registry.get_node_class(node.type)
        class_name = cls.__name__ if cls else "UnknownNode"
        
        # Params
        # We need to pass params. Simple types can be repr()
        # Some params might be in .data, others?
        # Our `exec` uses `self.config` or similar.
        # If the class accepts args in init, we pass them.
        # Our BasePlatformNode usually doesn't take init args for config.
        # We might need to set them after instantiation.
        
        script.append(f"    # Node: {node.label} ({node.type})")
        script.append(f"    {var_name} = {class_name}()")
        
        if node.data:
             # We assume our nodes use a .config attribute or we set attributes dynamically
             # To be safe and generic: let's set .config if it's a BasePlatformNode
             # or just comments if we don't know.
             # In `engine.py`, we did `pf_node.config = node_config.data`.
             # We should replicate that pattern.
             script.append(f"    {var_name}.config = {repr(node.data)}")
             
        script.append("")

    # 3. Connect Edges
    script.append("    # Connections")
    for edge in workflow.edges:
        src = id_to_var.get(edge.source)
        tgt = id_to_var.get(edge.target)
        if src and tgt:
            script.append(f"    {src} >> {tgt}")
            
    # 4. Create Flow
    # Find start nodes
    starts = [n for n in workflow.nodes if n.type == 'start']
    if starts:
        start_vars = [id_to_var[n.id] for n in starts]
        if len(start_vars) == 1:
            script.append(f"\n    flow = Flow({start_vars[0]})")
        else:
            script.append(f"\n    flow = Flow([{', '.join(start_vars)}])")
    else:
        # Fallback to first node or roots
         script.append(f"\n    # Warning: No start node found, using first node")
         if workflow.nodes:
             script.append(f"    flow = Flow({id_to_var[workflow.nodes[0].id]})")
         else:
             script.append("    flow = None")

    script.append("\n    if flow:")
    script.append("        print('Running flow...')")
    script.append("        shared = {}")
    script.append("        flow.run(shared)")
    script.append("        print('Results:', shared.get('results'))")
    
    script.append("\nif __name__ == '__main__':")
    script.append("    main()")
    
    return "\n".join(script)

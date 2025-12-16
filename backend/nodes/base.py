from pocketflow import Node, BatchNode, AsyncNode
from pydantic import BaseModel
from typing import List, Dict, Any, Type, Optional

class NodeSchema(BaseModel):
    type: str
    description: str
    inputs: List[str] = ["default"]
    outputs: List[str] = ["default"]
    params: Dict[str, str] = {} # param_name: type (string, int, boolean)

class BasePlatformNode:
    """Mixin to add platform metadata to PocketFlow nodes"""
    NODE_TYPE = "base"
    DESCRIPTION = "Base Node"
    INPUTS = ["default"]
    OUTPUTS = ["default"]
    PARAMS = {} # Example: {"prompt": "string", "retries": "int"}

    @classmethod
    def get_schema(cls) -> NodeSchema:
        return NodeSchema(
            type=cls.NODE_TYPE,
            description=cls.DESCRIPTION,
            inputs=cls.INPUTS,
            outputs=cls.OUTPUTS,
            params=cls.PARAMS
        )

    def run(self, shared):
        node_id = getattr(self, 'id', 'unknown')
        callback = getattr(self, 'on_event', None)
        
        print(f"DEBUG BasePlatformNode.run: node_id={node_id}, has_callback={callback is not None}")
        
        if callback:
            import asyncio
            # Call callback somewhat correctly. 
            # If callback is async? Our engine calls run in a thread usually.
            # But the callback (broadcast) is async.
            # If run is synchronous, we can't await easily.
            # But we are running in `asyncio.to_thread` in engine.
            # So we perform a blocking call to the async callback? No.
            # We usually need an event loop.
            # Valid approach: pass a synchronous wrapper that schedules the task on the loop.
            try:
                print(f"DEBUG: Calling callback for node_start: {node_id}")
                callback("node_start", {"node_id": node_id})
            except Exception as e:
                print(f"Callback error: {e}")

        try:
            prep_res = self.prep(shared)
            exec_res = self.exec(prep_res)
            res = self.post(shared, prep_res, exec_res)
            
            if callback:
                try:
                    print(f"DEBUG: Calling callback for node_end: {node_id}")
                    callback("node_end", {"node_id": node_id})
                except Exception as e:
                    print(f"Callback error: {e}")
            
            return res
        except Exception as e:
            if callback:
                 try:
                    callback("node_error", {"node_id": node_id, "error": str(e)})
                 except: 
                     pass
            raise e

    def post(self, shared, prep_res, exec_res):
        print(f"DEBUG: Executing post for {getattr(self, 'name', 'Unknown')}")
        if "results" not in shared:
            shared["results"] = {}
        # Use node name or ID if available. 
        # PocketFlow Nodes have .name attribute.
        shared["results"][self.name] = exec_res
        # Also store by ID if possible?
        node_id = getattr(self, 'id', None)
        if node_id:
             shared["results"][node_id] = exec_res
             
        print(f"DEBUG: Updated shared['results'] with {self.name}")
        # Return None to use "default" edge
        return None

# Example wrapper
class DebugNode(Node, BasePlatformNode):
    NODE_TYPE = "debug"
    DESCRIPTION = "Print input to console"
    PARAMS = {"prefix": "string", "show_shared": "boolean"}
    
    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        prefix = cfg.get("prefix", "DEBUG")
        show_shared = cfg.get("show_shared", False)
        
        # Get input from previous node
        results = shared.get("results", {})
        last_result = None
        if results:
            last_key = list(results.keys())[-1]
            last_result = results[last_key]
        
        return {
            "prefix": prefix,
            "input": last_result,
            "shared": shared if show_shared else None
        }

    def exec(self, prep_res):
        prefix = prep_res.get("prefix", "DEBUG")
        input_val = prep_res.get("input")
        shared = prep_res.get("shared")
        
        print(f"[{prefix}] Input: {input_val}")
        if shared:
            print(f"[{prefix}] Memory: {shared.get('memory', {})}")
        
        return input_val  # Pass through the input

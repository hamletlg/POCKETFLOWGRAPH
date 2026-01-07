from pocketflow import Node, BatchNode, AsyncNode
from pydantic import BaseModel
from typing import List, Dict, Any, Type, Optional, Union


class ParameterDefinition(BaseModel):
    type: str  # "string", "boolean", "int", "float"
    enum: Optional[List[str]] = None  # For enum parameters
    default: Optional[Any] = None  # Default value
    description: Optional[str] = None  # Parameter description


class NodeSchema(BaseModel):
    type: str
    description: str
    inputs: List[str] = ["default"]
    outputs: List[str] = ["default"]
    params: Dict[
        str, Union[str, ParameterDefinition]
    ] = {}  # param_name: type or ParameterDefinition


class BasePlatformNode:
    """Mixin to add platform metadata to PocketFlow nodes"""

    NODE_TYPE = "base"
    DESCRIPTION = "Base Node"
    INPUTS = ["default"]
    OUTPUTS = ["default"]
    PARAMS = {}  # Example: {"prompt": "string", "retries": "int"}

    @classmethod
    def get_schema(cls) -> NodeSchema:
        # Convert simple PARAMS dict to ParameterDefinition objects
        enhanced_params = {}
        for param_name, param_def in cls.PARAMS.items():
            if isinstance(param_def, dict):
                # Already enhanced format
                enhanced_params[param_name] = ParameterDefinition(**param_def)
            else:
                # Simple string format - convert to ParameterDefinition
                enhanced_params[param_name] = ParameterDefinition(type=param_def)

        return NodeSchema(
            type=cls.NODE_TYPE,
            description=cls.DESCRIPTION,
            inputs=cls.INPUTS,
            outputs=cls.OUTPUTS,
            params=enhanced_params,
        )

    def run(self, shared):
        node_id = getattr(self, "id", "unknown")
        callback = getattr(self, "on_event", None)

        print(
            f"DEBUG BasePlatformNode.run: node_id={node_id}, has_callback={callback is not None}"
        )

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
                    callback("node_end", {"node_id": node_id, "node_name": getattr(self, "name", node_id)})
                    
                    # Broadcast state_update after each node completes
                    # Safely serialize results to handle non-JSON-serializable objects
                    def safe_serialize(obj):
                        if isinstance(obj, dict):
                            return {k: safe_serialize(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [safe_serialize(item) for item in obj]
                        elif isinstance(obj, (str, int, float, bool, type(None))):
                            return obj
                        else:
                            return str(obj)
                    
                    raw_results = shared.get("results", {})
                    print(f"DEBUG: Broadcasting state_update. Raw results keys: {list(raw_results.keys())}")
                    serialized_results = safe_serialize(raw_results)
                    serialized_memory = safe_serialize(shared.get("memory", {}))
                    
                    print(f"DEBUG: Serialized results: {serialized_results}")
                    
                    callback("state_update", {
                        "memory": serialized_memory,
                        "results": serialized_results,
                        "node_id": node_id
                    })
                except Exception as e:
                    print(f"Callback error: {e}")
                    import traceback
                    traceback.print_exc()

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
        print(f"DEBUG BasePlatformNode.post: exec_res type={type(exec_res)}")
        if "results" not in shared:
            shared["results"] = {}
        
        # Use node name or ID if available.
        # PocketFlow Nodes have .name attribute.
        # CRITICAL: In Python 3.7+, updating a key doesn't change its order.
        # We must delete it first to ensure it moves to the end of the dict,
        # otherwise successors using "last_key" will see stale data in loops.
        name = self.name
        if name in shared["results"]:
            del shared["results"][name]
        shared["results"][name] = exec_res
        
        # Also store by ID if possible
        node_id = getattr(self, "id", None)
        if node_id:
            if node_id in shared["results"]:
                del shared["results"][node_id]
            shared["results"][node_id] = exec_res

        print(f"DEBUG: Updated shared['results'] with {self.name} (moved to end)")
        
        # Broadcast node_end and state_update
        # Run() is bypassed by PocketFlow engine, so we must do it here
        callback = getattr(self, "on_event", None)
        if callback:
            try:
                # Node End
                callback("node_end", {"node_id": node_id, "node_name": name})
                
                # State Update
                # Safely serialize results to handle non-JSON-serializable objects
                def safe_serialize(obj):
                    if isinstance(obj, dict):
                        return {k: safe_serialize(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [safe_serialize(item) for item in obj]
                    elif isinstance(obj, (str, int, float, bool, type(None))):
                        return obj
                    else:
                        return str(obj)
                
                serialized_results = safe_serialize(shared.get("results", {}))
                serialized_memory = safe_serialize(shared.get("memory", {}))
                
                print(f"DEBUG: Broadcasting state_update from post(). Results keys: {list(serialized_results.keys())}")
                callback("state_update", {
                    "memory": serialized_memory,
                    "results": serialized_results,
                    "node_id": node_id
                })
            except Exception as e:
                print(f"Callback error in post: {e}")
                import traceback
                traceback.print_exc()

        # Return None to use "default" edge
        return None


# Example wrapper
class DebugNode(BasePlatformNode, Node):
    NODE_TYPE = "debug"
    DESCRIPTION = "Print input to console"
    PARAMS = {
        "prefix": {
            "type": "string",
            "default": "DEBUG",
            "description": "Debug message prefix",
        },
        "show_shared": {
            "type": "boolean",
            "default": False,
            "description": "Show shared memory in debug output",
        },
    }

    def prep(self, shared):
        cfg = getattr(self, "config", {})
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
            "shared": shared if show_shared else None,
        }

    def exec(self, prep_res):
        prefix = prep_res.get("prefix", "DEBUG")
        input_val = prep_res.get("input")
        shared = prep_res.get("shared")

        print(f"[{prefix}] Input: {input_val}")
        if shared:
            print(f"[{prefix}] Memory: {shared.get('memory', {})}")

        return input_val  # Pass through the input

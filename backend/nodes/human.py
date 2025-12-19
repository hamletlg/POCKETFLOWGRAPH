import uuid
import threading
import json
import time
from .base import BasePlatformNode
from pocketflow import Node

# Global storage for HITL requests to allow communication between main thread/API and worker threads
# Key: request_id, Value: {"event": threading.Event, "response": Any}
pending_requests = {}

class HumanInputNode(BasePlatformNode, Node):
    """
    Pauses workflow execution and waits for user input via a frontend form.
    """
    NODE_TYPE = "human_input"
    DESCRIPTION = "Pause and wait for user approval or input"
    INPUTS = ["default"]
    OUTPUTS = ["default", "approved", "rejected"]
    PARAMS = {
        "prompt": "string",         # Header/Instruction for the user
        "fields": "string",         # JSON string: [{"name": "feedback", "type": "text", "label": "Comments"}]
        "timeout": "int"            # Optional seconds to wait before defaulting
    }

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        
        # Build context for display (what the user sees)
        input_val = None
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            input_val = results[last_key]
        
        # Parse fields
        fields_str = cfg.get("fields", "[]")
        try:
            fields = json.loads(fields_str)
        except:
            # Fallback default approval checkbox
            fields = [{"name": "approved", "type": "boolean", "label": "Approve?"}]

        return {
            "prompt": cfg.get("prompt", "User Input Required"),
            "fields": fields,
            "timeout": int(cfg.get("timeout", 0) or 0),
            "input_val": input_val,
            "shared": shared
        }

    def exec(self, prep_res):
        request_id = str(uuid.uuid4())
        wait_event = threading.Event()
        
        # Store in global registry
        pending_requests[request_id] = {
            "event": wait_event,
            "response": None,
            "node_id": getattr(self, 'id', 'unknown')
        }
        
        # Broadcast via WebSocket if callback available
        on_event = getattr(self, 'on_event', None)
        if on_event:
            on_event("USER_INPUT_REQUIRED", {
                "request_id": request_id,
                "prompt": prep_res["prompt"],
                "fields": prep_res["fields"],
                "data": prep_res["input_val"] # Context to show the user
            })
        
        print(f"HumanInputNode [{self.name}]: Waiting for user response (ID: {request_id})")
        
        # Wait for signal from API
        timeout = prep_res["timeout"]
        signaled = wait_event.wait(timeout=timeout if timeout > 0 else None)
        
        if not signaled:
            print(f"HumanInputNode [{self.name}]: Timeout reached.")
            del pending_requests[request_id]
            return {"error": "Timeout", "data": None, "approved": False}
        
        # Retrieve response
        response_data = pending_requests[request_id]["response"]
        del pending_requests[request_id]
        
        print(f"HumanInputNode [{self.name}]: Received response: {response_data}")
        
        return {
            "data": response_data,
            "approved": response_data.get("approved", True) if isinstance(response_data, dict) else True,
            "success": True
        }

    def post(self, shared, prep_res, exec_res):
        # Store data in memory
        if exec_res.get("success"):
            data = exec_res["data"]
            if isinstance(data, dict):
                if "memory" not in shared:
                    shared["memory"] = {}
                shared["memory"].update(data)
            
            super().post(shared, prep_res, data)
            
            # Route to specific output if present
            if exec_res.get("approved"):
                return "approved"
            else:
                return "rejected"
        
        super().post(shared, prep_res, exec_res.get("error", "User input failed"))
        return None

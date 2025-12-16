"""
Control Flow Nodes for PocketFlow Platform

Provides conditional branching and looping constructs:
- IfElseNode: Binary condition branching
- SwitchNode: Multi-branch value matching
- LoopNode: Iterate over list items
- WhileNode: Condition-based looping
- MergeNode: Combine multiple inputs
- TryCatchNode: Error handling with success/error paths
- DelayNode: Pause execution for specified duration
"""

import json
import time
from .base import BasePlatformNode
from pocketflow import Node


class IfElseNode(BasePlatformNode, Node):
    """Evaluates condition and routes to 'true' or 'false' output."""
    NODE_TYPE = "if_else"
    DESCRIPTION = "Branch based on condition (true/false)"
    INPUTS = ["default"]
    OUTPUTS = ["true", "false"]
    PARAMS = {
        "condition": "string",  # Python expression, use {input} for previous result
        "value": "string"       # Optional: override input value
    }

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        
        # Get input value from previous node or override
        value_override = cfg.get("value", "")
        if value_override:
            return {"input": value_override}
        
        # Get from shared results
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            return {"input": results[last_key]}
        return {"input": ""}

    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        condition = cfg.get("condition", "True")
        
        # Build evaluation context
        context = {"input": prep_res.get("input", "")}
        
        # Replace {input} placeholder with actual value for simple conditions
        eval_condition = condition
        for key, val in context.items():
            eval_condition = eval_condition.replace(f"{{{key}}}", repr(val))
        
        try:
            result = eval(eval_condition, {"__builtins__": {}}, context)
            return bool(result)
        except Exception as e:
            print(f"IfElseNode condition error: {e}")
            return False

    def post(self, shared, prep_res, exec_res):
        # Store result
        super().post(shared, prep_res, exec_res)
        # Return edge name based on condition result
        return "true" if exec_res else "false"


class SwitchNode(BasePlatformNode, Node):
    """Routes based on matching input value against defined cases."""
    NODE_TYPE = "switch"
    DESCRIPTION = "Route to different outputs based on value matching"
    INPUTS = ["default"]
    OUTPUTS = ["case_1", "case_2", "case_3", "default"]  # Static outputs for UI
    PARAMS = {
        "case_1": "string",  # Value to match for case_1
        "case_2": "string",  # Value to match for case_2
        "case_3": "string",  # Value to match for case_3
    }

    def prep(self, shared):
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            return {"input": str(results[last_key])}
        return {"input": ""}

    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        input_val = prep_res.get("input", "").strip()
        
        # Check each case
        for case_name in ["case_1", "case_2", "case_3"]:
            case_val = cfg.get(case_name, "").strip()
            if case_val and input_val == case_val:
                return case_name
        
        return "default"

    def post(self, shared, prep_res, exec_res):
        super().post(shared, prep_res, exec_res)
        return exec_res  # Return the matched case name as edge


class LoopNode(BasePlatformNode, Node):
    """Iterates over items, executing 'loop' path for each, then 'done'."""
    NODE_TYPE = "loop"
    DESCRIPTION = "Loop over items (JSON array or count)"
    INPUTS = ["default"]
    OUTPUTS = ["loop", "done"]
    PARAMS = {
        "items": "string",      # JSON array like ["a","b","c"] or a number for count
        "loop_var": "string"    # Variable name to store current item (default: "item")
    }

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        node_id = getattr(self, 'id', 'unknown_loop')
        loop_key = f"_loop_{node_id}"
        
        # Initialize or get loop state
        if loop_key not in shared:
            items_str = cfg.get("items", "[]")
            try:
                # Try parsing as JSON array
                items = json.loads(items_str)
                if isinstance(items, int):
                    items = list(range(items))
                elif not isinstance(items, list):
                    items = [items]
            except:
                # Try as integer count
                try:
                    count = int(items_str)
                    items = list(range(count))
                except:
                    items = []
            
            shared[loop_key] = {
                "items": items,
                "index": 0,
                "loop_var": cfg.get("loop_var", "item")
            }
        
        return shared[loop_key]

    def exec(self, prep_res):
        items = prep_res.get("items", [])
        index = prep_res.get("index", 0)
        
        if index < len(items):
            return {"continue": True, "current": items[index], "index": index}
        return {"continue": False, "current": None, "index": index}

    def post(self, shared, prep_res, exec_res):
        cfg = getattr(self, 'config', {})
        node_id = getattr(self, 'id', 'unknown_loop')
        loop_key = f"_loop_{node_id}"
        loop_var = cfg.get("loop_var", "item")
        
        if exec_res["continue"]:
            # Store current item in memory for downstream nodes
            if "memory" not in shared:
                shared["memory"] = {}
            shared["memory"][loop_var] = exec_res["current"]
            shared["memory"][f"{loop_var}_index"] = exec_res["index"]
            
            # Increment index for next iteration
            shared[loop_key]["index"] += 1
            
            # Store in results
            super().post(shared, prep_res, exec_res["current"])
            return "loop"
        else:
            # Clean up loop state
            if loop_key in shared:
                del shared[loop_key]
            super().post(shared, prep_res, "loop_complete")
            return "done"


class WhileNode(BasePlatformNode, Node):
    """Loops while condition is true, with max iteration limit."""
    NODE_TYPE = "while_loop"
    DESCRIPTION = "Loop while condition is true"
    INPUTS = ["default"]
    OUTPUTS = ["continue", "done"]
    PARAMS = {
        "condition": "string",      # Python expression
        "max_iterations": "int"     # Safety limit (default: 100)
    }

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        node_id = getattr(self, 'id', 'unknown_while')
        while_key = f"_while_{node_id}"
        
        # Initialize loop counter
        if while_key not in shared:
            shared[while_key] = {"iteration": 0}
        
        # Build context for condition evaluation
        context = {"iteration": shared[while_key]["iteration"]}
        
        # Add memory variables
        if "memory" in shared:
            context.update(shared["memory"])
        
        # Add last result
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            context["input"] = results[last_key]
        
        return {"context": context, "while_key": while_key, "shared": shared}

    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        condition = cfg.get("condition", "False")
        max_iter = int(cfg.get("max_iterations", 100))
        context = prep_res["context"]
        
        # Check iteration limit
        if context["iteration"] >= max_iter:
            return {"continue": False, "reason": "max_iterations"}
        
        # Evaluate condition
        try:
            result = eval(condition, {"__builtins__": {}}, context)
            return {"continue": bool(result), "reason": "condition"}
        except Exception as e:
            print(f"WhileNode condition error: {e}")
            return {"continue": False, "reason": "error"}

    def post(self, shared, prep_res, exec_res):
        while_key = prep_res["while_key"]
        
        if exec_res["continue"]:
            shared[while_key]["iteration"] += 1
            super().post(shared, prep_res, shared[while_key]["iteration"])
            return "continue"
        else:
            # Clean up
            if while_key in shared:
                del shared[while_key]
            super().post(shared, prep_res, "while_complete")
            return "done"


class MergeNode(BasePlatformNode, Node):
    """Merges multiple input paths into a single output."""
    NODE_TYPE = "merge"
    DESCRIPTION = "Combine multiple inputs into one output"
    INPUTS = ["a", "b", "c"]
    OUTPUTS = ["default"]
    PARAMS = {}

    def prep(self, shared):
        # Simply pass through the last result
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            return results[last_key]
        return None

    def exec(self, prep_res):
        # Pass through
        return prep_res

    def post(self, shared, prep_res, exec_res):
        super().post(shared, prep_res, exec_res)
        return None  # Use default edge


class TryCatchNode(BasePlatformNode, Node):
    """Wraps execution and routes to success or error output based on result."""
    NODE_TYPE = "try_catch"
    DESCRIPTION = "Error handling - route to success or error path"
    INPUTS = ["default"]
    OUTPUTS = ["success", "error"]
    PARAMS = {
        "error_patterns": "string"  # Optional: comma-separated error patterns to catch
    }

    def prep(self, shared):
        # Get the last result which may contain an error
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            return {"input": results[last_key], "key": last_key}
        return {"input": None, "key": None}

    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        input_val = prep_res.get("input", "")
        error_patterns = cfg.get("error_patterns", "Error,error,Exception,Failed,failed")
        
        # Convert to string for checking
        input_str = str(input_val) if input_val else ""
        
        # Check if input looks like an error
        patterns = [p.strip() for p in error_patterns.split(",") if p.strip()]
        is_error = any(pattern in input_str for pattern in patterns)
        
        return {
            "is_error": is_error,
            "value": input_val,
            "error_message": input_str if is_error else None
        }

    def post(self, shared, prep_res, exec_res):
        # Store error info in memory if error occurred
        if exec_res["is_error"]:
            if "memory" not in shared:
                shared["memory"] = {}
            shared["memory"]["last_error"] = exec_res["error_message"]
            super().post(shared, prep_res, exec_res["error_message"])
            return "error"
        else:
            super().post(shared, prep_res, exec_res["value"])
            return "success"


class DelayNode(BasePlatformNode, Node):
    """Pauses execution for a specified duration."""
    NODE_TYPE = "delay"
    DESCRIPTION = "Pause execution for specified seconds"
    INPUTS = ["default"]
    OUTPUTS = ["default"]
    PARAMS = {
        "seconds": "float",        # Duration to sleep (default: 1.0)
        "message": "string"        # Optional: message to log during delay
    }

    def prep(self, shared):
        # Pass through the last result
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            return results[last_key]
        return None

    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        
        try:
            seconds = float(cfg.get("seconds", 1.0))
        except (ValueError, TypeError):
            seconds = 1.0
        
        message = cfg.get("message", "")
        
        if message:
            print(f"DelayNode: {message} (waiting {seconds}s)")
        else:
            print(f"DelayNode: Sleeping for {seconds} seconds")
        
        # Perform the delay
        time.sleep(seconds)
        
        # Pass through the input
        return prep_res

    def post(self, shared, prep_res, exec_res):
        super().post(shared, prep_res, exec_res)
        return None  # Use default edge


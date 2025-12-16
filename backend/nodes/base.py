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
        prep_res = self.prep(shared)
        exec_res = self.exec(prep_res)
        return self.post(shared, prep_res, exec_res)

    def post(self, shared, prep_res, exec_res):
        print(f"DEBUG: Executing post for {getattr(self, 'name', 'Unknown')}")
        if "results" not in shared:
            shared["results"] = {}
        # Use node name or ID if available. 
        # PocketFlow Nodes have .name attribute.
        shared["results"][self.name] = exec_res
        print(f"DEBUG: Updated shared['results'] with {self.name}")
        # Return None to use "default" edge
        return None

# Example wrapper
class DebugNode(Node, BasePlatformNode):
    NODE_TYPE = "debug"
    DESCRIPTION = "Prinst input to console"
    PARAMS = {"prefix": "string"}
    
    def prep(self, shared):
        prefix = self.params.get("prefix", "DEBUG: ")
        return prefix

    def exec(self, prep_res):
        print(f"{prep_res} {self.params}")
        return self.params

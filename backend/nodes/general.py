from .base import BasePlatformNode
from pocketflow import Node

class StartNode(BasePlatformNode, Node):
    NODE_TYPE = "start"
    DESCRIPTION = "Entry point of the flow"
    PARAMS = {
        "show_overlay": "boolean",
        "local_llm_address": "string" # e.g. http://localhost:1234/v1
    }
    
    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        llm_addr = cfg.get("local_llm_address")
        if llm_addr:
            shared["llm_base_url"] = llm_addr
        return shared
    
    def exec(self, prep_res):
        return "Flow Started"

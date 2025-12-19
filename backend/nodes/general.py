from .base import BasePlatformNode
from pocketflow import Node


class StartNode(BasePlatformNode, Node):
    """Entry point of the flow with optional configuration."""

    NODE_TYPE = "start"
    DESCRIPTION = "Entry point of the flow"
    PARAMS = {
        "local_llm_address": {
            "type": "string",
            "description": "Local LLM server address (e.g., http://localhost:1234/v1)",
        },
        "initial_value": {
            "type": "string",
            "description": "Optional initial input value",
        },
        "show_overlay": {
            "type": "boolean",
            "default": False,
            "description": "Toggle execution result overlay",
        },
    }

    def prep(self, shared):
        cfg = getattr(self, "config", {})

        # Set global LLM address if provided
        llm_addr = cfg.get("local_llm_address")
        if llm_addr:
            shared["llm_base_url"] = llm_addr

        return shared

    def exec(self, prep_res):
        cfg = getattr(self, "config", {})
        initial = cfg.get("initial_value", "")
        return initial if initial else "Flow Started"

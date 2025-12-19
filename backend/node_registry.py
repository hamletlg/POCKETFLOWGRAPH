import os
import importlib
import inspect
from typing import Dict, Type
from .nodes.base import BasePlatformNode, NodeSchema, DebugNode
from .nodes.llm import LLMNode
from .nodes.general import StartNode
from .nodes.io import FileReadNode, FileWriteNode, PDFReadNode
from .nodes.web import WebSearchNode, WebFetchNode, RSSNode
from .nodes.data import MemoryNode, SQLiteNode
from .nodes.scheduling import CronNode
from .nodes.control_flow import IfElseNode, SwitchNode, LoopNode, WhileNode, MergeNode, TryCatchNode, DelayNode, JSONDispatcherNode, SubWorkflowNode

class NodeRegistry:
    def __init__(self):
        self.node_classes: Dict[str, Type[BasePlatformNode]] = {}
        
        # Explicit registration
        self.register(StartNode)
        self.register(CronNode)
        self.register(LLMNode)
        self.register(DebugNode)
        self.register(FileReadNode)
        self.register(FileWriteNode)
        self.register(PDFReadNode)
        self.register(WebSearchNode)
        self.register(WebFetchNode)
        self.register(RSSNode)
        self.register(MemoryNode)
        self.register(SQLiteNode)
        # Control Flow Nodes
        self.register(IfElseNode)
        self.register(SwitchNode)
        self.register(LoopNode)
        self.register(WhileNode)
        self.register(MergeNode)
        self.register(TryCatchNode)
        self.register(DelayNode)
        self.register(JSONDispatcherNode)
        self.register(SubWorkflowNode)

    def register(self, cls):
        if hasattr(cls, "NODE_TYPE"):
            self.node_classes[cls.NODE_TYPE] = cls

    def get_node_class(self, node_type: str) -> Type[BasePlatformNode]:
        return self.node_classes.get(node_type)

    def get_all_metadata(self):
        nodes = []
        for _, cls in self.node_classes.items():
            try:
                # We assume get_schema is available on BasePlatformNode subclasses
                schema = cls.get_schema() 
                nodes.append(schema)
            except Exception as e:
                print(f"Error extracting schema from {cls}: {e}")
        return nodes

registry = NodeRegistry()

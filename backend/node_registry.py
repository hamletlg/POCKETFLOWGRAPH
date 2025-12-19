import os
import importlib
import inspect
from typing import Dict, Type
from .nodes.base import BasePlatformNode, NodeSchema, DebugNode
from .nodes.llm import LLMNode
from .nodes.general import StartNode
from .nodes.io import FileReadNode, FileWriteNode, PDFReadNode
from .nodes.control_flow import IfElseNode, SwitchNode, LoopNode, WhileNode, MergeNode, TryCatchNode, DelayNode, JSONDispatcherNode, SubWorkflowNode, SequentialBatchNode
from .nodes.web import WebSearchNode, WebFetchNode, RSSNode
from .nodes.data import MemoryNode, SQLiteNode, VariableExtractorNode
from .nodes.vector_memory import VectorMemoryNode
from .nodes.base import NodeSchema
from .nodes.scheduling import CronNode

# No changes needed here, just verifying.

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
        self.register(VariableExtractorNode)
        self.register(SequentialBatchNode)
        self.register(VectorMemoryNode)
        
        # Visual/Utility Nodes (Front-end only, dummies in backend)
        class NoteNode:
            NODE_TYPE = "note"
            DESCRIPTION = "A sticky note for documentation"
            INPUTS = []
            OUTPUTS = []
            PARAMS = {}
            @classmethod
            def get_schema(cls):
                return NodeSchema(type=cls.NODE_TYPE, description=cls.DESCRIPTION, inputs=cls.INPUTS, outputs=cls.OUTPUTS, params=cls.PARAMS)

        class GroupNode:
            NODE_TYPE = "group"
            DESCRIPTION = "A labeled block to group nodes"
            INPUTS = []
            OUTPUTS = []
            PARAMS = {}
            @classmethod
            def get_schema(cls):
                return NodeSchema(type=cls.NODE_TYPE, description=cls.DESCRIPTION, inputs=cls.INPUTS, outputs=cls.OUTPUTS, params=cls.PARAMS)

        self.register(NoteNode)
        self.register(GroupNode)

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

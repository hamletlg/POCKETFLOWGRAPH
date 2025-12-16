from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class NodeMetadata(BaseModel):
    type: str
    description: str
    inputs: List[str]
    outputs: List[str]
    params: Dict[str, Any]

class Edge(BaseModel):
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None

class NodeConfig(BaseModel):
    id: str
    type: str # This should match NodeMetadata.type
    label: str
    position: Dict[str, float]
    data: Dict[str, Any] # Parameters

class Workflow(BaseModel):
    nodes: List[NodeConfig]
    edges: List[Edge]

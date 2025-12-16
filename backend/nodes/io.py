import os
from .base import BasePlatformNode
from pocketflow import Node

class FileReadNode(BasePlatformNode, Node):
    NODE_TYPE = "file_read"
    DESCRIPTION = "Read content from a file"
    PARAMS = {"path": "string"}
    
    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        path = cfg.get("path", "")
        if not path:
            return "Error: No path provided"
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

class FileWriteNode(BasePlatformNode, Node):
    NODE_TYPE = "file_write"
    DESCRIPTION = "Write content to a file"
    PARAMS = {"path": "string", "content": "string", "mode": "string"} # mode: w or a
    
    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        path = cfg.get("path", "")
        mode = cfg.get("mode", "w")
        
        # content can come from params OR from previous node (prep_res)
        content_param = cfg.get("content", "")
        
        # If prep_res is valid string and not empty, use it.
        # Otherwise use content param.
        content_to_write = content_param
        if prep_res and isinstance(prep_res, str):
             # Strategy: if param is empty, use input. 
             # Or maybe append? let's stick to: if input exists, it overrides empty param.
             if not content_param:
                 content_to_write = prep_res
        
        if not path:
            return "Error: No path provided"
            
        try:
            with open(path, mode, encoding="utf-8") as f:
                f.write(content_to_write)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

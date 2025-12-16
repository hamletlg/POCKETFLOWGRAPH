import sqlite3
import os
from .base import BasePlatformNode
from pocketflow import Node

class MemoryNode(BasePlatformNode, Node):
    NODE_TYPE = "memory"
    DESCRIPTION = "Store and Retrieve values from shared memory"
    PARAMS = {"key": "string", "value": "string", "operation": "string"} # get, set
    
    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        key = cfg.get("key", "default_key")
        value = cfg.get("value", "")
        op = cfg.get("operation", "get")
        
        # Access shared memory? 
        # prep_res in my implementation IS the last result, not the full shared dict.
        # But wait, BasePlatformNode.prep returns prep_res generated from shared.
        # I need access to 'shared' to WRITE to it for the NEXT nodes.
        # But exec only gets prep_res. 
        
        # ISSUE: PocketFlow separation of concerns.
        # 'shared' is passed to prep, post. Not exec.
        # So 'MemoryNode' logic usually happens in 'prep' (read) or 'post' (write).
        
        # Let's handle it in `post` via a special return or Side Effect?
        # OR: I can pass 'shared' through prep?
        
        # My BasePlatformNode.prep default (in base.py? No, base.py doesn't implement prep)
        # LLMNode implements prep.
        # I should implement prep here to grab 'shared'.
        return "Memory Node Executor"
        
    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        key = cfg.get("key", "default_key")
        op = cfg.get("operation", "get")
        val = cfg.get("value", "")
        
        # Create memory info if not exists
        if "memory" not in shared:
            shared["memory"] = {}
            
        if op == "set":
            # If value param is empty, use previous node output (found in shared results)
            if not val:
                 results = shared.get("results", {})
                 if results:
                    last_key = list(results.keys())[-1]
                    val = results[last_key]
            
            shared["memory"][key] = val
            return f"Set {key} = {val}"
            
        elif op == "get":
            return shared["memory"].get(key, "Not Found")
            
        return "Invalid Operation"

    def exec(self, prep_res):
        return prep_res

class SQLiteNode(BasePlatformNode, Node):
    NODE_TYPE = "sqlite"
    DESCRIPTION = "Execute SQL Query"
    PARAMS = {"db_path": "string", "query": "string"}
    
    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        db_path = cfg.get("db_path", "database.db")
        query = cfg.get("query", "")
        
        if not query:
            return "Error: No query provided"
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            
            if query.strip().lower().startswith("select"):
                rows = cursor.fetchall()
                conn.close()
                return str(rows)
            else:
                conn.commit()
                conn.close()
                return "Query executed successfully"
        except Exception as e:
            return f"SQL Error: {e}"

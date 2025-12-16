import sqlite3
import os
import json
from .base import BasePlatformNode
from pocketflow import Node


class MemoryNode(BasePlatformNode, Node):
    """
    Store and retrieve values with optional file-based persistence.
    
    Operations:
    - get: Retrieve a value by key
    - set: Store a value (from param or previous node output)
    - delete: Remove a key
    - list: List all keys (optionally filtered by namespace)
    - append: Append to a list value
    """
    NODE_TYPE = "memory"
    DESCRIPTION = "Store/retrieve values (session or persistent file)"
    PARAMS = {
        "key": "string",           # Key name
        "value": "string",         # Value to store (for set/append)
        "operation": "string",     # get, set, delete, list, append
        "persistent": "boolean",   # If true, saves to JSON file
        "namespace": "string"      # Optional: group keys (e.g., "user.prefs")
    }
    
    # File path for persistent storage
    MEMORY_FILE = ".pocketflow_memory.json"

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        key = cfg.get("key", "").strip()
        op = cfg.get("operation", "get").lower().strip()
        val = cfg.get("value", "")
        persistent = cfg.get("persistent", False)
        namespace = cfg.get("namespace", "").strip()
        
        # Build full key with namespace
        full_key = f"{namespace}.{key}" if namespace and key else key
        
        # Initialize session memory if not exists
        if "memory" not in shared:
            shared["memory"] = {}
        
        # Load persistent memory if needed
        persistent_data = {}
        if persistent:
            persistent_data = self._load_persistent()
        
        # Get input from previous node if value is empty
        input_value = None
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            input_value = results[last_key]
        
        return {
            "key": key,
            "full_key": full_key,
            "op": op,
            "value": val,
            "input_value": input_value,
            "persistent": persistent,
            "persistent_data": persistent_data,
            "namespace": namespace,
            "shared": shared
        }

    def exec(self, prep_res):
        op = prep_res["op"]
        key = prep_res["key"]
        full_key = prep_res["full_key"]
        value = prep_res["value"]
        input_value = prep_res["input_value"]
        persistent = prep_res["persistent"]
        persistent_data = prep_res["persistent_data"]
        shared = prep_res["shared"]
        namespace = prep_res["namespace"]
        
        # Choose storage: persistent or session
        storage = persistent_data if persistent else shared.get("memory", {})
        
        if op == "get":
            result = storage.get(full_key, None)
            if result is None:
                return {"success": False, "value": None, "message": f"Key '{full_key}' not found"}
            return {"success": True, "value": result, "message": f"Retrieved '{full_key}'"}
        
        elif op == "set":
            # Use provided value, or fall back to input from previous node
            store_value = value if value else input_value
            
            # Try to parse as JSON for complex types
            if isinstance(store_value, str):
                try:
                    store_value = json.loads(store_value)
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string
            
            storage[full_key] = store_value
            
            # Update shared memory (for session access by other nodes)
            shared["memory"][full_key] = store_value
            
            # Persist if needed
            if persistent:
                self._save_persistent(storage)
            
            return {"success": True, "value": store_value, "message": f"Set '{full_key}'"}
        
        elif op == "delete":
            if full_key in storage:
                del storage[full_key]
                if full_key in shared.get("memory", {}):
                    del shared["memory"][full_key]
                if persistent:
                    self._save_persistent(storage)
                return {"success": True, "value": None, "message": f"Deleted '{full_key}'"}
            return {"success": False, "value": None, "message": f"Key '{full_key}' not found"}
        
        elif op == "list":
            # List all keys, optionally filtered by namespace
            if namespace:
                keys = [k for k in storage.keys() if k.startswith(f"{namespace}.")]
            else:
                keys = list(storage.keys())
            return {"success": True, "value": keys, "message": f"Found {len(keys)} keys"}
        
        elif op == "append":
            # Append to a list value
            store_value = value if value else input_value
            
            existing = storage.get(full_key, [])
            if not isinstance(existing, list):
                existing = [existing] if existing else []
            
            existing.append(store_value)
            storage[full_key] = existing
            shared["memory"][full_key] = existing
            
            if persistent:
                self._save_persistent(storage)
            
            return {"success": True, "value": existing, "message": f"Appended to '{full_key}'"}
        
        return {"success": False, "value": None, "message": f"Unknown operation: {op}"}

    def _load_persistent(self) -> dict:
        """Load persistent memory from JSON file."""
        if os.path.exists(self.MEMORY_FILE):
            try:
                with open(self.MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_persistent(self, data: dict):
        """Save persistent memory to JSON file."""
        try:
            with open(self.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving persistent memory: {e}")

    def post(self, shared, prep_res, exec_res):
        """Return the value for downstream nodes."""
        value = exec_res.get("value")
        
        # Store result
        super().post(shared, prep_res, value)
        return None

class SQLiteNode(BasePlatformNode, Node):
    """Execute SQL queries with variable substitution and structured output."""
    NODE_TYPE = "sqlite"
    DESCRIPTION = "Execute SQL query (supports {input} and {memory_key})"
    PARAMS = {
        "db_path": "string",
        "query": "string",
        "as_list": "boolean"  # Return as list for Loop compatibility
    }

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        
        # Build context for variable substitution
        context = {}
        
        # Get input from previous node
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            context["input"] = results[last_key]
        
        # Add memory variables
        if "memory" in shared:
            context.update(shared["memory"])
        
        return {
            "db_path": cfg.get("db_path", "database.db"),
            "query": cfg.get("query", ""),
            "as_list": cfg.get("as_list", False),
            "context": context
        }

    def exec(self, prep_res):
        db_path = prep_res["db_path"]
        query = prep_res["query"]
        as_list = prep_res["as_list"]
        context = prep_res["context"]
        
        if not query:
            return {"error": "No query provided", "rows": [], "success": False}
        
        # Variable substitution in query
        for key, value in context.items():
            # Escape single quotes for SQL safety
            if isinstance(value, str):
                safe_value = value.replace("'", "''")
            else:
                safe_value = str(value)
            query = query.replace(f"{{{key}}}", safe_value)
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            
            if query.strip().lower().startswith("select"):
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                conn.close()
                
                # Convert to list of dicts for easier use
                if as_list and columns:
                    result = [dict(zip(columns, row)) for row in rows]
                else:
                    result = rows
                
                return {"rows": result, "columns": columns, "count": len(rows), "success": True}
            else:
                affected = cursor.rowcount
                conn.commit()
                conn.close()
                return {"affected": affected, "success": True, "message": f"Query executed, {affected} rows affected"}
                
        except Exception as e:
            return {"error": str(e), "success": False}

    def post(self, shared, prep_res, exec_res):
        if exec_res.get("success"):
            # For SELECT queries, return rows (or list of dicts)
            if "rows" in exec_res:
                super().post(shared, prep_res, exec_res["rows"])
            else:
                super().post(shared, prep_res, exec_res.get("message", "OK"))
        else:
            super().post(shared, prep_res, exec_res.get("error", "Query failed"))
        return None


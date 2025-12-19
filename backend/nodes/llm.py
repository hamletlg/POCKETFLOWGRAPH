from .base import BasePlatformNode
from pocketflow import Node
import openai
import os
import json


class LLMNode(BasePlatformNode, Node):
    """
    Generate text using a local LLM (OpenAI compatible).
    
    Features:
    - Variable injection: Use {input}, {memory_key} in prompts
    - Persistent memory: Reads from both session and file-based memory
    - Chat history: Optional conversation tracking with configurable max turns
    """
    NODE_TYPE = "llm"
    DESCRIPTION = "Generate text using a local LLM (OpenAI compatible)"
    INPUTS = ["default", "context"]
    PARAMS = {
        "api_base": "string",       # e.g. http://localhost:1234/v1
        "api_key": "string",        # usually 'lm-studio' or similar
        "model": "string",          # e.g. "llama-3.2"
        "system_prompt": "string",
        "user_prompt": "string",    # can use {input}, {memory_key}
        "temperature": "float",
        "use_history": "boolean",   # Enable chat history
        "conversation_id": "string", # Unique ID for conversation (default: "default")
        "max_history": "int"        # Max messages to keep (default: 10)
    }
    
    MEMORY_FILE = ".pocketflow_memory.json"

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        
        # LLM Configuration
        default_base = shared.get("llm_base_url", "http://localhost:1234/v1")
        val = cfg.get("api_base")
        self.api_base = val if val else default_base
        self.api_key = cfg.get("api_key", "lm-studio")
        self.model = cfg.get("model", "local-model")
        self.system_prompt = cfg.get("system_prompt", "You are a helpful assistant.")
        self.user_prompt_template = cfg.get("user_prompt", "{input}")
        self.temperature = float(cfg.get("temperature", 0.7))
        
        # Chat history configuration
        self.use_history = cfg.get("use_history", False)
        self.conversation_id = cfg.get("conversation_id", "default") or "default"
        self.max_history = int(cfg.get("max_history", 10) or 10)
        
        # Build Context from multiple sources
        context = {}
        results = shared.get("results", {})
        input_mapping = getattr(self, 'input_mapping', {})
        if input_mapping:
            # Map "default" handle to "input" variable in prompt
            default_node_name = input_mapping.get("default")
            if default_node_name and default_node_name in results:
                context['input'] = results[default_node_name]
            
            # Map "context" handle to "context" variable in prompt
            context_node_name = input_mapping.get("context")
            if context_node_name and context_node_name in results:
                context['context'] = results[context_node_name]

        # 2. Fallback to "last result" logic if no mapping or missing keys
        if 'input' not in context and results:
            last_key = list(results.keys())[-1]
            context['input'] = results[last_key]
        
        if 'input' not in context:
            context['input'] = ""
        
        # 2. Session memory (in-memory)
        if "memory" in shared and isinstance(shared["memory"], dict):
            context.update(shared["memory"])
        
        # 3. Persistent memory (from file) - NEW
        persistent_data = self._load_persistent()
        for key, value in persistent_data.items():
            if key not in context:  # Don't override session memory
                context[key] = value
        
        # 4. Load chat history if enabled
        history = []
        if self.use_history:
            history = self._load_history(self.conversation_id)
        
        return {
            "context": context,
            "history": history,
            "shared": shared
        }

    def exec(self, prep_res):
        context = prep_res["context"]
        history = prep_res["history"]
        
        print(f"DEBUG LLMNode: context_keys={list(context.keys())}")
        
        # Build user content with variable substitution
        user_content = self.user_prompt_template
        for key, value in context.items():
            # Handle complex types
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            user_content = user_content.replace(f"{{{key}}}", str(value))
        
        print(f"DEBUG LLMNode: final_content='{user_content[:100]}...'")
        
        try:
            client = openai.OpenAI(base_url=self.api_base, api_key=self.api_key, timeout=600)
            
            # Build messages list
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add history if enabled
            if self.use_history and history:
                messages.extend(history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_content})
            
            print(f"Sending request to {self.api_base} with model {self.model} ({len(messages)} messages)")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            content = response.choices[0].message.content
            print(f"LLMNode response: {content[:100]}...")
            
            return {
                "response": content,
                "user_message": user_content,
                "success": True
            }
        except Exception as e:
            print(f"LLMNode Error: {e}")
            return {
                "response": f"Error: {str(e)}",
                "user_message": user_content,
                "success": False
            }

    def post(self, shared, prep_res, exec_res):
        """Store result and update chat history if enabled."""
        response = exec_res.get("response", "")
        
        # Update chat history if enabled
        if self.use_history and exec_res.get("success"):
            user_msg = exec_res.get("user_message", "")
            self._save_history(
                self.conversation_id,
                user_msg,
                response,
                self.max_history
            )
        
        # Store response for downstream nodes
        super().post(shared, prep_res, response)
        return None

    def _load_persistent(self) -> dict:
        """Load persistent memory from JSON file."""
        if os.path.exists(self.MEMORY_FILE):
            try:
                with open(self.MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _load_history(self, conversation_id: str) -> list:
        """Load chat history for a conversation."""
        data = self._load_persistent()
        history_key = f"_chat_history_{conversation_id}"
        return data.get(history_key, [])

    def _save_history(self, conversation_id: str, user_msg: str, assistant_msg: str, max_history: int):
        """Save chat history, respecting max_history limit."""
        data = self._load_persistent()
        history_key = f"_chat_history_{conversation_id}"
        
        history = data.get(history_key, [])
        
        # Append new messages
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})
        
        # Trim to max_history (max_history is number of turns, so multiply by 2 for messages)
        max_messages = max_history * 2
        if len(history) > max_messages:
            history = history[-max_messages:]
        
        data[history_key] = history
        
        # Save back to file
        try:
            with open(self.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving chat history: {e}")


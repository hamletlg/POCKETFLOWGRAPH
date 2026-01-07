from .base import BasePlatformNode
from pocketflow import Node
import openai
import os
import json
import config


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
    PARAMS = {
        "api_base": "string",       # e.g. http://localhost:1234/v1
        "api_key": "string",        # usually 'lm-studio' or similar
        "model": "string",          # e.g. "llama-3.2"
        "system_prompt": "string",
        "user_prompt": "string",    # can use {input}, {memory_key}
        "image": "string",          # Optional: Image path or URL or {variable}
        "temperature": "float",
        "use_history": "boolean",   # Enable chat history
        "conversation_id": "string", # Unique ID for conversation (default: "default")
        "max_history": "int",        # Max messages to keep (default: 10)
        "time_out": "int"          # Request timeout in seconds
    }
    
    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        
        # LLM Configuration Hierarchy: Node > Shared > App Default
        self.api_base = cfg.get("api_base") or shared.get("llm_base_url") or config.LLM_BASE_URL
        self.api_key = cfg.get("api_key") or shared.get("llm_api_key") or config.LLM_API_KEY
        self.model = cfg.get("model") or shared.get("llm_model") or config.LLM_MODEL
        
        self.system_prompt = cfg.get("system_prompt", "You are a helpful assistant.")
        self.user_prompt_template = cfg.get("user_prompt", "{input}")
        self.image_template = cfg.get("image", "") # Optional image input
        self.temperature = float(cfg.get("temperature", 0.7))
        self.time_out = int(cfg.get("time_out", 600))
        
        # Chat history configuration
        self.use_history = cfg.get("use_history", False)
        self.conversation_id = cfg.get("conversation_id", "default") or "default"
        self.max_history = int(cfg.get("max_history", 10) or 10)
        
        # Build Context from multiple sources
        context = {}
        
        # 1. "input": result of the predecessor node
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            context['input'] = results[last_key]
        else:
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

    def _encode_image(self, image_path):
        import base64
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def exec(self, prep_res):
        context = prep_res["context"]
        history = prep_res["history"]
        
        print(f"DEBUG LLMNode: context_keys={list(context.keys())}")
        
        # Build user content with variable substitution
        user_content = self.user_prompt_template
        image_input = self.image_template
        
        for key, value in context.items():
            # Handle complex types
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            replacement = str(value)
            user_content = user_content.replace(f"{{{key}}}", replacement)
            if image_input:
                image_input = image_input.replace(f"{{{key}}}", replacement)
        
        print(f"DEBUG LLMNode: final_content='{user_content[:100]}...'")
        
        # Get callback for event broadcasting
        callback = getattr(self, "on_event", None)
        node_id = getattr(self, "id", "unknown")
        
        try:
            client = openai.OpenAI(base_url=self.api_base, api_key=self.api_key, timeout=self.time_out)
            
            # Build messages list
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add history if enabled
            if self.use_history and history:
                messages.extend(history)
            
            # Add current user message
            if image_input and (image_input.startswith("http") or os.path.exists(image_input)):
                # Multi-modal payload
                content_payload = [{"type": "text", "text": user_content}]
                
                if image_input.startswith("http"):
                    image_url = image_input
                    print(f"Using image URL: {image_url}")
                    content_payload.append({
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    })
                else: 
                    # Local file
                    try:
                        base64_image = self._encode_image(image_input)
                        print(f"Encoded local image: {image_input}")
                        content_payload.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        })
                    except Exception as img_err:
                        print(f"Failed to encode image: {img_err}")
                        # Fallback to just text if image fails
                
                messages.append({"role": "user", "content": content_payload})
            else:
                # Standard text payload
                messages.append({"role": "user", "content": user_content})
            
            print(f"Sending request to {self.api_base} with model {self.model} ({len(messages)} messages)")
            
            # Broadcast llm_call event
            if callback:
                try:
                    # Truncate prompt preview for display
                    prompt_preview = user_content[:500] + ("..." if len(user_content) > 500 else "")
                    callback("llm_call", {
                        "node_id": node_id,
                        "model": self.model,
                        "prompt_preview": prompt_preview,
                        "message_count": len(messages)
                    })
                except Exception as e:
                    print(f"llm_call callback error: {e}")
            
            import time
            start_time = time.time()
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            content = response.choices[0].message.content
            print(f"LLMNode response: {content[:100]}...")
            
            # Broadcast llm_response event
            if callback:
                try:
                    # Send full response (frontend can handle display)
                    callback("llm_response", {
                        "node_id": node_id,
                        "node_name": getattr(self, "name", node_id),
                        "model": self.model,
                        "response": content,  # Full response
                        "duration_ms": duration_ms
                    })
                except Exception as e:
                    print(f"llm_response callback error: {e}")
            
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
        print(f"DEBUG LLMNode.post: exec_res keys={list(exec_res.keys())}")
        response = exec_res.get("response", "")
        print(f"DEBUG LLMNode.post: response length={len(response)}")
        
        # Update chat history if enabled
        if self.use_history and exec_res.get("success"):
            try:
                user_msg = exec_res.get("user_message", "")
                # Note: We currently only save text in history for simplicity
                # To support full multimodal history, we'd need to store the structured list.
                # providing text-only representation for now.
                self._save_history(
                    self.conversation_id,
                    user_msg,
                    response,
                    self.max_history
                )
            except Exception as e:
                print(f"LLMNode.post Warning: Failed to save history: {e}")
        
        # Store response for downstream nodes
        print(f"DEBUG LLMNode.post: calling super().post with response type {type(response)}")
        super().post(shared, prep_res, response)
        return None

    def _load_persistent(self) -> dict:
        """Load persistent memory from JSON file."""
        if os.path.exists(config.MEMORY_FILE):
            try:
                with open(config.MEMORY_FILE, "r", encoding="utf-8") as f:
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
            with open(config.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving chat history: {e}")


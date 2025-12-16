from .base import BasePlatformNode
from pocketflow import Node
import openai
import os

class LLMNode(BasePlatformNode, Node):
    NODE_TYPE = "llm"
    DESCRIPTION = "Generate text using a local LLM (OpenAI compatible)"
    PARAMS = {
        "api_base": "string", # e.g. http://localhost:1234/v1
        "api_key": "string",  # usually 'lm-studio' or similar
        "model": "string",    # e.g. "llama-3.2"
        "system_prompt": "string",
        "user_prompt": "string", # can use {input} to inject previous node output
        "temperature": "float"
    }

    def prep(self, shared):
        # Retrieve params from self.config (to allow PocketFlow to manage self.params)
        cfg = getattr(self, 'config', {})
        
        # Check global override from StartNode
        default_base = shared.get("llm_base_url", "http://localhost:1234/v1")
        
        self.api_base = cfg.get("api_base", default_base)
        # If the user specifically set api_base in this node to something different from default, 
        # normally cfg.get would return it.
        # But if the user specifically Wants the global override to take precedence?
        # Typically "Global Config" > "Default", but "Node Config" > "Global Config".
        # However, the user said "override the predefined address".
        # If the node has "http://localhost:1234/v1" configured (which is default in UI?), 
        # how do we distinguish "user set this" vs "default"?
        # For now, let's assume if it's in shared, we treat it as the new default if the node param is empty or default.
        # However, if the user explicitly typed a different URL in the node, that should probably win.
        # But if the user left it as default or empty, the global one wins.
        # Let's trust the logic: cfg.get("api_base", default_base)
        # If "api_base" is set in config (and not empty / None), it wins.
        # If it's not set (e.g. empty string), we might want fallback?
        # Let's enforce: if config value is empty string, use default_base.
        
        val = cfg.get("api_base")
        self.api_base = val if val else default_base
        self.api_key = cfg.get("api_key", "lm-studio")
        self.model = cfg.get("model", "local-model")
        self.system_prompt = cfg.get("system_prompt", "You are a helpful assistant.")
        self.user_prompt_template = cfg.get("user_prompt", "{input}")
        self.temperature = float(cfg.get("temperature", 0.7))
        
        # Build Context
        context = {}
        
        # 1. "input": result of the predecessor node
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            context['input'] = results[last_key]
        else:
            context['input'] = ""
            
        # 2. Memory: add all keys from shared memory
        if "memory" in shared and isinstance(shared["memory"], dict):
            context.update(shared["memory"])
            
        return context

    def exec(self, context):
        # Context contains 'input' and memory variables
        # Use simple string replacement for safety and control
        
        cfg = getattr(self, 'config', {})
        print(f"DEBUG LLMNode: config={cfg}")
        print(f"DEBUG LLMNode: context_keys={list(context.keys())} content={context}")
        
        user_content = self.user_prompt_template
        
        # Replace {key} with value from context
        # We loop over context to support arbitrary keys
        for key, value in context.items():
            user_content = user_content.replace(f"{{{key}}}", str(value))
            
        print(f"DEBUG LLMNode: final_content='{user_content}'")
        
        try:
            client = openai.OpenAI(base_url=self.api_base, api_key=self.api_key)
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content}
            ]
            print(f"Sending request to {self.api_base} with model {self.model}")
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            content = response.choices[0].message.content
            print(f"LLMNode response: {content}")
            return content
        except Exception as e:
            print(f"LLMNode Error: {e}")
            return f"Error: {str(e)}"

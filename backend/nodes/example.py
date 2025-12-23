from .base import BasePlatformNode
from pocketflow import Node


class ExampleNode(BasePlatformNode, Node):
    """
    A simple example node that demonstrates the basic structure.
    
    This node takes an input string and returns it with a prefix.
    It shows how to define parameters, process data, and handle execution.
    """
    
    # Define the node type (must be unique)
    NODE_TYPE = "example"
    
    # Description for UI display
    DESCRIPTION = "A simple example node that adds a prefix to input"
    
    # Define parameters with their types and default values
    PARAMS = {
        "prefix": {
            "type": "string",
            "default": "Example:",
            "description": "Text to prepend to the input"
        },
        "uppercase": {
            "type": "boolean", 
            "default": False,
            "description": "Convert output to uppercase"
        }
    }

    def prep(self, shared):
        """
        Prepare data for execution.
        
        This method is called before exec() and should prepare any context
        needed for the node's operation. It receives the shared memory from 
        previous nodes.
        """
        cfg = getattr(self, "config", {})
        
        # Get configuration parameters with defaults
        self.prefix = cfg.get("prefix", "Example:")
        self.uppercase = cfg.get("uppercase", False)
        
        # Extract input from previous node results
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            input_value = results[last_key]
        else:
            input_value = ""
            
        return {
            "input": input_value,
            "prefix": self.prefix,
            "uppercase": self.uppercase
        }

    def exec(self, prep_res):
        """
        Execute the node's main logic.
        
        This method contains the core functionality of your node. It receives
        the prepared data from prep() and returns the result to be passed forward.
        """
        input_value = prep_res.get("input", "")
        prefix = prep_res.get("prefix", "Example:")
        uppercase = prep_res.get("uppercase", False)
        
        # Process the input
        result = f"{prefix} {input_value}"
        
        # Apply transformations if needed
        if uppercase:
            result = result.upper()
            
        print(f"ExampleNode processed: '{input_value}' -> '{result}'")
        
        return result

    def post(self, shared, prep_res, exec_res):
        """
        Post-processing after execution.
        
        This method is called after exec() and is used to store results
        in shared memory or perform cleanup operations.
        """
        # Store result for downstream nodes
        super().post(shared, prep_res, exec_res)
        return None


# Example usage:
# {
#   "type": "example",
#   "config": {
#     "prefix": "Processed:",
#     "uppercase": true
#   }
# }
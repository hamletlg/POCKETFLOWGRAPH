import unittest
from backend.nodes.llm import LLMNode
import config

class TestLLMConfigHierarchy(unittest.TestCase):
    def test_default_values(self):
        """Test that defaults from config.py are used when no other info is present."""
        node = LLMNode()
        node.config = {}
        shared = {}
        
        node.prep(shared)
        
        self.assertEqual(node.api_base, config.LLM_BASE_URL)
        self.assertEqual(node.api_key, config.LLM_API_KEY)
        self.assertEqual(node.model, config.LLM_MODEL)

    def test_shared_override(self):
        """Test that shared context (e.g., from Workflow Start) overrides defaults."""
        node = LLMNode()
        node.config = {}
        shared = {
            "llm_base_url": "http://shared-override.com",
            "llm_api_key": "shared-key",
            "llm_model": "shared-model"
        }
        
        node.prep(shared)
        
        self.assertEqual(node.api_base, "http://shared-override.com")
        self.assertEqual(node.api_key, "shared-key")
        self.assertEqual(node.model, "shared-model")

    def test_node_override(self):
        """Test that node-specific config overrides everything."""
        node = LLMNode()
        node.config = {
            "api_base": "http://node-override.com",
            "api_key": "node-key",
            "model": "node-model"
        }
        shared = {
            "llm_base_url": "http://shared-override.com",
            "llm_api_key": "shared-key",
            "llm_model": "shared-model"
        }
        
        node.prep(shared)
        
        self.assertEqual(node.api_base, "http://node-override.com")
        self.assertEqual(node.api_key, "node-key")
        self.assertEqual(node.model, "node-model")

if __name__ == '__main__':
    unittest.main()

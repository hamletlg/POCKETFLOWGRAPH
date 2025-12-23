import unittest
from unittest.mock import MagicMock, patch
import os
import base64
from backend.nodes.llm import LLMNode

class TestLLMNodePayload(unittest.TestCase):
    def setUp(self):
        self.test_image_path = "test_image.txt"
        with open(self.test_image_path, "wb") as f:
            f.write(b"fake_image_content")

    def tearDown(self):
        if os.path.exists(self.test_image_path):
            os.remove(self.test_image_path)

    @patch('backend.nodes.llm.openai.OpenAI')
    def test_image_payload_construction(self, mock_openai):
        # Setup Mock
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="Image analyzed"))]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        # Setup Node
        node = LLMNode()
        node.config = {
            "model": "gpt-4-vision",
            "user_prompt": "Describe this image",
            "image": "{image_path}"
        }
        
        # Shared State
        shared = {
            "results": {
                "prev_node": self.test_image_path
            }
        }
        
        # Execution
        prep_res = node.prep(shared)
        # Manually inject variable into context as it would come from results
        prep_res["context"]["image_path"] = self.test_image_path
        
        result = node.exec(prep_res)
        
        # Verification
        self.assertTrue(result["success"])
        
        # Check call arguments
        call_args = mock_client.chat.completions.create.call_args
        self.assertIsNotNone(call_args)
        
        messages = call_args.kwargs['messages']
        user_message_content = messages[-1]['content']
        
        # Should be a list (multimodal)
        self.assertIsInstance(user_message_content, list)
        self.assertEqual(len(user_message_content), 2)
        
        # Check Text
        self.assertEqual(user_message_content[0]['type'], 'text')
        self.assertEqual(user_message_content[0]['text'], 'Describe this image')
        
        # Check Image
        self.assertEqual(user_message_content[1]['type'], 'image_url')
        image_url = user_message_content[1]['image_url']['url']
        
        expected_base64 = base64.b64encode(b"fake_image_content").decode('utf-8')
        self.assertTrue(image_url.startswith("data:image/jpeg;base64,"))
        self.assertIn(expected_base64, image_url)

    @patch('backend.nodes.llm.openai.OpenAI')
    def test_url_payload_construction(self, mock_openai):
        # Setup Mock
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="URL analyzed"))]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        # Setup Node
        node = LLMNode()
        node.config = {
            "model": "gpt-4-vision",
            "user_prompt": "Describe",
            "image": "http://example.com/image.jpg"
        }
        
        # Shared State
        shared = {"results": {}}
        
        # Execution
        prep_res = node.prep(shared)
        result = node.exec(prep_res)
        
        # Verification
        messages = mock_client.chat.completions.create.call_args.kwargs['messages']
        user_message_content = messages[-1]['content']
        
        self.assertEqual(user_message_content[1]['type'], 'image_url')
        self.assertEqual(user_message_content[1]['image_url']['url'], "http://example.com/image.jpg")

if __name__ == '__main__':
    unittest.main()

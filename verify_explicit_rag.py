
import asyncio
from backend.schemas import Workflow, NodeConfig, Edge
from backend.engine import run_workflow
from backend.node_registry import registry

async def test_explicit_handles():
    print("Testing Explicit Context Handles...")
    
    # Define a simple workflow
    # Start -> LLM (default)
    # Start -> LLM (context) - using the same start as context for simplicity in test
    
    workflow = Workflow(
        nodes=[
            NodeConfig(
                id="node_start",
                type="start",
                label="Start",
                position={"x": 0, "y": 0},
                data={"initial_value": "What is the capital of France?"}
            ),
            NodeConfig(
                id="node_context",
                type="debug",
                label="Knowledge",
                position={"x": 200, "y": 0},
                data={"prefix": "INFO"} 
            ),
            NodeConfig(
                id="node_llm",
                type="llm",
                label="Assistant",
                position={"x": 400, "y": 0},
                data={
                    "user_prompt": "Question: {input}\nContext: {context}\n\nAnswer:",
                    "model": "gpt-3.5-turbo" # dummy
                }
            )
        ],
        edges=[
            Edge(source="node_start", target="node_context", sourceHandle="out-default", targetHandle="in-default"),
            Edge(source="node_context", target="node_llm", sourceHandle="out-default", targetHandle="in-context")
        ]
    )
    
    # We need to mock the LLM call or just check if prep receives the right data.
    # I'll monkeypatch LLMNode.exec to just return the prep data for verification.
    
    from backend.nodes.llm import LLMNode
    original_exec = LLMNode.exec
    
    def mock_exec(self, prep_res):
        print(f"DEBUG MOCK: prep_res keys = {list(prep_res['context'].keys())}")
        # LLMNode.post expects a dict with a 'response' key
        return {"response": prep_res['context'], "success": True}
        
    LLMNode.exec = mock_exec
    
    try:
        result = await run_workflow(workflow)
        print("Workflow completed.")
        
        # Check results
        llm_res = result["results"].get("Assistant")
        print(f"LLM Result: {llm_res}")
        
        if not llm_res:
            print(f"Available results: {list(result['results'].keys())}")
            
        assert llm_res is not None, "Assistant node result not found"
        assert "input" in llm_res, f"'input' missing from llm_res: {llm_res}"
        assert "context" in llm_res, f"'context' missing from llm_res: {llm_res}"
        assert llm_res["input"] == "What is the capital of France?"
        assert llm_res["context"] == "What is the capital of France?" # Since Knowledge node just passed it through
        
        print("✅ Verification Successful: Explicit handles are mapped correctly!")
        
    finally:
        LLMNode.exec = original_exec

if __name__ == "__main__":
    asyncio.run(test_explicit_handles())

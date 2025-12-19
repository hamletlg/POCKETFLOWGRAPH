import threading
import time
import json
from backend.nodes.human import HumanInputNode, pending_requests

def test_hitl_success():
    print("Testing HITL Success Flow...")
    
    # 1. Setup Node
    node = HumanInputNode()
    node.name = "TestApprover"
    node.id = "node_123"
    node.config = {
        "prompt": "Please approve this test",
        "fields": json.dumps([{"name": "comment", "type": "text", "label": "Notes"}])
    }
    
    shared = {"results": {"prev_node": "Some previous output"}}
    prep_res = node.prep(shared)
    
    # 2. Run in thread (simulating workflow execution)
    def run_node():
        nonlocal exec_res
        exec_res = node.exec(prep_res)
    
    exec_res = None
    thread = threading.Thread(target=run_node)
    thread.start()
    
    # 3. Wait for request to appear in pending_requests
    limit = 10
    request_id = None
    while limit > 0:
        if pending_requests:
            request_id = list(pending_requests.keys())[0]
            break
        time.sleep(0.5)
        limit -= 1
    
    if not request_id:
        print("FAILED: No request ID generated")
        return False
    
    print(f"Generated Request ID: {request_id}")
    
    # 4. Simulate User Response (Mimic the API endpoint)
    response_data = {"comment": "All good!", "approved": True}
    pending_requests[request_id]["response"] = response_data
    pending_requests[request_id]["event"].set()
    
    # 5. Wait for node to finish
    thread.join(timeout=5)
    
    if exec_res is None:
        print("FAILED: Node did not finish")
        return False
    
    # 6. Verify Result
    print(f"Exec Result: {exec_res}")
    assert exec_res["success"] is True
    assert exec_res["approved"] is True
    assert exec_res["data"]["comment"] == "All good!"
    
    # Verify post mapping
    node.post(shared, prep_res, exec_res)
    assert shared["memory"]["comment"] == "All good!"
    assert shared["results"]["TestApprover"] == response_data
    
    print("SUCCESS: HITL Success Flow Verified")
    return True

def test_hitl_timeout():
    print("\nTesting HITL Timeout Flow...")
    node = HumanInputNode()
    node.name = "TimeoutNode"
    node.config = {"timeout": 1}
    shared = {"results": {}}
    prep_res = node.prep(shared)
    
    exec_res = node.exec(prep_res)
    print(f"Exec Result (Timeout): {exec_res}")
    assert exec_res["error"] == "Timeout"
    assert exec_res["approved"] is False
    
    print("SUCCESS: HITL Timeout Flow Verified")
    return True

if __name__ == "__main__":
    s1 = test_hitl_success()
    s2 = test_hitl_timeout()
    
    if s1 and s2:
        print("\nALL VERIFICATIONS PASSED!")
    else:
        exit(1)

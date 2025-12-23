import pytest
from fastapi.testclient import TestClient
from backend.main import app
import os
import shutil

client = TestClient(app)

@pytest.fixture
def clean_workspaces():
    # Setup
    yield
    # Teardown: Remove test workspaces
    if os.path.exists("backend/workspaces/test_ws"):
        shutil.rmtree("backend/workspaces/test_ws")

def test_list_workspaces():
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    workspaces = response.json()
    assert "default" in workspaces

def test_create_and_switch_workspace(clean_workspaces):
    # Create
    response = client.post("/api/workspaces", json={"name": "test_ws"})
    assert response.status_code == 200
    assert response.json()["name"] == "test_ws"
    
    # Verify created
    response = client.get("/api/workspaces")
    assert "test_ws" in response.json()
    
    # Switch
    response = client.post("/api/workspaces/active", json={"name": "test_ws"})
    assert response.status_code == 200
    
    # Verify active
    response = client.get("/api/workspaces/active")
    assert response.json()["name"] == "test_ws"
    
    # Switch back to default
    client.post("/api/workspaces/active", json={"name": "default"})

def test_workflow_isolation(clean_workspaces):
    # 1. Ensure we are in default
    client.post("/api/workspaces/active", json={"name": "default"})
    
    # 2. Save a workflow in default
    wf_data = {
        "nodes": [],
        "edges": []
    }
    client.post("/api/workflows/wf_default", json=wf_data)
    
    # 3. Create and switch to new workspace
    client.post("/api/workspaces", json={"name": "test_ws"})
    client.post("/api/workspaces/active", json={"name": "test_ws"})
    
    # 4. List workflows - should be empty (excluding migrated if any, but test_ws should be empty)
    response = client.get("/api/workflows")
    workflows = response.json()
    assert "wf_default" not in workflows
    
    # 5. Save workflow in test_ws
    client.post("/api/workflows/wf_test", json=wf_data)
    
    # 6. Switch back to default
    client.post("/api/workspaces/active", json={"name": "default"})
    
    # 7. List workflows - should have wf_default, NOT wf_test
    response = client.get("/api/workflows")
    workflows = response.json()
    assert "wf_default" in workflows
    assert "wf_test" not in workflows

def test_delete_workspace(clean_workspaces):
    # Create
    client.post("/api/workspaces", json={"name": "test_del"})
    
    # Try delete default - should fail
    response = client.delete("/api/workspaces/default")
    assert response.status_code == 400
    
    # Switch to test_del
    client.post("/api/workspaces/active", json={"name": "test_del"})
    
    # Try delete active - should fail
    response = client.delete("/api/workspaces/test_del")
    assert response.status_code == 400
    
    # Switch back to default
    client.post("/api/workspaces/active", json={"name": "default"})
    
    # Delete test_del
    response = client.delete("/api/workspaces/test_del")
    assert response.status_code == 200
    
    # Verify gone
    response = client.get("/api/workspaces")
    assert "test_del" not in response.json()

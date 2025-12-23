from fastapi import FastAPI, WebSocket, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import uvicorn
import asyncio
import importlib
import os
import json
import inspect
import logging
from .node_registry import registry
from .scheduler import SchedulerService
from .schemas import NodeMetadata, Edge, NodeConfig, Workflow
from .workspace_manager import WorkspaceManager

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PocketFlow Graph Platform")

# Workspaces & Scheduler
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
workspace_manager = WorkspaceManager(ROOT_DIR)
# Initial Migration
legacy_workflows_path = os.path.join(ROOT_DIR, "workflows")
workspace_manager.migrate_legacy_workflows(legacy_workflows_path)

# Initialize Scheduler with current workspace
scheduler = SchedulerService(workspace_manager.get_workflows_dir(workspace_manager.get_current_workspace()))

# WS Manager
from .websockets import manager

@app.on_event("startup")
async def startup_event():
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.stop()

# Helper for Thread-Safe Broadcast
def broadcast_sync(event_type: str, data: dict):
    # data["type"] = event_type
    message = json.dumps({"type": event_type, "data": data})
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
         pass
         
# Better approach: store loop globally
loop_instance = None
@app.on_event("startup")
async def set_loop():
    global loop_instance
    loop_instance = asyncio.get_running_loop()

def event_callback(event, payload):
    # print(f"EVENT_CALLBACK: {event} - {payload} - loop_instance={loop_instance}")
    if loop_instance:
        message = json.dumps({"type": event, "payload": payload})
        # print(f"Broadcasting: {message}")
        asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop_instance)
    else:
        print("WARNING: loop_instance is None, cannot broadcast events")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store (for now) -> move to files later
workflows = {}

@app.get("/")
def read_root():
    return {"message": "PocketFlow Graph Platform API"}

@app.get("/api/nodes", response_model=List[NodeMetadata])
def get_nodes():
    return registry.get_all_metadata()

# --- WORKSPACE ENDPOINTS ---

@app.get("/api/workspaces")
def list_workspaces():
    return workspace_manager.list_workspaces()

@app.post("/api/workspaces")
def create_workspace(name: str = Body(..., embed=True)):
    workspace_manager.create_workspace(name)
    return {"status": "created", "name": name}

@app.get("/api/workspaces/active")
def get_active_workspace():
    return {"name": workspace_manager.get_current_workspace()}

@app.post("/api/workspaces/active")
def set_active_workspace(name: str = Body(..., embed=True)):
    try:
        workspace_manager.set_current_workspace(name)
        # Update scheduler to watch new directory
        new_workflows_dir = workspace_manager.get_workflows_dir(name)
        scheduler.workflows_dir = new_workflows_dir 
        scheduler.refresh_jobs()
        return {"status": "switched", "name": name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/api/workspaces/{name}")
def delete_workspace(name: str):
    try:
        workspace_manager.delete_workspace(name)
        return {"status": "deleted", "name": name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- WORKFLOW ENDPOINTS ---

@app.post("/api/workflow/run")
async def run_workflow_endpoint(workflow: Workflow):
    from .engine import run_workflow
    try:
        # Broadcast Start
        await manager.broadcast(json.dumps({"type": "workflow_start", "payload": {"name": "manual_run"}}))
        
        # Inject Workspace Context
        # We can pass the workspace data path to the engine/nodes
        current_ws = workspace_manager.get_current_workspace()
        data_dir = workspace_manager.get_data_dir(current_ws)
        
        # We assume run_workflow accepts a context or we might need to modify it.
        # For now, let's assume nodes access files relative to CWD or absolute.
        # Ideally, we modify engine.py to accept 'context' dict.
        # Let's check engine.py next. For now, we run as is.
        
        result = await run_workflow(workflow, event_callback)
        
        # Broadcast End
        await manager.broadcast(json.dumps({"type": "workflow_end", "payload": result}))
        
        return result
    except Exception as e:
         await manager.broadcast(json.dumps({"type": "workflow_error", "payload": str(e)}))
         raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/export")
async def export_workflow(workflow: Workflow):
    from .exporter import generate_script
    try:
        script_content = generate_script(workflow)
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(script_content, media_type="text/x-python")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflows")
def list_workflows():
    workflows_dir = workspace_manager.get_workflows_dir(workspace_manager.get_current_workspace())
    if not os.path.exists(workflows_dir):
        return []
    files = [f.replace(".json", "") for f in os.listdir(workflows_dir) if f.endswith(".json")]
    return files

@app.post("/api/workflows/{name}")
async def save_workflow(name: str, workflow: Workflow):
    workflows_dir = workspace_manager.get_workflows_dir(workspace_manager.get_current_workspace())
    os.makedirs(workflows_dir, exist_ok=True)
    file_path = os.path.join(workflows_dir, f"{name}.json")
    
    with open(file_path, "w") as f:
        f.write(workflow.model_dump_json())
        
    # Refresh scheduler
    try:
        scheduler.refresh_jobs()
    except Exception as e:
        logger.error(f"Failed to refresh scheduler: {e}")
        
    return {"status": "saved", "name": name}

@app.get("/api/workflows/{name}")
def load_workflow(name: str):
    workflows_dir = workspace_manager.get_workflows_dir(workspace_manager.get_current_workspace())
    file_path = os.path.join(workflows_dir, f"{name}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    with open(file_path, "r") as f:
        data = json.load(f)
        
    return data

@app.delete("/api/workflows/{name}")
def delete_workflow(name: str):
    workflows_dir = workspace_manager.get_workflows_dir(workspace_manager.get_current_workspace())
    file_path = os.path.join(workflows_dir, f"{name}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    os.remove(file_path)
    
    # Refresh scheduler
    try:
        scheduler.refresh_jobs()
    except Exception as e:
        logger.error(f"Failed to refresh scheduler: {e}")

    return {"status": "deleted", "name": name}

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive / listen
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)


# Log Buffer
log_buffer = []

class ListHandler(logging.Handler):
    def emit(self, record):
        log_buffer.append(self.format(record))
        if len(log_buffer) > 100:
            log_buffer.pop(0)

handler = ListHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logger.addHandler(handler)

@app.get("/api/logs")
def get_logs():
    return log_buffer

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True, timeout_keep_alive=300)

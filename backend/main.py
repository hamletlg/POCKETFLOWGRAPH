from fastapi import FastAPI, WebSocket, HTTPException
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

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PocketFlow Graph Platform")

# Scheduler
workflows_dir = "backend/workflows"
os.makedirs(workflows_dir, exist_ok=True)
scheduler = SchedulerService(workflows_dir)

@app.on_event("startup")
async def startup_event():
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.stop()

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

# In-memory store (for now) -> move to files later
workflows = {}

@app.get("/")
def read_root():
    return {"message": "PocketFlow Graph Platform API"}

@app.get("/api/nodes", response_model=List[NodeMetadata])
def get_nodes():
    return registry.get_all_metadata()

@app.post("/api/workflow/run")
async def run_workflow_endpoint(workflow: Workflow):
    from .engine import run_workflow
    try:
        return await run_workflow(workflow)
    except Exception as e:
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
    workflows_dir = "backend/workflows"
    if not os.path.exists(workflows_dir):
        return []
    files = [f.replace(".json", "") for f in os.listdir(workflows_dir) if f.endswith(".json")]
    return files

@app.post("/api/workflows/{name}")
async def save_workflow(name: str, workflow: Workflow):
    workflows_dir = "backend/workflows"
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
    file_path = f"backend/workflows/{name}.json"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    with open(file_path, "r") as f:
        data = json.load(f)
        
    return data

@app.delete("/api/workflows/{name}")
def delete_workflow(name: str):
    file_path = f"backend/workflows/{name}.json"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    os.remove(file_path)
    
    # Refresh scheduler
    try:
        scheduler.refresh_jobs()
    except Exception as e:
        logger.error(f"Failed to refresh scheduler: {e}")

    return {"status": "deleted", "name": name}

@app.websocket("/api/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    await websocket.send_text(f"Connected to job {job_id}")
    try:
        while True:
            # Simulate logs
            await asyncio.sleep(1)
            await websocket.send_text(f"Job {job_id}: Processing...")
    except Exception:
        print("WS Disconnected")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

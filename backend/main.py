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
from .nodes.human import pending_requests

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PocketFlow Graph Platform")

# Scheduler
workflows_dir = "backend/workflows"
os.makedirs(workflows_dir, exist_ok=True)
scheduler = SchedulerService(workflows_dir)

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
         # If we are in the loop? No, nodes run in thread.
         # But the call comes from a thread, so get_running_loop() might fail or return nothing?
         # Actually uvicorn runs in a main loop.
         # So we need access to THAT loop.
         # We can save it on startup.
         pass
         
# Better approach: store loop globally
loop_instance = None
@app.on_event("startup")
async def set_loop():
    global loop_instance
    loop_instance = asyncio.get_running_loop()

def event_callback(event, payload):
    print(f"EVENT_CALLBACK: {event} - {payload} - loop_instance={loop_instance}")
    if loop_instance:
        message = json.dumps({"type": event, "payload": payload})
        print(f"Broadcasting: {message}")
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
        # Broadcast Start
        await manager.broadcast(json.dumps({"type": "workflow_start", "payload": {"name": "manual_run"}}))
        
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

@app.post("/api/human/respond/{request_id}")
async def human_respond(request_id: str, data: Dict[str, Any]):
    if request_id not in pending_requests:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    
    # Store data and trigger the event
    pending_requests[request_id]["response"] = data
    pending_requests[request_id]["event"].set()
    
    return {"status": "ok", "message": "Signal sent to workflow"}

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
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

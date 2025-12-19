"""
FIXED VERSION of backend/main.py startup event handlers
Replace lines 29-59 in main.py with this consolidated version
"""

# Scheduler
workflows_dir = "backend/workflows"
os.makedirs(workflows_dir, exist_ok=True)
scheduler = SchedulerService(workflows_dir)

# WS Manager
from .websockets import manager

# Global loop instance for thread-safe broadcasting
loop_instance = None

@app.on_event("startup")
async def startup_event():
    global loop_instance
    # Store the event loop for thread-safe WebSocket broadcasting
    loop_instance = asyncio.get_running_loop()
    print(f"DEBUG: Event loop stored: {loop_instance}")
    
    # Start the scheduler
    scheduler.start()
    print("DEBUG: Scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.stop()
    print("DEBUG: Scheduler stopped")

def event_callback(event, payload):
    print(f"EVENT_CALLBACK: {event} - {payload} - loop_instance={loop_instance}")
    if loop_instance is None:
        print("WARNING: loop_instance is None, cannot broadcast events")
        return
        
    try:
        message = json.dumps({"type": event, "payload": payload})
        print(f"DEBUG: Broadcasting message: {message}")
        
        # Schedule the async broadcast on the main event loop
        future = asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop_instance)
        print(f"DEBUG: Broadcast scheduled, future: {future}")
        
        # Optional: Wait for completion (but don't block too long)
        try:
            future.result(timeout=1.0)  # Wait up to 1 second
            print("DEBUG: Broadcast completed successfully")
        except Exception as e:
            print(f"WARNING: Broadcast failed: {e}")
            
    except Exception as e:
        print(f"ERROR: Failed to create or schedule broadcast: {e}")

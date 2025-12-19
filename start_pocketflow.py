
import subprocess
import os
import signal
import sys
import time

def start_services():
    print("🚀 Starting PocketFlow Platform...")
    
    # Get the root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    
    # 1. Start Backend
    print("📦 Starting Backend (Port 8000)...")
    
    # Detect VENV python
    venv_python = os.path.join(root_dir, "venv", "bin", "python")
    if not os.path.exists(venv_python):
        # Fallback for Windows
        venv_python = os.path.join(root_dir, "venv", "Scripts", "python.exe")
    
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    if python_exe == venv_python:
        print(f"🔹 Using Virtual Environment: {venv_python}")
    else:
        print(f"⚠️ VENV not found at {venv_python}, using system python: {python_exe}")

    backend_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=root_dir,
    )
    
    # 2. Wait a bit for backend to initialize
    time.sleep(2)
    
    # 3. Start Frontend
    print("🎨 Starting Frontend (Vite)...")
    try:
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir
        )
    except FileNotFoundError:
        print("❌ Error: 'npm' not found. Please ensure Node.js is installed.")
        backend_process.terminate()
        sys.exit(1)

    print("\n✅ PocketFlow is running!")
    print("🔗 Backend: http://localhost:8000")
    print("🔗 Frontend: http://localhost:5173 (usually)")
    print("\nPress Ctrl+C to stop both services.\n")

    try:
        # Wait for both processes
        while True:
            time.sleep(1)
            if backend_process.poll() is not None:
                print("⚠️ Backend process stopped.")
                break
            if frontend_process.poll() is not None:
                print("⚠️ Frontend process stopped.")
                break
    except KeyboardInterrupt:
        print("\n🛑 Stopping PocketFlow...")
    finally:
        # Graceful shutdown
        backend_process.terminate()
        frontend_process.terminate()
        
        # Give them a moment to close
        time.sleep(1)
        
        # Kill if still alive
        if backend_process.poll() is None: backend_process.kill()
        if frontend_process.poll() is None: frontend_process.kill()
        
        print("👋 Services stopped successfully.")

if __name__ == "__main__":
    start_services()

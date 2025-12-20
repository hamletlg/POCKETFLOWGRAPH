import subprocess
import os
import sys
import time
import signal

def get_venv_executable(name):
    """Finds an executable inside the virtual environment."""
    # Check for standard Unix path (venv/bin/name)
    path = os.path.join(os.getcwd(), "venv", "bin", name)
    
    # Check for Windows path (venv/Scripts/name.exe) if above fails
    if not os.path.exists(path):
        path = os.path.join(os.getcwd(), "venv", "Scripts", f"{name}.exe")
        
    if not os.path.exists(path):
        print(f"⚠️  Could not find '{name}' in virtual environment. Is venv created?")
        sys.exit(1)
    return path

def start_backend():
    print("📦 Starting Backend (Port 8000)...")
    uvicorn_path = get_venv_executable("uvicorn")
    
    # We execute uvicorn directly from the venv path. 
    # No need for 'source activate' or shell=True
    return subprocess.Popen(
        [uvicorn_path, "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=os.getcwd()
    )

def start_frontend():
    print("🎨 Starting Frontend (Vite)...")
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    log_file = os.path.join(frontend_dir, "frontend.log")
    
    # Open file for appending logs
    f = open(log_file, "w")
    
    # shell=True is required for npm usually to resolve PATH correctly
    return subprocess.Popen(
        "npm run dev", 
        cwd=frontend_dir, 
        shell=True, 
        stdout=f, 
        stderr=f
    ), f

def main():
    print("🚀 Starting PocketFlow Platform...")
    
    backend_process = None
    frontend_process = None
    frontend_log_file = None

    try:
        # Start processes and store their Popen objects
        backend_process = start_backend()
        frontend_process, frontend_log_file = start_frontend()

        print("✅ Services are running and the app is available at http://localhost:5173/. Press Ctrl+C to stop.")

        # LOOP FOREVER to keep the script running
        while True:
            time.sleep(1)
            # Optional: Check if processes died unexpectedly
            if backend_process.poll() is not None:
                print("❌ Backend crashed unexpectedly.")
                break
            if frontend_process.poll() is not None:
                print("❌ Frontend crashed unexpectedly.")
                break

    except KeyboardInterrupt:
        print("\n👋 Stopping services...")
    finally:
        # Graceful cleanup
        if backend_process:
            print("   - Killing Backend...")
            backend_process.terminate()
            # backend_process.wait() # Optional: wait for it to actually close
        
        if frontend_process:
            print("   - Killing Frontend...")
            # On Windows/Shell=True, terminate() might not kill the child tree.
            # Usually requires platform specific handling, but basic terminate works for most Linux/Mac setups.
            if sys.platform == "win32":
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)])
            else:
                os.killpg(os.getpgid(frontend_process.pid), signal.SIGTERM) 

        if frontend_log_file:
            frontend_log_file.close()
        
        print("✅ Done.")

if __name__ == "__main__":
    main()

"""
Unified Single-Command Runner for the Entire Food Waste Optimization System.
Starts both the FastAPI Backend (Person B + Person A) and the React Frontend (Person C)
together as ONE integrated process, with automatic health monitoring and graceful shutdown.
"""

import os
import sys
import time
import subprocess
import signal
import urllib.request
import json
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

def check_service(url, timeout=2):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FoodOptimizerRunner"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def kill_proc(proc):
    if not proc:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            proc.terminate()
            proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

def ensure_environment():
    # 1. Ensure backend/data directory exists
    backend_data = os.path.join(ROOT_DIR, "backend", "data")
    os.makedirs(backend_data, exist_ok=True)

    # 2. Ensure .env exists
    env_file = os.path.join(ROOT_DIR, ".env")
    if not os.path.exists(env_file):
        print("[*] Creating local .env configuration...")
        env_content = (
            "CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:3000,http://localhost:80\n"
            "LOG_LEVEL=INFO\n"
            "ENVIRONMENT=local\n"
            "VITE_API_BASE_URL=http://localhost:8000\n"
        )
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)

    # 3. Ensure frontend dependencies are installed
    node_modules = os.path.join(FRONTEND_DIR, "node_modules")
    if not os.path.exists(node_modules):
        print("[*] Installing frontend dependencies (npm install)...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        subprocess.run([npm_cmd, "install"], cwd=FRONTEND_DIR, check=True)

def main():
    print("=" * 70)
    print(" AUTONOMOUS CONTEXT-AWARE FOOD WASTE OPTIMIZATION SYSTEM")
    print(" Starting Entire Stack (FastAPI Backend + ML Engine + React Cockpit)")
    print("=" * 70)

    ensure_environment()

    # 1. Check if backend is already running or start it
    backend_proc = None
    if check_service("http://127.0.0.1:8000/health"):
        print("[OK] FastAPI Backend is already running on http://127.0.0.1:8000")
    else:
        print("[*] Launching FastAPI Backend on http://127.0.0.1:8000 ...")
        backend_cmd = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", "8000"]
        backend_proc = subprocess.Popen(backend_cmd, cwd=ROOT_DIR)

    # 2. Check if frontend is already running or start it
    frontend_proc = None
    if check_service("http://127.0.0.1:5173"):
        print("[OK] React Frontend is already running on http://127.0.0.1:5173")
    else:
        print("[*] Launching React Vite Cockpit on http://127.0.0.1:5173 ...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
            cwd=FRONTEND_DIR
        )

    # 3. Wait for readiness
    print("[*] Waiting for services to synchronize...")
    for _ in range(20):
        b_ok = check_service("http://127.0.0.1:8000/health")
        f_ok = check_service("http://127.0.0.1:5173")
        if b_ok and f_ok:
            break
        time.sleep(1)

    print("\n" + "=" * 70)
    print(" [SUCCESS] ENTIRE INTEGRATED PROJECT IS RUNNING LIVE TOGETHER!")
    print("=" * 70)
    print("  Interactive Web Cockpit:  http://localhost:5173")
    print("  FastAPI Backend API:      http://localhost:8000")
    print("  Interactive Swagger Docs: http://localhost:8000/docs")
    print("  System Health Endpoint:   http://localhost:8000/health")
    print("=" * 70)
    print("Press Ctrl+C to stop all services.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        if backend_proc:
            kill_proc(backend_proc)
        if frontend_proc:
            kill_proc(frontend_proc)
        print("All services stopped cleanly.")

if __name__ == "__main__":
    main()

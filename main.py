import subprocess
import sys
import time
import argparse

def main():
    parser = argparse.ArgumentParser(description="Smart SOC Decision Engine")
    parser.add_argument("--api-only", action="store_true", help="Start only the FastAPI backend")
    parser.add_argument("--dashboard-only", action="store_true", help="Start only the Streamlit dashboard")
    args = parser.parse_args()

    print("Starting Smart SOC Decision Engine...")
    
    api_process = None
    dashboard_process = None

    try:
        if not args.dashboard_only:
            # Start the FastAPI backend
            print("Launching FastAPI Backend on http://127.0.0.1:8000")
            api_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "api.router:app", "--host", "127.0.0.1", "--port", "8000"],
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
            # Give the backend a moment to start before launching the dashboard
            time.sleep(2)

        if not args.api_only:
            # Start the Streamlit dashboard
            print("Launching Streamlit Dashboard...")
            dashboard_process = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "dashboard.py"],
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
        # Keep the main thread alive, waiting for both processes
        if api_process:
            api_process.wait()
        if dashboard_process:
            dashboard_process.wait()
            
    except KeyboardInterrupt:
        print("\nShutting down Smart SOC Decision Engine processes...")
        if api_process:
            api_process.terminate()
        if dashboard_process:
            dashboard_process.terminate()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()

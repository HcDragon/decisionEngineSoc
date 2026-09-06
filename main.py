import os
import subprocess
import sys
import time
import argparse

def get_python_interpreter() -> str:
    """Finds a Python interpreter that has required dependencies (uvicorn, streamlit, fastapi) installed."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "venv_mac", "bin", "python3"),
        sys.executable,
        "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3",
        os.path.join(base_dir, "venv", "bin", "python3"),
    ]
    for cand in candidates:
        if cand and os.path.exists(cand):
            try:
                res = subprocess.run([cand, "-c", "import uvicorn, streamlit, fastapi"], capture_output=True)
                if res.returncode == 0:
                    return cand
            except Exception:
                pass
    return sys.executable

def main():
    parser = argparse.ArgumentParser(description="Smart SOC Unified Decision Engine & AI/ML IDS")
    parser.add_argument("--api-only", action="store_true", help="Start only the FastAPI backend")
    parser.add_argument("--dashboard-only", action="store_true", help="Start only the Streamlit dashboard")
    parser.add_argument("--no-feed", action="store_true", help="Disable the continuous live AI/ML threat flow pipeline")
    parser.add_argument("--with-feed", action="store_true", help="Explicitly enable ML feed (enabled by default)")
    parser.add_argument("--samples", type=int, default=300, help="Number of samples to feed through ML pipeline")
    parser.add_argument("--feed-delay", type=float, default=1.5, help="Delay between threat event inferences (seconds)")
    args = parser.parse_args()

    py_bin = get_python_interpreter()

    print("=" * 70)
    print("  SMART SOC UNIFIED AI/ML DETECTION & AUTONOMOUS DECISION ENGINE")
    print("=" * 70)
    print(f"[*] Active Python Runtime : {py_bin}")
    
    api_process = None
    dashboard_process = None
    feed_process = None

    try:
        if not args.dashboard_only:
            # Start the FastAPI backend
            print("[1/3] Launching FastAPI Backend on http://127.0.0.1:8000 ...")
            api_process = subprocess.Popen(
                [py_bin, "-m", "uvicorn", "decision_engine.api.routes:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
            # Give backend a moment to initialize
            time.sleep(2)

        if not args.api_only:
            # Start the Streamlit dashboard
            print("[2/3] Launching Streamlit Unified SOC Dashboard on http://localhost:8501 ...")
            dashboard_process = subprocess.Popen(
                [py_bin, "-m", "streamlit", "run", "dashboard.py"],
                stdout=sys.stdout,
                stderr=sys.stderr
            )

        # Run feed by default unless user specified --no-feed or single-component mode
        should_run_feed = not args.no_feed and not args.api_only and not args.dashboard_only
        if should_run_feed:
            time.sleep(2.5)
            print(f"[3/3] Launching Native AI/ML Threat Detection Feed (delay={args.feed_delay}s) ...")
            feed_process = subprocess.Popen(
                [py_bin, "run_pipeline.py", "--samples", str(args.samples), "--delay", str(args.feed_delay)],
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
        print("\nAll Smart SOC services active. Press Ctrl+C to stop all services.\n")
        
        # Keep main thread alive, waiting for processes
        while True:
            time.sleep(1)
            # Check if any main process crashed
            if api_process and api_process.poll() is not None:
                print("[-] FastAPI process exited unexpectedly.")
                break
            if dashboard_process and dashboard_process.poll() is not None:
                print("[-] Dashboard process exited.")
                break

    except KeyboardInterrupt:
        print("\nShutting down Smart SOC Decision Engine processes...")
    finally:
        if feed_process and feed_process.poll() is None:
            feed_process.terminate()
        if api_process and api_process.poll() is None:
            api_process.terminate()
        if dashboard_process and dashboard_process.poll() is None:
            dashboard_process.terminate()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()

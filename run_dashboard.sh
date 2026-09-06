#!/bin/bash
# ==============================================================================
# SmartSOC Dashboard Launcher
# Automatically uses the virtual environment with Streamlit installed
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "venv_mac/bin/python3" ]; then
    PYTHON_EXEC="venv_mac/bin/python3"
elif [ -f "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" ]; then
    PYTHON_EXEC="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
else
    PYTHON_EXEC="python3"
fi

echo "[*] Launching SmartSOC Dashboard via $PYTHON_EXEC on http://localhost:8501 ..."
exec "$PYTHON_EXEC" -m streamlit run dashboard.py "$@"

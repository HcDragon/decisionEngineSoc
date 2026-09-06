#!/bin/bash
# ==============================================================================
# SmartSOC Test Runner
# Automatically targets the virtual environment with pytest installed
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "venv_mac/bin/python3" ]; then
    PYTHON_EXEC="./venv_mac/bin/python3"
else
    PYTHON_EXEC="python3"
fi

echo "[*] Running Pytest test suite via $PYTHON_EXEC ..."
exec "$PYTHON_EXEC" -m pytest tests/ "$@"

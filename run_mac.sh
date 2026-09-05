#!/bin/bash
# ==============================================================================
# Smart SOC Decision Engine - MacBook Air M4 (macOS Apple Silicon) Launcher
# ==============================================================================

set -e

echo "===================================================================="
echo "  SmartSOC Decision Engine - macOS (Apple Silicon M4) Startup Script"
echo "===================================================================="

# Determine project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "[-] Error: Python 3 not found. Install via Homebrew: brew install python@3.11"
    exit 1
fi

echo "[+] Python version: $(python3 --version)"

# Check for Apple Silicon architecture
ARCH=$(uname -m)
echo "[+] Detected architecture: $ARCH (macOS Apple Silicon)"

# Create virtual environment if not present
if [ ! -d "venv_mac" ]; then
    echo "[+] Creating virtual environment 'venv_mac'..."
    python3 -m venv venv_mac
fi

# Activate virtual environment
source venv_mac/bin/activate

# Upgrade pip and install requirements
echo "[+] Checking requirements..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Optional: Install nfstream if libpcap is available
if command -v brew &>/dev/null; then
    if ! brew list libpcap &>/dev/null; then
        echo "[*] Optional: For live en0 packet sniffing, run: brew install libpcap && pip install nfstream"
    fi
fi

# Auto-detect IDS Project directory
if [ -z "$IDS_PROJECT_DIR" ]; then
    if [ -d "../AimlProject/ids_project" ]; then
        export IDS_PROJECT_DIR="$(cd ../AimlProject/ids_project && pwd)"
    elif [ -d "../ids_project" ]; then
        export IDS_PROJECT_DIR="$(cd ../ids_project && pwd)"
    elif [ -d "$HOME/AimlProject/ids_project" ]; then
        export IDS_PROJECT_DIR="$HOME/AimlProject/ids_project"
    elif [ -d "$HOME/ids_project" ]; then
        export IDS_PROJECT_DIR="$HOME/ids_project"
    fi
fi

if [ -n "$IDS_PROJECT_DIR" ]; then
    echo "[+] Linked upstream AI/ML IDS directory: $IDS_PROJECT_DIR"
else
    echo "[!] Note: Set IDS_PROJECT_DIR if ids_project is in a custom path:"
    echo "    export IDS_PROJECT_DIR=/path/to/ids_project"
fi

echo "[+] Launching SmartSOC Manager on macOS..."
echo "    FastAPI Backend:     http://127.0.0.1:8000/docs"
echo "    Streamlit Dashboard: http://localhost:8501"
echo "===================================================================="

python3 main.py

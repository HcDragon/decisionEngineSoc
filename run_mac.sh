#!/usr/bin/env bash
# ==============================================================================
# AI-Based Smart SOC Manager — macOS Setup & Launch Script
# Compatible with Apple Silicon (M1/M2/M3/M4) & Intel Macs
# ==============================================================================

set -e

# Change directory to script location (project root)
cd "$(dirname "$0")"

echo "=========================================================="
echo "  AI-Based Smart SOC Manager (macOS Launcher)"
echo "=========================================================="

# 1. Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "[-] Python 3 not found. Please install Python via Homebrew: 'brew install python'"
    exit 1
fi
echo "[+] Detected $(python3 --version)"

# 2. Check Node & npm
if ! command -v npm &>/dev/null; then
    echo "[-] Node/npm not found. Please install Node via Homebrew: 'brew install node'"
    exit 1
fi
echo "[+] Detected Node $(node -v) / npm $(npm -v)"

# 3. Virtual Environment Setup
if [ ! -d ".venv" ]; then
    echo "[*] Creating Python virtual environment in .venv..."
    python3 -m venv .venv
fi

echo "[*] Activating virtual environment..."
source .venv/bin/activate

# 4. Install Dependencies
echo "[*] Verifying Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r soc/backend/requirements.txt

# 5. Environment configuration (.env)
if [ ! -f ".env" ]; then
    echo "[*] Initializing .env with SQLite for local Mac dev..."
    cp .env.example .env
    sed -i '' 's|^DATABASE_URL=postgresql.*|# DATABASE_URL=postgresql...|g' .env 2>/dev/null || true
    sed -i '' 's|^# DATABASE_URL=sqlite:///./soc.db|DATABASE_URL=sqlite:///./soc.db|g' .env 2>/dev/null || true
    if ! grep -q "DATABASE_URL=sqlite:///./soc.db" .env; then
        echo "DATABASE_URL=sqlite:///./soc.db" >> .env
    fi
fi

# 6. Seed Database
echo "[*] Initializing schema and seed telemetry..."
python3 -m soc.backend.app.db.seed

# 7. Dashboard dependencies
if [ ! -d "soc/dashboard/node_modules" ]; then
    echo "[*] Installing dashboard npm packages..."
    (cd soc/dashboard && npm install)
fi

# 8. macOS Packet Capture Guidance
echo ""
echo "----------------------------------------------------------"
echo "  macOS Network Packet Capture (NFStream):"
echo "  - By default, macOS requires permissions to tap physical NICs."
echo "  - To allow unprivileged real packet capture on Wi-Fi (en0):"
echo "      sudo chmod o+r /dev/bpf*"
echo "  - If omitted, safe emulation tap is automatically used."
echo "----------------------------------------------------------"
echo ""

# 9. Startup options
echo "Choose how to start:"
echo "  1) Start Both Backend API and Dashboard (Concurrently)"
echo "  2) Start Backend API only (Port 8000)"
echo "  3) Start Dashboard only (Port 3000)"
echo "  4) Run Pytest Test Suite"
echo ""

read -p "Select option [1-4] (default: 1): " choice
choice=${choice:-1}

case $choice in
    1)
        echo "[+] Starting Backend on http://localhost:8000..."
        python3 -m uvicorn soc.backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
        BACKEND_PID=$!

        echo "[+] Starting Dashboard on http://localhost:3000..."
        (cd soc/dashboard && npm run dev) &
        FRONTEND_PID=$!

        trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM EXIT
        wait
        ;;
    2)
        echo "[+] Starting Backend on http://localhost:8000..."
        exec python3 -m uvicorn soc.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    3)
        echo "[+] Starting Dashboard on http://localhost:3000..."
        cd soc/dashboard && exec npm run dev
        ;;
    4)
        echo "[*] Running pytest test suite..."
        python3 -m pytest soc/backend/tests -v
        ;;
    *)
        echo "Invalid selection."
        exit 1
        ;;
esac

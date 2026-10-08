#!/usr/bin/env bash
# ==============================================================================
# AI-Based Smart SOC Manager — Linux (Ubuntu/Debian) Setup & Launch Script
# Configures the SOC server for REAL network-flow capture via NFStream.
# ==============================================================================
set -e
cd "$(dirname "$0")"

# --- Python version for the venv -------------------------------------------
# NFStream (6.5.x) does NOT ship wheels for Python 3.14. If a 3.12/3.11 is
# present we use it for the venv so native packet capture can be installed.
PYBIN=""
for cand in python3.12 python3.11 python3.13 python3; do
    if command -v "$cand" &>/dev/null; then PYBIN="$cand"; break; fi
done
echo "[*] Using interpreter: $PYBIN ($($PYBIN --version 2>&1))"
case "$($PYBIN --version 2>&1)" in
    *3.14*|*3.15*)
        echo "[-] $PYBIN is 3.14+. NFStream has no wheel for it and venv/ensurepip"
        echo "    is unavailable, so the venv would be broken. Install python3.12 first:"
        echo "      sudo add-apt-repository -y ppa:deadsnakes/ppa"
        echo "      sudo apt update && sudo apt install -y python3.12 python3.12-venv python3.12-dev"
        echo "    then re-run this script (it will auto-pick python3.12)."
        exit 1
        ;;
esac

# --- System prerequisites (needs sudo) -------------------------------------
echo "[*] Installing system prerequisites (sudo required)..."
sudo apt update
sudo apt install -y \
    "${PYBIN}-venv" "${PYBIN}-dev" python3-pip \
    libpcap-dev tcpdump build-essential \
    nodejs npm || {
        echo "[-] apt install failed. Install the packages listed above manually."; exit 1; }

# --- Python virtual environment --------------------------------------------
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment (.venv) with $PYBIN..."
    "$PYBIN" -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip wheel
echo "[*] Installing backend Python dependencies..."
pip install -r soc/backend/requirements.txt

# --- Database seed ----------------------------------------------------------
echo "[*] Seeding schema and demo telemetry (SQLite: soc.db)..."
python -m soc.backend.app.db.seed

# --- Dashboard deps ---------------------------------------------------------
if [ ! -d "soc/dashboard/node_modules" ]; then
    echo "[*] Installing dashboard npm packages..."
    (cd soc/dashboard && npm install)
fi

# --- Packet capture permission (real flows without running as root) --------
echo "[*] Granting packet-capture capability to the venv interpreter..."
VENV_PY="$(readlink -f .venv/bin/python)"
sudo setcap cap_net_raw,cap_net_admin+eip "$VENV_PY" || \
    echo "[!] setcap failed — you can still capture by launching uvicorn with sudo."
getcap "$VENV_PY" || true

cat <<'EOF'

----------------------------------------------------------------------
 Setup complete. To test REAL network flow capture:

   source .venv/bin/activate
   python -m uvicorn soc.backend.app.main:app --host 0.0.0.0 --port 8000

 Then in another terminal:
   # start the monitor and point it at a port you will send traffic to
   curl -X POST http://localhost:8000/api/traffic/start
   # confirm it is in NATIVE capture mode (not emulation):
   curl -s http://localhost:8000/api/traffic/status | grep engine_mode
   # generate some real traffic to that port, e.g.:
   curl http://localhost:8000/health
   # watch real flows arrive:
   curl -s http://localhost:8000/api/traffic/flows?limit=10

 engine_mode must read "native_nfstream". If it says "emulated_stream",
 the interpreter lacks capture capability (re-run the setcap step) or
 NFStream failed to import (check Python version / libpcap-dev).
----------------------------------------------------------------------
EOF

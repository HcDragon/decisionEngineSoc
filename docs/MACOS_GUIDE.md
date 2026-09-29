# macOS & MacBook Setup Guide (Apple Silicon & Intel)

This guide explains how to set up, run, and develop the **AI-Based Smart SOC Manager** on macOS (compatible with M1/M2/M3/M4 Apple Silicon and Intel MacBooks).

---

## Prerequisites (via Homebrew)

Open your macOS Terminal and verify or install Python 3 and Node.js:

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3, Node, and libpcap
brew install python node libpcap
```

---

## Option 1: One-Click Launch Script (Recommended)

We provide a dedicated launcher script that handles virtual environment creation, dependencies, SQLite configuration, and starts both backend and dashboard:

```bash
# Make script executable
chmod +x run_mac.sh

# Run the launcher
./run_mac.sh
```

It will present an interactive menu:
1. **Start Both Backend and Dashboard** (`http://localhost:8000` & `http://localhost:3000`)
2. **Start Backend Only**
3. **Start Dashboard Only**
4. **Run Test Suite**

---

## Option 2: Using the Makefile

The [Makefile](../Makefile) is fully cross-platform for macOS and Linux:

```bash
# 1. Install all dependencies
make install

# 2. Seed database
make seed

# 3. Run backend
make api

# 4. In a second terminal, run dashboard
make dashboard

# 5. Run tests
make test
```

---

## Option 3: Docker & Docker Compose on Mac

If you have **Docker Desktop for Mac** (Apple Silicon or Intel):

```bash
# Start all containers (Postgres, API, Dashboard)
docker compose up -d

# View status
docker compose ps

# View logs
docker compose logs -f

# Stop
docker compose down
```

All base images (`python:3.11-slim`, `postgres:16-alpine`, `node:20-alpine`, `nginx:alpine`) are natively compiled for `linux/arm64` (Apple Silicon).

---

## macOS Network Packet Capture (NFStream on Mac)

On macOS, low-level packet capture uses the BSD Berkeley Packet Filter (`/dev/bpf*`).

### 1. Safe Emulation Mode (Default)
If run without root permissions, the system automatically runs in safe emulation mode so everything (dashboard, metrics, IDS inference) works without requiring system privileges.

### 2. Live Wi-Fi / Ethernet Sniffing
To allow NFStream to capture real live packets on your Mac's Wi-Fi adapter (`en0`):

```bash
# Grant read access to macOS BPF devices:
sudo chmod o+r /dev/bpf*
```

Once granted, NFStreamer will bind to the active macOS network adapter without needing `sudo`.

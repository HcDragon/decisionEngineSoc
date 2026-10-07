# Live Demo & Attack Simulation Guide

How to demonstrate the AI-Based Smart SOC Manager in front of judges using
**two machines** on an isolated lab network:

| Role | Machine | Runs |
|------|---------|------|
| **SOC Server + Target** | Native Ubuntu | Backend API (`:8000`), Dashboard (`:3000`), ML model | 
| **Attacker** | VM (bridged networking) | Attack + benign traffic scripts aimed at the SOC server |

> ⚠️ **Scope:** Every command below targets *your own* SOC server on *your own*
> isolated lab subnet. These tools (nmap, hping3, hydra, arpspoof) generate real
> packets — only run them against the demo machine you control, never a network
> you don't own. Use a host-only / bridged lab segment with nothing else on it.

---

## 0. What is "real" in this demo (read this first)

Be honest with judges about what each part proves — it makes the demo stronger,
not weaker.

| Track | What it shows | Is the AI actually running? |
|-------|---------------|-----------------------------|
| **A — Model replay** (`simulate.py`) | The trained Random Forest classifying real CICIDS-style attack flows in real time, with live accuracy | ✅ **Yes** — real model, real attack feature data |
| **B — Live network attacks** (VM → server) | Real packets (floods, scans, brute force, ARP spoof) captured by NFStream and shown on the dashboard's Live Traffic monitor | ⚠️ Partial — real packets are captured, but the live monitor does **not** yet run the model on them (see note below) |

**The gap to know about:** In [`app/monitor/streamer.py`](../soc/backend/app/monitor/streamer.py),
native NFStream flows are recorded as `Benign Traffic` and the model is loaded but
not invoked per-flow. The **emulation fallback** (used when no packet-capture
permission is available) *does* inject labelled attacks (~15%). So:

- To show **real AI classification** → use **Track A**.
- To show a **live, moving dashboard** → use **Track B**; either run it in
  emulation mode (attacks appear automatically) or wire live classification in
  (see §6).

Present Track A as "this is our detection brain" and Track B as "this is the
live SOC console it feeds." Run them side by side on two monitors if you can.

---

## 1. Prerequisites

### On the SOC Server (native Ubuntu)
```bash
# System deps for packet capture + builds
sudo apt update
sudo apt install -y python3-venv python3-pip nodejs npm libpcap-dev tcpdump

# Project deps (from repo root)
python3 -m venv .venv && source .venv/bin/activate
pip install -r soc/backend/requirements.txt
pip install -r ids_project/requirements.txt

# Dashboard deps
(cd soc/dashboard && npm install)
```

Make sure the model artifacts exist in `ids_project/`:
`model.pkl`, `label_encoder.pkl`, `scaler.pkl`, `feature_names.pkl`.
(If missing: `cd ids_project && python train_model.py` — needs the dataset CSV.)

### On the Attacker VM
```bash
sudo apt update
sudo apt install -y nmap hping3 hydra dsniff curl apache2-utils iperf3
# dsniff provides arpspoof; apache2-utils provides `ab`
```

### Network check (both machines)
```bash
ip -4 addr          # note each machine's IP, e.g. server 10.10.1.5, VM 10.10.1.20
ping -c3 <server-ip>   # from the VM, confirm reachability
```
For the ARP-spoofing step the two machines **must be on the same subnet / L2
segment** — use **bridged** networking for the VM, not NAT.

---

## 2. Start the SOC server (Ubuntu)

```bash
# Terminal 1 — backend (capturing real packets needs privilege)
source .venv/bin/activate
# Optional: let the monitor capture without full root
sudo setcap cap_net_raw,cap_net_admin=eip $(readlink -f $(which python3))
python3 -m uvicorn soc.backend.app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — dashboard
cd soc/dashboard && npm run dev -- --host 0.0.0.0
```

Open the dashboard from any machine on the lab net: `http://<server-ip>:3000`
Verify the API: `curl http://<server-ip>:8000/health`

**Point the live monitor at the port you'll attack.** The dashboard's Live
Traffic page (or the API) switches the monitored port:
```bash
# e.g. monitor HTTP so nmap/hping against :80 show up
curl -X POST http://<server-ip>:8000/api/traffic/port -H 'Content-Type: application/json' -d '{"port":80}'
```

---

## 3. Track A — Real AI model on real attack data (on the server)

This is the centerpiece: the actual trained model classifying real attack flows,
live, with a running accuracy count.

```bash
cd ids_project
source ../.venv/bin/activate
python simulate.py
```

You'll see a live feed like:
```
[  1/160] Predicted: DoS SYN Flood            Actual: DoS SYN Flood            ✓
[  2/160] Predicted: Dictionary Brute Force   Actual: Dictionary Brute Force   ✓
...
  Correct: 156/160 | Accuracy: 97.5%
```

Tuning knobs in [`simulate.py`](simulate.py):
- `ROWS_PER_FILE` — how many flows per attack type (raise for a longer feed)
- `DELAY_SECONDS` — pacing (`0.5` reads nicely on a projector; lower = faster)

> Talking point: the model recognises these **attack families** — DoS floods
> (SYN/UDP/DNS/ICMP), Recon (ping sweep / OS scan), Dictionary Brute Force,
> and MITM ARP Spoofing — the same families the Decision Engine scores and
> maps to playbooks in [`soc/config/policies.yaml`](../soc/config/policies.yaml).

---

## 4. Track B — Real attack traffic from the VM → SOC server

Run each from the **Attacker VM**, with `SERVER=<server-ip>`. Watch the
dashboard's Live Traffic / overview update on the server. Run one at a time so
judges can see each attack type land.

```bash
SERVER=10.10.1.5      # <-- set to your SOC server IP
```

### 4a. Benign baseline (do this first — establishes "normal")
```bash
# Steady legitimate HTTP load
ab -n 2000 -c 20 http://$SERVER:80/        # needs a listener on :80, see note
while true; do curl -s http://$SERVER:8000/health >/dev/null; sleep 0.5; done
```

### 4b. Reconnaissance — port / OS scan (maps to `recon` family)
```bash
nmap -sS -T4 $SERVER                 # SYN port scan
nmap -O $SERVER                      # OS fingerprint
nmap -sn 10.10.1.0/24                # ping sweep / host discovery
```

### 4c. DoS flood (maps to `dos_flood` family)
```bash
# SYN flood against the monitored port (Ctrl-C after ~10-15s)
sudo hping3 -S --flood -p 80 $SERVER
# UDP flood
sudo hping3 --udp --flood -p 53 $SERVER
# ICMP flood
sudo hping3 --icmp --flood $SERVER
```

### 4d. Dictionary brute force (maps to `brute_force` family)
```bash
# Requires an auth service on the target (e.g. SSH on the server).
# Use a tiny wordlist for a quick demo:
printf 'admin\nroot\npassword\n123456\nletmein\n' > /tmp/wl.txt
hydra -l admin -P /tmp/wl.txt ssh://$SERVER
```

### 4e. MITM ARP spoofing (maps to `mitm` family — needs same L2)
```bash
GATEWAY=10.10.1.1    # your lab gateway
sudo sysctl -w net.ipv4.ip_forward=1
sudo arpspoof -i eth0 -t $SERVER $GATEWAY     # Ctrl-C to stop
```

> **Why some of these need a listener:** NFStream meters flows to/from the
> monitored port. For `ab`/brute-force to produce flows, the server must have
> something listening (an HTTP server on `:80`, `sshd` for hydra). Quick HTTP
> target on the server: `python3 -m http.server 80`.

---

## 5. Suggested 5-minute demo script

1. **(30s)** Dashboard up, show it idle/healthy → "this is the SOC console."
2. **(90s)** Run **Track A** `simulate.py` → "our Random Forest classifying real
   attacks live at ~97% accuracy." Point at the families.
3. **(90s)** From the VM, fire **4b recon → 4c SYN flood** → watch Live Traffic
   spike, protocol distribution shift, top-sources fill with the attacker IP.
4. **(60s)** Open [`policies.yaml`](../soc/config/policies.yaml) → "each family
   maps to a playbook and a mode — DoS → rate-limit (recommend), brute force →
   auto-lockout, MITM → isolate." Show `recommend_only` as the safety default.
5. **(30s)** Flip automation mode via the dashboard kill-switch → close on safety
   (dry-run by default, nothing touches real networks).

---

## 6. Optional: make Track B show *real* model-classified attacks

If you want live captured packets to be labelled by the model (not just metered),
wire the classifier into the flow recorder. In
[`app/monitor/streamer.py`](../soc/backend/app/monitor/streamer.py),
`_record_native_flow()` already has the model loaded (`self._model`,
`self._scaler`, `self._encoder`, `self._feature_names`) — build a feature vector
from the NFStream flow aligned to `self._feature_names`, run
`self._encoder.inverse_transform(self._model.predict(self._scaler.transform(X)))`,
and set `threat_label` / `is_threat` / `confidence` from the result.

Caveat noted in [`docs/ASSUMPTIONS.md`](../docs/ASSUMPTIONS.md): the training
dataset has no IP columns and `Src Port` is an influential (capture-artifact)
feature, so live NFStream features won't line up 1:1 with the model's expected
columns — expect to map/fill a subset. **If you're short on time before the
demo, don't attempt this live — rely on Track A for real detection and run
Track B in emulation mode for the moving dashboard.**

Emulation mode (automatic attack labels, no wiring needed): run the backend
**without** packet-capture privilege (skip the `setcap` step / don't use sudo),
and the monitor falls back to the labelled emulation stream.

---

## 7. Cleanup (after the demo)

```bash
# Attacker VM
sudo pkill hping3 ; sudo pkill arpspoof
sudo sysctl -w net.ipv4.ip_forward=0

# SOC server
curl -X POST http://localhost:8000/api/traffic/clear   # flush flow buffer
# Ctrl-C the uvicorn and vite terminals
```

---

## 8. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dashboard can't reach API from another machine | Start uvicorn/vite with `--host 0.0.0.0`; open firewall: `sudo ufw allow 8000,3000/tcp` |
| Live Traffic stays empty | Monitored port ≠ attacked port — set it via `/api/traffic/port`; confirm a listener exists on that port |
| Engine shows `emulated_stream` not `native_nfstream` | No capture permission — run with the `setcap` step above, or accept emulation for the demo |
| `simulate.py` can't find model | Run from inside `ids_project/`; ensure the four `.pkl` files are present |
| ARP spoof does nothing | VM must be **bridged**, same subnet as the server; enable `ip_forward` |
| nmap/hydra flows don't appear | Target needs an open service (`python3 -m http.server 80`, `sshd`) |

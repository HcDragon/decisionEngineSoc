# SOC Manager — Live Attack & Defence Demonstration

End-to-end walkthrough for demoing the **AI-Based Smart SOC Manager**: start the
backend + dashboard, launch real attack traffic, watch the decision engine raise
incidents, and show **Automatic** vs **Manual** defence from the UI.

Everything here is lab-only and safe by default. Nothing touches a real network
unless you explicitly arm the namespace lab (`SOC_EXECUTOR=lab`), which is
confined to the isolated `10.66.0.0/24` test subnet.

---

## 0. What's in the box

| Piece | Path | Role |
|-------|------|------|
| Backend API + engine | `soc/backend` | capture → classify → decide → respond |
| Dashboard (React/Vite) | `soc/dashboard` | live flows, incidents, defence toggle |
| No-sudo traffic generator | `scripts/gen_traffic.py` | real recon/flood packets, no root/tools |
| Attack-lab installer | `scripts/setup_attack_lab.sh` | installs nmap/hydra/hping3 + Juice Shop |
| No-sudo live test | `scripts/run_live_test.sh` | one-shot detection smoke test |
| Namespace defence lab | `testlab/*.sh` | isolated attacker netns + **real** nft blocking |
| One-command acceptance | `testlab/acceptance.sh` | full attack→block→TTL-recovery proof |

---

## 1. Prerequisites (one time)

```bash
cd ~/Desktop/Rashomon
./run_linux.sh            # builds the Python 3.12 venv + installs deps
```

- Requires **Python 3.12** (nfstream has no 3.14 wheel). `run_linux.sh` picks it
  automatically and hard-fails on 3.14.
- For **real packet capture** (optional — otherwise it falls back to an emulated
  tap):
  ```bash
  sudo setcap cap_net_raw,cap_net_admin+eip /usr/bin/python3.12
  ```
- Dashboard deps (first run only):
  ```bash
  cd soc/dashboard && npm install && cd -
  ```

> **If `vite` fails with `EACCES … node_modules/.vite-temp`:** an earlier `sudo`
> run left a root-owned temp dir. Clear it once with
> `sudo rm -rf soc/dashboard/node_modules/.vite-temp`. Same for a root-owned
> `soc.db`: `sudo rm -f soc.db`.

---

## 2. Quick demo — no sudo, no extra tools (≈2 min)

The fastest path. Generates real packets whose flow-shape trips the heuristic
detector, with no nmap/root required.

### 2a. Start the backend
```bash
source .venv/bin/activate
python -m soc.backend.app.db.seed            # clean seed
python -m uvicorn soc.backend.app.main:app --host 0.0.0.0 --port 8000
```
Check the engine mode:
```bash
curl -s localhost:8000/api/traffic/status | python -m json.tool | grep engine_mode
# native_nfstream  = real capture (setcap done)   |   emulated_stream = fallback
```

### 2b. Start the dashboard (second terminal)
```bash
cd soc/dashboard
npm run dev -- --host 0.0.0.0 --port 3001
# open http://localhost:3001
```

### 2c. Fire attacks (third terminal)
```bash
# Recon scan -> 'Recon OS Scan' incident
curl -s -XPOST localhost:8000/api/traffic/port -H 'Content-Type: application/json' -d '{"port":9999}'
.venv/bin/python scripts/gen_traffic.py recon --port 9999 --count 80

# DoS flood -> 'DoS SYN Flood' incident
curl -s -XPOST localhost:8000/api/traffic/port -H 'Content-Type: application/json' -d '{"port":9900}'
.venv/bin/python scripts/gen_traffic.py flood --port 9900 --packets 600
```

Or run the whole thing in one shot:
```bash
./scripts/run_live_test.sh
```

### 2d. Watch it land
- **Dashboard:** incidents appear in **Active SOC Incidents**; threat flows turn
  red in the live table.
- **API:**
  ```bash
  curl -s localhost:8000/api/incidents | python -m json.tool
  curl -s localhost:8000/api/audit/verify          # hash chain intact
  ```

---

## 3. Automatic vs Manual defence (the headline UI feature)

The **Defence Mode** switch lives in the dashboard header. It drives the global
automation kill-switch (`POST /system/mode`):

| UI button | Automation mode | Behaviour |
|-----------|-----------------|-----------|
| **AUTOMATIC** | `auto` | Engine contains malicious sources on its own. Incidents show an *Auto-contained* badge. |
| **MANUAL** *(switch to this)* | `recommend_only` | Engine only **proposes**; you click **Block** per incident. |
| **OFF** | `off` | Monitor only, no containment. |

**Default is Automatic.** To demo manual control:

1. Click **MANUAL** in the header. The incidents panel banner turns cyan:
   *"Manual defence — review each incident and click Block to contain it."*
2. Launch an attack (section 2c). An incident appears with a red **Block** button.
3. Click **Block** → the source is contained (virtual-firewall entry created,
   incident → `contained`, analyst approval + action recorded in the audit chain).
4. A **Release** button replaces it → click to lift containment (TTL also expires
   it automatically).

Under the hood these buttons call:
```
POST /api/incidents/{id}/respond      # block_ip (analyst-approved)
POST /api/incidents/{id}/release      # lift containment
```
Both honour the executor guardrails: `simulated`/`dry_run` only write DB-tracked
virtual-firewall rows (zero real side effects); the `lab` executor additionally
applies a real `nft` rule (section 4).

Verify from the API:
```bash
curl -s localhost:8000/api/firewall | python -m json.tool      # active blocks
curl -s localhost:8000/api/incidents/1 | python -m json.tool   # decisions + actions
```

---

## 4. Full defence lab — REAL nft blocking (sudo, isolated)

Proves containment end-to-end: a real SSH brute-force from an isolated attacker
namespace is detected, **auto-blocked with a real `nft` drop rule**, the attacker
genuinely loses reachability, then recovers when the block's TTL expires.

> Confined to `10.66.0.0/24` in a network namespace with **no default route**
> (no internet, no LAN). Rules live in a dedicated `inet soc_lab` table so
> teardown never touches the host firewall.

### One command
```bash
sudo bash testlab/acceptance.sh
```
This installs `sshd`/`hydra`/`hping3`, verifies namespace isolation, starts the
backend in **lab executor + auto** mode watching port 22, then:

- **Attack A — SSH brute-force** → `brute_force` → `R-BRUTE (auto)` → real nft
  block → attacker ping **FAILS** → TTL expiry → ping **RECOVERS**.
- **Attack B — SYN flood** → `dos_flood` → `R-DOS (recommend)` → detected,
  mitigation **proposed** (policy keeps DoS analyst-gated).

### Manual control of the lab
```bash
sudo testlab/setup_netns.sh          # create isolated attacker netns
sudo START_DASHBOARD=1 testlab/start_testlab.sh
# attack from inside the attacker namespace:
sudo testlab/run_attacker.sh nmap -sS -T4 10.66.0.10 -p 22
sudo testlab/run_attacker.sh hping3 -S --flood -p 22 10.66.0.10
sudo testlab/stop_testlab.sh         # flush nft rules + tear down netns
```

To also demo web-layer targets (nmap/hydra against OWASP Juice Shop on :3000):
```bash
sudo ./scripts/setup_attack_lab.sh   # installs tools + launches Juice Shop (Docker)
```
> Note: the detection path is **flow-level** (NFStream + heuristic). Network
> attacks (scan/flood/brute) surface as incidents; app-layer attacks
> (SQLi/XSS/login abuse) are invisible by design.

---

## 5. Detection cheat-sheet

| Attack | Tool / generator | Flow signature | Family → Rule |
|--------|------------------|----------------|---------------|
| Port scan | `gen_traffic.py recon` / `nmap -sS` | ≤2 pkts, tiny, ~0 dur | `recon` → R-RECON |
| SYN/UDP flood | `gen_traffic.py flood` / `hping3 --flood` | ≥200 pkts, ≤100 B/pkt | `dos_flood` → R-DOS (recommend) |
| SSH brute-force | `hydra ssh://` | short repeated sessions on :22 | `brute_force` → R-BRUTE (auto) |

---

## 6. Teardown / reset

```bash
# quick demo: Ctrl-C the uvicorn + vite terminals, then
rm -f soc.db

# lab: always run the stopper (flushes real nft rules + namespaces)
sudo testlab/stop_testlab.sh
```

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `engine_mode=emulated_stream` | run the `setcap` line (§1) and launch from the venv |
| `vite` EACCES on `.vite-temp` | `sudo rm -rf soc/dashboard/node_modules/.vite-temp` |
| permission denied on `soc.db` | `sudo rm -f soc.db` (root-owned from a prior sudo run) |
| no incidents after attack | wait ~4–8 s for flow expiry; confirm the monitored port matches the attack port |
| attacker can reach internet in lab | isolation broken — `sudo testlab/teardown_netns.sh` and re-run setup |

Run the test suite anytime:
```bash
.venv/bin/python -m pytest -q
```

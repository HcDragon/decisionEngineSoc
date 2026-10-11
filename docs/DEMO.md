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
| **Attack** scripts | `attack/` | installer, netns runner, traffic generator, runnable scenarios |
| &nbsp;&nbsp;↳ Attack-lab installer | `attack/setup.sh` | installs nmap/hydra/hping3 + Juice Shop |
| &nbsp;&nbsp;↳ No-sudo traffic generator | `attack/gen_traffic.py` | real recon/flood packets, no root/tools |
| &nbsp;&nbsp;↳ Namespace runner | `attack/run.sh` | run any tool inside the attacker netns |
| &nbsp;&nbsp;↳ Runnable scenarios | `attack/scenarios/*.sh` | `brute_force` · `syn_flood` · `recon_scan`, each fireable alone |
| **Defend** scripts | `defend/` | netns setup/teardown, backend start/stop, shared `lab.env` |
| &nbsp;&nbsp;↳ Namespace defence lab | `defend/setup_netns.sh` / `teardown_netns.sh` | isolated attacker netns + **real** nft blocking |
| &nbsp;&nbsp;↳ Lab start/stop | `defend/start.sh` / `defend/stop.sh` | backend in lab-executor + auto mode |
| &nbsp;&nbsp;↳ No-sudo live test | `defend/live_test.sh` | one-shot detection smoke test |
| One-command acceptance | `acceptance.sh` | orchestrates defend + attack: full attack→block→TTL-recovery proof |

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

The fastest path to see **real NFStream capture + live ML classification**, with
no nmap/root required. It shows flows being captured and scored by the model in
real time.

> **Detections now require the sudo lab (§4).** Live detection runs on the
> trained RandomForest only (ML-only; the flow-shape heuristic is kept strictly
> as a no-model fallback). The model learned real attack *signatures* — SYN
> floods, nmap scans, SSH brute force — not crude packet-count rules. The no-sudo
> generator (`gen_traffic.py`) produces only coarse heuristic-shaped traffic
> (e.g. a completed TCP echo connection, not a spoofed-source SYN storm), which
> the model **correctly** classifies as benign. So this quick demo confirms the
> capture→adapter→model path is live, but to raise real incidents you need the
> real attack tools in §4. This is by design, not a gap: a model that can't be
> fooled by fake traffic is the point.

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

### 2c. Generate traffic (third terminal)
```bash
curl -s -XPOST localhost:8000/api/traffic/port -H 'Content-Type: application/json' -d '{"port":9999}'
.venv/bin/python attack/gen_traffic.py recon --port 9999 --count 80
curl -s -XPOST localhost:8000/api/traffic/port -H 'Content-Type: application/json' -d '{"port":9900}'
.venv/bin/python attack/gen_traffic.py flood --port 9900 --packets 600
```

Or run the whole thing in one shot:
```bash
./defend/live_test.sh
```

### 2d. Watch it land
- **Dashboard:** flows stream into the **Live Traffic** table and the backend log
  shows `IDS model live feature coverage: 57/57` — real capture, real ML scoring.
- **Incidents will read 0.** That is the correct ML-only result: `gen_traffic.py`
  is not a real attack tool, so the model classifies its traffic as benign. For
  real incidents, go to §4 (sudo lab with `hping3` / `nmap` / `hydra`).
- **API:**
  ```bash
  curl -s localhost:8000/api/traffic/status | python -m json.tool  # engine_mode + flow counts
  curl -s localhost:8000/api/incidents | python -m json.tool       # 0 here; populated by §4
  ```

> To watch the flow-shape heuristic fire on this generator instead (for a quick
> smoke test of the decision pipeline without the lab), start the backend with
> `SOC_USE_MODEL=0` — the model is skipped and the heuristic fallback takes over.
> Those incidents carry no probabilities/margin and are **not** explainable, so
> this is a diagnostic mode, not the product.

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

**This is where live ML detection actually fires.** Real attack tools produce
real attack signatures, which the trained RandomForest classifies off live
NFStream flows (57 features, see `soc/backend/app/monitor/features.py`); the
decision engine then raises an incident and, in `auto`, applies a real `nft`
drop rule. Proves containment end-to-end: a real SSH brute-force from an isolated
attacker namespace is detected, **auto-blocked**, the attacker genuinely loses
reachability, then recovers when the block's TTL expires.

> Confined to `10.66.0.0/24` in a network namespace with **no default route**
> (no internet, no LAN). Rules live in a dedicated `inet soc_lab` table so
> teardown never touches the host firewall.

### One command
```bash
sudo bash acceptance.sh
```
This installs `sshd`/`hydra`/`hping3`, verifies namespace isolation, starts the
backend in **lab executor + auto** mode watching port 22, then:

- **Attack A — SSH brute-force** → `brute_force` → `R-BRUTE (auto)` → real nft
  block → attacker ping **FAILS** → TTL expiry → ping **RECOVERS**.
- **Attack B — SYN flood** → `dos_flood` → `R-DOS (recommend)` → detected,
  mitigation **proposed** (policy keeps DoS analyst-gated).

### Manual control of the lab
```bash
sudo defend/setup_netns.sh          # create isolated attacker netns
sudo START_DASHBOARD=1 defend/start.sh

# fire a single, self-contained attack scenario (each runs inside the netns):
sudo attack/scenarios/brute_force.sh            # SSH brute-force  -> R-BRUTE (auto)
sudo PORT=22 attack/scenarios/syn_flood.sh      # SYN flood        -> R-DOS (recommend)
sudo attack/scenarios/recon_scan.sh             # port scan        -> R-RECON

# …or drive any tool directly inside the attacker namespace:
sudo attack/run.sh nmap -sS -T4 10.66.0.10 -p 22
sudo attack/run.sh hping3 -S --flood -p 22 10.66.0.10

sudo defend/stop.sh         # flush nft rules + tear down netns
```

To also demo web-layer targets (nmap/hydra against OWASP Juice Shop on :3000):
```bash
sudo ./attack/setup.sh   # installs tools + launches Juice Shop (Docker)
```
> Note: the detection path is **flow-level** (NFStream → RandomForest). Network
> attacks (scan/flood/brute/MITM) surface as incidents; app-layer attacks
> (SQLi/XSS/login abuse) are invisible by design — the model reads flow
> statistics, not HTTP payloads.

---

## 5. Detection cheat-sheet

Live detection is **ML-only**: the RandomForest ([ids_project](../ids_project/),
retrained on the 57 NFStream-observable features) classifies each live flow. Real
attack tools produce signatures the model recognises; the no-sudo
`gen_traffic.py` does not (it only ever shaped traffic for the legacy heuristic,
which now runs only as the no-model fallback).

| Attack | Real tool (fires the model) | Model class → Family → Rule |
|--------|------------------------------|------------------------------|
| Port / OS scan | `nmap -sS` / `attack/run.sh nmap` | `Recon Scan` → `recon` → R-RECON |
| SYN flood | `hping3 -S --flood --rand-source` | `DoS SYN Flood` → `dos_flood` → R-DOS (recommend) |
| SSH brute-force | `hydra ssh://` | `Dictionary Brute Force` → `brute_force` → R-BRUTE (auto) |
| ARP-spoof MITM | `arpspoof` / ettercap on-LAN | `MITM ARP Spoofing` → `mitm` → R-MITM |

The model also emits real **probabilities + a top-2 margin** per flow, which feed
the `R-CRIT-AUTO` `min_margin` guardrail and the explanation panel. Heuristic
(no-model) incidents carry neither, by design.

---

## 6. Teardown / reset

```bash
# quick demo: Ctrl-C the uvicorn + vite terminals, then
rm -f soc.db

# lab: always run the stopper (flushes real nft rules + namespaces)
sudo defend/stop.sh
```

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `engine_mode=emulated_stream` | run the `setcap` line (§1) and launch from the venv |
| `vite` EACCES on `.vite-temp` | `sudo rm -rf soc/dashboard/node_modules/.vite-temp` |
| permission denied on `soc.db` | `sudo rm -f soc.db` (root-owned from a prior sudo run) |
| no incidents after attack | wait ~4–8 s for flow expiry; confirm the monitored port matches the attack port |
| attacker can reach internet in lab | isolation broken — `sudo defend/teardown_netns.sh` and re-run setup |

Run the test suite anytime:
```bash
.venv/bin/python -m pytest -q
```

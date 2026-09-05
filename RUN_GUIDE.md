# Smart SOC Manager — Master Execution & File Guide

Comprehensive manual containing **all execution commands**, system workflows, and an exhaustive **file-by-file reference** for the Smart SOC Autonomous Decision Engine and its integration with the upstream AI/ML Intrusion Detection System (IDS).

---

## 📑 Table of Contents
1. [Prerequisites & Environment Setup](#1-prerequisites--environment-setup)
2. [Commands to Run the Project](#2-commands-to-run-the-project)
   - [Option A: Full System Launcher](#option-a-full-system-launcher-recommended)
   - [Option B: Individual Component Execution](#option-b-individual-component-execution)
   - [Option C: Real IDS Telemetry Ingestion](#option-c-real-ids-telemetry-ingestion-laimlproject)
   - [Option D: Automated Testing Suite](#option-d-automated-testing-suite)
   - [Option E: REST API Testing (cURL / PowerShell)](#option-e-rest-api-testing-curl--powershell)
3. [Exhaustive File-by-File Breakdown](#3-exhaustive-file-by-file-breakdown)
   - [Root Project Directory](#root-project-directory)
   - [The Enterprise Decision Engine (`decision_engine/`)](#the-enterprise-decision-engine-decision_engine)
   - [Upstream AI/ML IDS Project (`L:\AimlProject\ids_project`)](#upstream-aiml-ids-project-laimlprojectids_project)
   - [Legacy & Backward Compatibility Packages (`api/`, `core/`, `context/`, `intelligence/`, `models/`, `playbooks/`, `policies/`)](#legacy--compatibility-packages)
   - [Documentation (`docs/`)](#documentation-docs)
   - [Test Suite (`tests/`)](#test-suite-tests)

---

## 1. Prerequisites & Environment Setup

Ensure **Python 3.10+** is installed on your system.

### Install Required Dependencies:
Open your terminal (PowerShell, Command Prompt, or Bash) in `L:\DecisionEngine`:

```bash
pip install -r requirements.txt
```

---

## 2. Commands to Run the Project

### Option A: Full System Launcher (Recommended)
Launches **both** the FastAPI REST backend on port 8000 and the Streamlit SOC Command Center dashboard on port 8501 simultaneously:

```bash
python main.py
```
- **SOC Command Center Dashboard:** [http://localhost:8501](http://localhost:8501)
- **FastAPI Swagger Interactive UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Telemetry Endpoint:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

### Option B: Individual Component Execution

#### 1. Run Only the FastAPI Backend Microservice:
```bash
# Using main.py flag
python main.py --api-only

# OR directly with uvicorn (auto-reloading for development)
uvicorn decision_engine.api.routes:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Run Only the Streamlit Enterprise SOC Command Center:
```bash
# Using streamlit CLI directly
streamlit run dashboard.py

# OR using main.py flag
python main.py --dashboard-only
```

---

### Option C: Real IDS Telemetry Ingestion (`L:\AimlProject`)
Streams real network packets from the CICIDS2017 dataset through the Random Forest ML model in `L:\AimlProject\ids_project` into the Decision Engine:

```bash
# Stream 20 sample flows with 0.8s delay (In-Process Engine Mode)
python run_ids_feed.py --samples 20 --delay 0.8

# Stream 50 flows filtered specifically for SYN Flood attacks
python run_ids_feed.py --samples 50 --delay 0.5 --filter "DoS SYN Flood"

# Stream flows via the HTTP REST API on port 8000 (Simulates remote sensor)
python run_ids_feed.py --samples 25 --delay 0.5 --api

# Train or re-train the Random Forest IDS model (if model.pkl is missing)
python -u -c "import os; os.chdir(r'L:\AimlProject\ids_project'); import train_model; train_model.main()"
```

---

### Option D: Automated Testing Suite
Runs the complete test suite consisting of 35 unit, integration, and end-to-end scenario tests:

```bash
# Run all 35 tests with verbose output
python -m pytest tests/ -v

# Run only the Decision Engine pipeline tests (22 tests)
python -m pytest tests/test_decision_engine.py -v

# Run only the AI/ML IDS Bridge integration tests (4 tests)
python -m pytest tests/test_ids_bridge.py -v

# Run only the REST API tests (4 tests)
python -m pytest tests/test_api.py -v

# Run only the backward-compatibility engine tests (5 tests)
python -m pytest tests/test_engine.py -v
```

---

### Option E: REST API Testing (cURL / PowerShell)

#### 1. Health & Active Mitigations Check:
**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get | ConvertTo-Json
```
**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/health"
```

#### 2. Analyze a Threat Event:
**PowerShell:**
```powershell
$body = @{
    timestamp = "2026-09-06T00:00:00Z"
    attack_type = "DoS SYN Flood"
    confidence = 0.98
    src_ip = "198.51.100.25"
    dest_ip = "10.0.0.5"
    src_port = 54321
    dest_port = 80
    protocol = "TCP"
    packet_count = 150000
    flow_duration = 2.5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/decision/analyze" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json
```
**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/decision/analyze" \
     -H "Content-Type: application/json" \
     -d '{"timestamp":"2026-09-06T00:00:00Z","attack_type":"DoS SYN Flood","confidence":0.98,"src_ip":"198.51.100.25","dest_ip":"10.0.0.5","src_port":54321,"dest_port":80,"protocol":"TCP","packet_count":150000,"flow_duration":2.5}'
```

#### 3. List All Logged Incidents:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/incidents"
```

#### 4. Manually Approve a Pending Incident:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/decision/approve" \
     -H "Content-Type: application/json" \
     -d '{"incident_id": "INC-XXXXXXXX"}'
```

---

## 3. Exhaustive File-by-File Breakdown

### Root Project Directory

| File | Purpose & Responsibility |
|---|---|
| [`main.py`](file:///l:/DecisionEngine/main.py) | **Dual-Service Launcher**: Orchestrates running the FastAPI backend (uvicorn) and Streamlit dashboard concurrently or independently via CLI flags (`--api-only`, `--dashboard-only`). |
| [`dashboard.py`](file:///l:/DecisionEngine/dashboard.py) | **Enterprise SOC Command Center**: Streamlit application featuring live DEFCON status, incident triage queue, ML studio with Plotly graphs, active firewall radar, asset defense map, and forensic audit logs. |
| [`run_ids_feed.py`](file:///l:/DecisionEngine/run_ids_feed.py) | **Live IDS Feeder CLI**: Streams real network flow records from `L:\AimlProject\ids_project\dataset` through the trained ML model into the Decision Engine. |
| [`executor.py`](file:///l:/DecisionEngine/executor.py) | **Root Re-export Shim**: Backward-compatibility export providing access to `ActionExecutor` and `SimulationExecutor`. |
| [`requirements.txt`](file:///l:/DecisionEngine/requirements.txt) | **Dependencies Manifest**: Lists exact Python packages required (`fastapi`, `uvicorn`, `streamlit`, `scikit-learn`, `pandas`, `pydantic`, `plotly`, `pyyaml`, `requests`, `pytest`). |
| [`README.md`](file:///l:/DecisionEngine/README.md) | **Project Overview & Architecture Summary**: High-level repository guide with system architecture diagrams and feature summaries. |
| [`RUN_GUIDE.md`](file:///l:/DecisionEngine/RUN_GUIDE.md) | **Master Command & File Guide** *(This Document)*: Exhaustive instructions and file-by-file explanations. |
| [`.gitignore`](file:///l:/DecisionEngine/.gitignore) | **Git Exclusion Rules**: Prevents committing compiled bytecode (`__pycache__`), virtual environments, SQLite database files (`*.db`), and temporary logs. |

---

### The Enterprise Decision Engine (`decision_engine/`)
The production-grade modular SOAR Decision Engine:

#### 1. Core Orchestration & Pipeline
- [`decision_engine/decision/decision_manager.py`](file:///l:/DecisionEngine/decision_engine/decision/decision_manager.py): **Master Pipeline Orchestrator**: Executes the complete 11-stage autonomous security triage pipeline from ingestion to verification and rollback.
- [`decision_engine/decision/__init__.py`](file:///l:/DecisionEngine/decision_engine/decision/__init__.py): Exposes `DecisionManager`.

#### 2. Models (`decision_engine/models/`)
- [`models/threat_event.py`](file:///l:/DecisionEngine/decision_engine/models/threat_event.py): Strict Pydantic model for incoming threat events with a custom root validator that normalizes legacy flat dictionaries into standard nested schemas.
- [`models/context.py`](file:///l:/DecisionEngine/decision_engine/models/context.py): Segregates context into `ObservedTelemetry` (network), `DerivedMetrics` (packet rate, velocity), and `ConfiguredData` (CMDB/TIP).
- [`models/risk.py`](file:///l:/DecisionEngine/decision_engine/models/risk.py): Models the normalized 0–100 risk score and granular factor contributions (`RiskAssessment`, `RiskFactor`).
- [`models/policy.py`](file:///l:/DecisionEngine/decision_engine/models/policy.py): Models declarative policy rules, matching conditions, and arbitration results (`PolicyDefinition`, `PolicyMatchResult`).
- [`models/decision.py`](file:///l:/DecisionEngine/decision_engine/models/decision.py): Defines the final explainable security decision (`SecurityDecision`, `DecisionType`, `AutomationLevel`).
- [`models/playbook.py`](file:///l:/DecisionEngine/decision_engine/models/playbook.py): Models multi-step response playbooks and sequential step execution results (`PlaybookDefinition`, `PlaybookExecutionRecord`).
- [`models/action.py`](file:///l:/DecisionEngine/decision_engine/models/action.py): Models action execution parameters, status, and modes (`ActionExecutionRequest`, `ActionResult`, `ExecutionMode`).
- [`models/verification.py`](file:///l:/DecisionEngine/decision_engine/models/verification.py): Models closed-loop verification results and traffic reduction metrics (`VerificationResult`, `VerificationStatus`).
- [`models/incident.py`](file:///l:/DecisionEngine/decision_engine/models/incident.py): Stateful incident tracking model with lifecycle states from `DETECTED` to `CONTAINED` / `ESCALATED` (`IncidentRecord`, `IncidentState`).
- [`models/__init__.py`](file:///l:/DecisionEngine/decision_engine/models/__init__.py): Package model re-exports.

#### 3. Configuration (`decision_engine/config/`)
- [`config/risk.yaml`](file:///l:/DecisionEngine/decision_engine/config/risk.yaml): Declarative configuration defining factor weights (confidence, severity, anomaly, asset, reputation) and base severity scores for all 10 attack types.
- [`config/policies.yaml`](file:///l:/DecisionEngine/decision_engine/config/policies.yaml): Priority-ordered security policies governing automation levels (0 to 5), decision outcomes, and required playbooks.
- [`config/playbooks.yaml`](file:///l:/DecisionEngine/decision_engine/config/playbooks.yaml): Declarative multi-step response workflows (`PB-DOS-SYN`, `PB-DOS-UDP`, `PB-BRUTE-FORCE`, `PB-MITM-ARP`, etc.).

#### 4. Engine Subsystems
- [`context/context_enricher.py`](file:///l:/DecisionEngine/decision_engine/context/context_enricher.py): Context enrichment engine that computes derived flow rates and queries CMDB asset criticality and TIP threat reputation.
- [`risk/risk_engine.py`](file:///l:/DecisionEngine/decision_engine/risk/risk_engine.py): Mathematical risk calculator computing normalized scores and generating plain-English factor explanations.
- [`policy/policy_loader.py`](file:///l:/DecisionEngine/decision_engine/policy/policy_loader.py): Parses and validates YAML policies from `policies.yaml`.
- [`policy/policy_engine.py`](file:///l:/DecisionEngine/decision_engine/policy/policy_engine.py): Matches policies against enriched context and resolves priority conflicts deterministically.
- [`playbooks/playbook_loader.py`](file:///l:/DecisionEngine/decision_engine/playbooks/playbook_loader.py): Parses and validates playbook workflows from `playbooks.yaml`.
- [`playbooks/playbook_engine.py`](file:///l:/DecisionEngine/decision_engine/playbooks/playbook_engine.py): Sequentially executes playbook steps, checking automation level gates and analyst approvals.
- [`actions/action_executor.py`](file:///l:/DecisionEngine/decision_engine/actions/action_executor.py): Safe action executor managing active mitigation states, expiration TTLs, and allowlist enforcement.
- [`actions/adapters/base.py`](file:///l:/DecisionEngine/decision_engine/actions/adapters/base.py): Abstract base class defining the pluggable action adapter interface.
- [`actions/adapters/simulation_adapter.py`](file:///l:/DecisionEngine/decision_engine/actions/adapters/simulation_adapter.py): Safe simulation adapter executing allowlisted actions without modifying host OS state.
- [`actions/simulation_executor.py`](file:///l:/DecisionEngine/decision_engine/actions/simulation_executor.py): Backward-compatibility executor for simulation actions.
- [`verification/verification_engine.py`](file:///l:/DecisionEngine/decision_engine/verification/verification_engine.py): Closed-loop outcome verification comparing post-mitigation packet rates against baseline traffic.
- [`recovery/recovery_manager.py`](file:///l:/DecisionEngine/decision_engine/recovery/recovery_manager.py): State manager checking expired mitigations, initiating automatic rollback, and escalating persistent attacks.
- [`incidents/incident_manager.py`](file:///l:/DecisionEngine/decision_engine/incidents/incident_manager.py): Stateful incident deduplication and correlation manager operating over a sliding time window (300s).
- [`storage/db.py`](file:///l:/DecisionEngine/decision_engine/storage/db.py): Thread-local SQLite database with WAL (Write-Ahead Logging) mode for persistent storage of incidents, decisions, audit logs, and mitigations.
- [`audit/audit_logger.py`](file:///l:/DecisionEngine/decision_engine/audit/audit_logger.py): Forensic audit logging subsystem writing structured chronological records to SQLite and the event bus.
- [`events/event_bus.py`](file:///l:/DecisionEngine/decision_engine/events/event_bus.py): In-memory Pub/Sub event bus providing real-time telemetry and SSE queue streaming to the dashboard.
- [`api/routes.py`](file:///l:/DecisionEngine/decision_engine/api/routes.py): FastAPI microservice implementing `/analyze`, `/incidents`, `/decisions`, `/approve`, `/events/stream`, and `/health`.
- [`api/streaming.py`](file:///l:/DecisionEngine/decision_engine/api/streaming.py): Async Server-Sent Events (SSE) stream generator for the live dashboard event feed.
- [`integrations/ids_bridge.py`](file:///l:/DecisionEngine/decision_engine/integrations/ids_bridge.py): Bridge connecting to `L:\AimlProject\ids_project`, loading the Random Forest classifier and transformers, and converting real dataset flows into `ThreatEvent` instances.

---

### Upstream AI/ML IDS Project (`L:\AimlProject\ids_project`)

| File | Purpose & Responsibility |
|---|---|
| `model.pkl` | **Trained Random Forest Classifier**: Serialized 100-tree model trained on CICIDS2017 flow data for 10-class network intrusion classification. |
| `scaler.pkl` | **StandardScaler**: Fitted feature standardizer for the 73 numerical flow metrics. |
| `label_encoder.pkl` | **LabelEncoder**: Class mapping for the 10 detection categories. |
| `feature_names.pkl` | **Feature Index**: Ordered list of the 73 network flow feature names. |
| `dataset/cleaned_ids_dataset (1).csv` | **CICIDS2017 Dataset**: 101 MB raw network flow records used for model training and simulation streaming. |
| `train_model.py` | **Model Trainer**: Script that loads dataset, applies SMOTE, trains the Random Forest classifier, evaluates metrics, and dumps `model.pkl`. |
| `preprocess.py` | **Preprocessing Pipeline**: Loads CSV, removes duplicates/NaNs/infinities, balances classes, and fits the scaler and encoder. |
| `evaluate.py` | **Evaluation Script**: Computes Accuracy, F1 Score, average prediction confidence, and per-class classification reports. |
| `simulate.py` | **Local IDS Simulator**: Samples packets from the dataset, runs batch predictions, and prints predicted vs actual classes. |

---

### Legacy & Compatibility Packages
Maintained to guarantee zero regression for legacy code:

| File / Folder | Purpose & Responsibility |
|---|---|
| [`api/router.py`](file:///l:/DecisionEngine/api/router.py) | Re-exports `app`, `decision_manager`, `db`, and `INCIDENTS_DB` from `decision_engine.api.routes`. |
| [`api/schemas.py`](file:///l:/DecisionEngine/api/schemas.py) | Legacy Pydantic data contracts (`TrafficPrediction`, `DecisionResponse`). |
| [`core/engine.py`](file:///l:/DecisionEngine/core/engine.py) | Re-exports `DecisionManager` from `decision_engine.decision.decision_manager`. |
| [`core/executor.py`](file:///l:/DecisionEngine/core/executor.py) | Re-exports `ActionExecutor` and `SimulationExecutor`. |
| [`core/config.py`](file:///l:/DecisionEngine/core/config.py) | Legacy risk formula weights and severities. |
| [`context/asset_db.py`](file:///l:/DecisionEngine/context/asset_db.py) | CMDB lookup service for asset criticalities (`HIGH`, `MEDIUM`, `LOW`). |
| [`context/threat_intel.py`](file:///l:/DecisionEngine/context/threat_intel.py) | Threat Intelligence Platform (TIP) mock for IP reputation scoring. |
| [`intelligence/risk_calculator.py`](file:///l:/DecisionEngine/intelligence/risk_calculator.py) | Legacy dynamic risk formula calculator. |
| [`intelligence/policy_engine.py`](file:///l:/DecisionEngine/intelligence/policy_engine.py) | Legacy YAML policy evaluator. |
| [`models/enums.py`](file:///l:/DecisionEngine/models/enums.py) | Core enumerations (`AttackType`, `Severity`, `PlaybookID`, `IncidentStatus`). |
| [`playbooks/selector.py`](file:///l:/DecisionEngine/playbooks/selector.py) | Static mapping from `AttackType` to `PlaybookID`. |
| [`policies/*.yaml`](file:///l:/DecisionEngine/policies/) | Legacy individual policy files (`ddos_syn_flood.yaml`, `benign.yaml`, etc.). |

---

### Documentation (`docs/`)

| File | Purpose & Responsibility |
|---|---|
| [`docs/architecture.md`](file:///l:/DecisionEngine/docs/architecture.md) | **Software Architecture Specification**: Technical document detailing system design, sequence diagrams, risk algorithms, and data structures. |
| [`docs/simulation_guide.md`](file:///l:/DecisionEngine/docs/simulation_guide.md) | **Simulation Guide**: Instructions and code snippets for generating synthetic and replay network attacks. |

---

### Test Suite (`tests/`)

| File | Purpose & Responsibility |
|---|---|
| [`tests/test_api.py`](file:///l:/DecisionEngine/tests/test_api.py) | **REST API Tests (4 tests)**: Tests Swagger redirect, `/analyze` endpoint, incident queries, and manual analyst approval. |
| [`tests/test_decision_engine.py`](file:///l:/DecisionEngine/tests/test_decision_engine.py) | **Core Engine Tests (22 tests)**: Exhaustive test suite covering validation, enrichment, risk engine, policy matching, playbooks, action allowlists, verification, recovery, and audit logging. |
| [`tests/test_ids_bridge.py`](file:///l:/DecisionEngine/tests/test_ids_bridge.py) | **IDS Integration Tests (4 tests)**: Tests loading ML artifacts from `L:\AimlProject`, flow predictions, and verifies end-to-end processing across **all 10 attack classes**. |
| [`tests/test_engine.py`](file:///l:/DecisionEngine/tests/test_engine.py) | **Compatibility Tests (5 tests)**: Verifies backward-compatible method calls (`process_prediction`, dictionary subscript access, policy engine loading). |
| [`tests/malicious_payloads.json`](file:///l:/DecisionEngine/tests/malicious_payloads.json) | **Sample Fixtures**: Test payloads for manual and automated validation. |

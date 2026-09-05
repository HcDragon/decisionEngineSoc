# Smart SOC Manager: Autonomous Decision Engine

An enterprise-grade, deterministic **SOC Decision Engine** for automated cyber-threat triage, risk scoring, and remediation orchestration.

Designed to bridge the gap between Machine Learning threat detection and autonomous SOAR actions, eliminating alert fatigue and enabling machine-speed incident response.

---

## Key Features

- **11-Stage Autonomous Orchestration Pipeline:**
  1. Threat Event Validation (Strict Pydantic schema validation & legacy flat payload normalization)
  2. Context Enrichment (Observed telemetry, Derived metrics, and Configured CMDB/TIP data)
  3. Explainable Risk Scoring (Normalized 0–100 score with granular mathematical factor contributions)
  4. Policy Evaluation & Priority Resolution (Declarative YAML policies with deterministic priority arbitration)
  5. Decision Generation & Level Allocation (Automation levels 0 to 5, SOC analyst escalation flags)
  6. Playbook Orchestration (Config-driven multi-step response workflows in `playbooks.yaml`)
  7. Safe Action Execution (SIMULATION & PRODUCTION execution modes, strict action allowlists)
  8. Outcome Verification (Automated traffic drop percentage vs. expected threshold comparison)
  9. Recovery, Rollback & Escalation (Stateful action duration tracking, auto-rollback, and timeout escalation)
  10. Stateful Incident Management (Sliding time-window deduplication, persistent state machine)
  11. Forensic Audit Trail & Event Bus (Immutable SQLite WAL-mode audit logging and real-time SSE streaming)
- **Zero Fake Runtime Telemetry:** Ready to ingest real threat event streams via `POST /api/v1/decision/analyze` from upstream ML / NFStream pipelines.
- **Enterprise Streamlit SOAR Command Center:** Live incident registry, explainable decision inspector, active mitigation monitor, manual approval actions, and forensic audit stream.

---

## Project Structure

```
DecisionEngine/
├── main.py                         # Application launcher (FastAPI + Streamlit)
├── dashboard.py                    # Streamlit Enterprise SOAR Command Center
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
│
├── decision_engine/                # Production SOAR Decision Engine Module
│   ├── api/                        # FastAPI REST service & SSE live stream generator
│   │   ├── routes.py               # /analyze, /incidents, /decisions, /events/stream, /approve
│   │   └── streaming.py            # Real-time SSE generator for dashboard live feeds
│   ├── models/                     # Strongly-typed Pydantic v2 domain models
│   │   ├── threat_event.py         # ThreatEvent with automatic flat payload normalization
│   │   ├── context.py              # EnrichedContext (Observed, Derived, Configured)
│   │   ├── risk.py                 # RiskAssessment & RiskFactor contributions
│   │   ├── policy.py               # PolicyDefinition & PolicyMatchResult
│   │   ├── decision.py             # SecurityDecision (explainable reasons, automation levels)
│   │   ├── playbook.py             # PlaybookDefinition & PlaybookExecutionRecord
│   │   ├── action.py               # ActionExecutionRequest & ActionResult
│   │   ├── verification.py         # VerificationResult & status metrics
│   │   └── incident.py             # IncidentRecord with state transitions
│   ├── config/                     # Declarative YAML configurations
│   │   ├── risk.yaml               # Factor weights, base severities, confidence multipliers
│   │   ├── policies.yaml           # Security policies with deterministic priority ordering
│   │   └── playbooks.yaml          # Multi-step response workflows
│   ├── context/                    # Context enrichment engine (CMDB asset + TIP lookup)
│   ├── risk/                       # Explainable risk assessment engine (0-100 normalized)
│   ├── policy/                     # Declarative policy matcher with priority resolution
│   ├── playbooks/                  # Playbook workflow dispatcher and step executor
│   ├── actions/                    # Safe action execution subsystem
│   │   ├── action_executor.py      # SOAR executor with active mitigation tracking & allowlist
│   │   └── adapters/               # Pluggable execution adapters (SimulationAdapter, etc.)
│   ├── verification/               # Closed-loop mitigation verification engine
│   ├── recovery/                   # Action lifecycle manager (rollback & escalation)
│   ├── incidents/                  # Stateful incident correlation & sliding window deduplication
│   ├── storage/                    # Persistent SQLite storage with WAL mode & thread-local connections
│   ├── audit/                      # Forensic audit logging system
│   ├── events/                     # Real-time Pub/Sub and SSE event bus
│   └── decision/                   # DecisionManager master pipeline orchestrator
│
├── api/                            # Backward-compatible API router re-exports
├── core/                           # Backward-compatible core engine re-exports
├── docs/                           # Architectural specifications & simulation guide
└── tests/                          # Automated Pytest suite (31 tests passing)
    ├── test_decision_engine.py     # Comprehensive 22-test Decision Engine suite
    ├── test_api.py                 # REST API integration tests
    └── test_engine.py              # Decision Manager backward-compatibility tests
```

---

## Quickstart

### 1. Installation

Ensure Python 3.10+ is installed:

```bash
pip install -r requirements.txt
```

### 2. Launch the Application

Run both the FastAPI backend and Streamlit dashboard together:

```bash
python main.py
```

- **FastAPI API & Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Streamlit Dashboard:** [http://localhost:8501](http://localhost:8501)

#### Run Services Individually:
```bash
# FastAPI backend only
python main.py --api-only

# Streamlit dashboard only
python main.py --dashboard-only
```

---

## Running Tests

Execute the automated test suite with pytest:

```bash
pytest tests/
```

---

## Documentation

- [Architecture Design Document](docs/architecture.md): Complete specification of system components, mathematical formulas, and sequence diagrams.
- [Simulation Guide](docs/simulation_guide.md): Code examples and step-by-step instructions for simulating network attack traffic.

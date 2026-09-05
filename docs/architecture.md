# Smart SOC Manager: Decision Engine
## Enterprise Software Design & Technical Architecture Document

---

## Document Control
| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2026-07-30 | AI Architect | Initial Architecture Design for Decision Engine |
| 2.0 | 2026-07-31 | AI Architect | Updated to reflect actual codebase implementation |
| 2.1 | 2026-09-05 | AI Architect | Restructured to clean package layout with external policies |

---

## Chapter 1: Introduction

### 1.1 What is a SOC?
A Security Operations Center (SOC) is a centralized function within an organization employing people, processes, and technology to continuously monitor and improve an organization's security posture while preventing, detecting, analyzing, and responding to cybersecurity incidents.

### 1.2 Security Incident Response
Incident Response (IR) is the methodology an organization uses to respond to and manage a cyberattack. An effective IR strategy aims to limit damage, reduce recovery time, and mitigate costs. Traditional IR relies heavily on manual log analysis, which is slow and error-prone.

### 1.3 Why Decision Engines are Required
As network traffic volumes and attack sophistication increase, human analysts suffer from "alert fatigue." A Decision Engine sits at the core of an autonomous SOC, bridging the gap between detection (AI/ML models) and response. It contextualizes alerts, calculates risks, and determines the best course of action without human intervention.

### 1.4 Problems with Manual Incident Response
* **Alert Fatigue:** Analysts are overwhelmed by thousands of daily alerts, many of which are false positives.
* **Slow Response Times:** Manual triage takes minutes to hours, giving attackers time to exfiltrate data or disrupt services.
* **Inconsistent Decisions:** Different analysts may respond to the same threat differently based on their experience level.

### 1.5 Need for Automated Decision Making
Automated decision-making brings machine-speed response to cybersecurity. By using deterministic logic and context enrichment, the Decision Engine ensures consistent, immediate, and accurate remediation of threats like DoS floods and brute force attacks.

---

## Chapter 2: Decision Engine Fundamentals

### 2.1 Definition
The Decision Engine is the centralized intelligence module of the Smart SOC Manager. It receives predictions from the ML layer, evaluates the context, calculates a risk score, and determines the optimal remediation strategy.

### 2.2 Objectives
* Eliminate false positives from escalating to Tier 1 analysts.
* Provide machine-speed responses to high-confidence attacks.
* Standardize incident response procedures via automated playbooks.

### 2.3 Scope
The scope of this engine includes ingesting ML predictions, prioritizing incidents, recommending actions, enforcing automation levels, and logging all automated decisions. Simulated execution is handled by `core/executor.py` (`SimulationExecutor`).

### 2.4 Responsibilities
* **Contextualization:** Gathering asset criticality (`AssetDB`) and threat intelligence (`ThreatIntel`).
* **Risk Assessment:** Generating a dynamic risk score via `RiskCalculator`.
* **Policy Enforcement:** Deciding the automation level (0–5) via `PolicyEngine`.
* **Playbook Selection:** Mapping the attack type to a specific `PlaybookID`.
* **Incident Logging:** Storing decisions in the in-memory `INCIDENTS_DB` via the API layer.

### 2.5 Inputs and Outputs
**Inputs (`TrafficPrediction` schema):**
- `attack_type` (str) — e.g., `"DoS SYN Flood"`
- `confidence` (float) — 0.0–100.0 or 0.0–1.0
- `flow_context` — `src_ip`, `dest_ip`, `src_port`, `dest_port`, `protocol`, `packet_count`, `flow_duration`, `timestamp`

**Outputs (`DecisionResponse` schema):**
- `incident_id`, `attack_type`, `confidence`, `risk_score`, `severity`, `priority`
- `recommended_action`, `playbook` (`PlaybookID`), `automation_level`, `incident_status`
- `analyst_required`, `generated_time`, `src_ip`

### 2.6 Supported Attack Types
| Enum Value | String Label | Playbook |
|---|---|---|
| `BENIGN` | `Benign Traffic` | `PB-NET-000-BENIGN` |
| `BRUTE_FORCE` | `Dictionary Brute Force` | `PB-ID-001-BRUTEFORCE` |
| `DNS_FLOOD` | `DoS DNS Flood` | `PB-NET-002-DNS-FLOOD` |
| `ICMP_FLOOD` | `DoS ICMP Flood` | `PB-NET-003-ICMP-FLOOD` |
| `SYN_FLOOD` | `DoS SYN Flood` | `PB-NET-004-SYN-FLOOD` |
| `UDP_FLOOD` | `DoS UDP Flood` | `PB-NET-005-UDP-FLOOD` |

---

## Chapter 3: Enterprise SOAR Research

Modern SOAR platforms (Palo Alto Cortex XSOAR, Microsoft Sentinel, Splunk SOAR, IBM QRadar SOAR) separate the **Event Ingestion**, **Decision/Logic**, and **Orchestration** layers. The Smart SOC Decision Engine adopts this decoupled architecture: parsing incoming events, enriching them with asset/threat intelligence, applying declarative policies, and selecting playbooks.

---

## Chapter 4: Decision Engine Architecture

### 4.1 File System Layout

```
DecisionEngine/
│
├── main.py                         # Application launcher (FastAPI + Streamlit subprocesses)
├── dashboard.py                    # Streamlit frontend (Traffic Simulator + Incident Table)
├── executor.py                     # Root re-export for ActionExecutor & SimulationExecutor
├── requirements.txt                # Python dependencies
├── README.md                       # Comprehensive project guide
│
├── api/                            # FastAPI REST service
│   ├── __init__.py
│   ├── router.py                   # /analyze, /incidents, /approve endpoints
│   └── schemas.py                  # Pydantic models: TrafficPrediction, DecisionResponse
│
├── core/                           # Central decision pipeline & execution
│   ├── __init__.py
│   ├── engine.py                   # DecisionManager orchestrator
│   ├── config.py                   # Risk weights & severity base scores
│   └── executor.py                 # SimulationExecutor & ActionExecutor
│
├── context/                        # Context enrichment
│   ├── __init__.py
│   ├── asset_db.py                 # CMDB mock (asset criticality 0–100)
│   └── threat_intel.py             # TIP mock (reputation score 0–100)
│
├── intelligence/                   # Risk and policy logic
│   ├── __init__.py
│   ├── risk_calculator.py          # Weighted risk score computation
│   └── policy_engine.py            # Dynamic YAML policy loader & evaluator
│
├── models/                         # Domain models
│   ├── __init__.py
│   └── enums.py                    # AttackType, Severity, PlaybookID, IncidentStatus
│
├── playbooks/                      # SOC playbooks
│   ├── __init__.py
│   └── selector.py                 # AttackType -> Playbook mapping
│
├── policies/                       # Declarative YAML policies
│   ├── benign.yaml                 # Benign traffic handling
│   ├── brute_force.yaml            # Brute force attack policy
│   ├── ddos_dns_flood.yaml         # DNS flood policy
│   ├── ddos_icmp_flood.yaml        # ICMP flood policy
│   ├── ddos_syn_flood.yaml         # SYN flood policy
│   └── ddos_udp_flood.yaml         # UDP flood policy
│
├── docs/                           # Architecture and simulation documentation
│   ├── architecture.md             # This document
│   └── simulation_guide.md         # Simulation walkthrough & usage examples
│
└── tests/                          # Automated test suite
    ├── __init__.py
    ├── test_api.py                 # FastAPI test suite
    ├── test_engine.py              # DecisionManager unit and scenario tests
    └── malicious_payloads.json     # Test payloads
```

### 4.2 Module Responsibilities

| Module | Class | Responsibility |
|---|---|---|
| `api/router.py` | FastAPI app | REST endpoints; logs decisions to `INCIDENTS_DB` |
| `api/schemas.py` | `TrafficPrediction`, `DecisionResponse` | Pydantic data contracts |
| `models/enums.py` | `AttackType`, `Severity`, `PlaybookID`, `IncidentStatus` | Typed constants |
| `core/engine.py` | `DecisionManager` | Pipeline orchestrator |
| `core/executor.py` | `SimulationExecutor`, `ActionExecutor` | Simulates firewall, rate-limit, and IAM actions |
| `context/asset_db.py` | `AssetDB` | Returns asset criticality by destination IP |
| `context/threat_intel.py` | `ThreatIntel` | Returns threat reputation by source IP |
| `intelligence/risk_calculator.py` | `RiskCalculator` | Calculates weighted risk score |
| `intelligence/policy_engine.py` | `PolicyEngine` | Loads YAML policies from `policies/` and evaluates matches |
| `playbooks/selector.py` | `PlaybookSelector` | Maps attack types to response playbooks |
| `dashboard.py` | Streamlit App | Interactive SOC Command Center UI |

### 4.3 Risk Score Formula

```
Risk = (W1 × BaseSeverity) + (W2 × Confidence) + (W3 × AssetCriticality)
     + (W4 × ThreatIntelScore) + (W5 × FrequencyModifier)

Weights (core/config.py):
  W1 = 0.35  (Base Severity)
  W2 = 0.25  (Confidence)
  W3 = 0.20  (Asset Criticality)
  W4 = 0.10  (Threat Intel)
  W5 = 0.10  (Frequency / Packet Count)

Clamped between 0.0 and 100.0.
```

### 4.4 Automation Level Matrix

| Level | Condition | Status | Analyst Required |
|---|---|---|---|
| 0 | Benign traffic | `LOGGED` | No |
| 1 | Whitelisted IP / default fallback | `LOGGED` | No |
| 2 | Low confidence (≤ 90%) | `PENDING_APPROVAL` | Yes |
| 3 | High confidence, low risk | `PENDING_APPROVAL` | Yes |
| 4 | High confidence + high risk + critical asset | `PENDING_APPROVAL` | Yes |
| 5 | High confidence + high risk + non-critical asset | `AUTO_MITIGATED` | No |

---

## Chapter 5: Running and Verifying

### 5.1 Run the Full Stack
```bash
python main.py
```
- FastAPI: `http://127.0.0.1:8000/docs`
- Streamlit: `http://localhost:8501`

### 5.2 Run Automated Tests
```bash
pytest tests/
```

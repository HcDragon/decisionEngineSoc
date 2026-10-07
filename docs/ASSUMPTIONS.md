# System Assumptions & Design Decisions

This document outlines key technical and operational assumptions made during the design and development of the AI-Based Smart SOC Manager.

## 1. Environment & Dual Database Strategy
- **Production / Docker**: Runs on PostgreSQL 16 (`db` service in `docker-compose.yml`) utilizing native `JSONB` and indexing capabilities.
- **Local Dev / Testing**: In local environments without a live PostgreSQL instance or during fast unit tests, the system transparently supports SQLite with standard SQLAlchemy JSON type emulation.
- **Migrations**: Alembic handles schema evolution and migrations.

## 2. Model & Dataset Integration
- **Dataset Flow Columns**: The existing IDS dataset (`cleaned_ids_dataset (1).csv`) lacks explicit `src_ip` and `dst_ip` columns (flows contain ports, packet metrics, timing, and flags).
- **Synthetic Asset Addressing**: The replay simulator and ingestion pipeline attach synthetic IPs drawn from `config/assets.yaml` (`attacker_pool` for threat sources, and registered internal asset IPs for targets). This is a known, documented design limitation.
- **Model Weaknesses**: Per evaluation findings, DoS floods (DNS, UDP, ICMP) and Recon Host Discovery exhibit lower individual F1 scores. The Decision Engine mitigates this by aggregating predictions into coarse **attack families** and weighting model confidence with top-2 class probability margins.
- **Top Feature**: `Src Port` is an influential feature in the pre-trained model (likely a capture artifact). In phases 1-6, the model artifact is preserved unchanged.

## 3. Automation & Safety Guardrails
- **Default Automation State**: The system initializes in `recommend_only` mode. Fully autonomous execution (`auto`) requires explicit activation and satisfies strict confidence/margin guardrails.
- **Zero Real Side Effects by Default**: The default executor is `DryRunExecutor`. Live network modifications are strictly disabled unless `SOC_LAB_MODE=true`, `SOC_EXECUTOR=lab`, and target IPs strictly fall within configured lab CIDR boundaries.
- **Virtual Firewall**: In simulated mode (`SimulatedExecutor`), active IP blocks, host isolations, and rate limits are tracked in the database (`virtual_firewall` table) with scheduled TTL automatic rollback.

## 4. Hash-Chained Audit Trail
- Every critical state transition, analyst approval, rule execution, and system mode change appends a cryptographically verified, hash-chained record (`sha256(prev_hash + canonical_json(payload))`).
- Implemented in `soc/backend/app/audit/chain.py`. Genesis `prev_hash` is 64 zeros; `verify_chain()` recomputes the whole chain and reports the first break.

## 5. Risk Scoring — Benign Carries Zero Risk (F0 design decision)
- The weighted risk formula (`severity·0.35 + confidence·0.25 + asset·0.25 + intel·0.15`, +repeat-offender bonus capped at 10) treats the confidence, asset, and intel weights as amplifiers of an **attack** signal.
- Therefore a **benign** classification (family `benign`, severity 0.0) is scored **0.0 / LOW** regardless of model confidence or how critical the destination asset is. Rationale: a benign flow to a critical server must not score MEDIUM purely because the model is 99% sure it is benign and the target is valuable. Benign flows are handled by the default `monitor`/`pb_log_only` rule and never open an incident.
- Consequence: `min_alert_confidence` (0.40) gates whether an **attack** classification becomes an alert at all; benign flows are counted for telemetry but not scored as risk.

## 6. Policy Versioning
- `load_policy_bundle()` computes a deterministic `policy_hash` (SHA-256 over the normalized policies/assets/allowlist/intel/playbook inputs). Every Decision stores this hash so it can be traced to the exact policy version that produced it. `reload_policy()` supports hot reload.

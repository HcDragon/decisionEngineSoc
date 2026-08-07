# Smart SOC Manager: Decision Engine Simulation Guide

This guide provides Python script examples to simulate predictions from the Threat Detection Engine and pass them directly to the Decision Engine logic.

## Usage

You can test the engine by passing a dictionary to the `process_prediction` method of the `DecisionManager`.

### Basic Test Script
Create a python script in the root directory (e.g., `simulate.py`):

```python
import json
from decision_engine.core.engine import DecisionManager

engine = DecisionManager()

# Simulate a High-Confidence DoS SYN Flood on a Critical Asset (10.0.0.5)
prediction = {
    "attack_type": "DoS SYN Flood",
    "confidence": 98.5,
    "source_ip": "192.168.1.100",
    "destination_ip": "10.0.0.5",
    "packet_count": 150000
}

decision = engine.process_prediction(prediction)

print(json.dumps(decision, indent=2))
```

### Expected Output
Because `10.0.0.5` is a critical tier 1 asset, the output will yield `"automation_level": "Level 4"`, meaning human approval is required before execution.

```json
{
  "incident_id": "INC-20260807-ABCD",
  "attack_type": "DoS SYN Flood",
  "confidence": 98.5,
  "risk_score": 93.35,
  "severity": "CRITICAL",
  "priority": "P1",
  "recommended_action": "Enable TCP SYN Cookies on load balancer.",
  "playbook": "PB-NET-004-SYN-FLOOD",
  "automation_level": "Level 4",
  "incident_status": "OPEN",
  "analyst_required": true,
  "generated_time": "2026-08-07T10:35:00.000000"
}
```

### Simulating Other Scenarios
Simply adjust the dictionary values:
* **Fully Auto (Level 5)**: Change `destination_ip` to a non-critical asset (e.g., `10.0.0.10`).
* **Ignore (Level 0)**: Change `attack_type` to `Benign`.
* **Low Confidence Alert (Level 2)**: Lower the `confidence` below `90.0`.

# Smart SOC Manager: Decision Engine Simulation Guide

This guide provides Python script examples to simulate predictions from the Threat Detection Engine and pass them directly to the Decision Engine logic.

## Usage

You can test the engine by passing either a dictionary or a `TrafficPrediction` object to the `DecisionManager`.

### Basic Test Script

Create a python script in the root directory (e.g., `simulate.py`):

```python
import json
from core.engine import DecisionManager

engine = DecisionManager()

# Simulate a High-Confidence DoS SYN Flood on a Critical Asset (10.0.0.5)
prediction = {
    "attack_type": "DoS SYN Flood",
    "confidence": 98.5,
    "source_ip": "192.168.1.100",
    "destination_ip": "10.0.0.5",
    "packet_count": 150000
}

# process_prediction accepts raw dicts or TrafficPrediction instances
decision = engine.process_prediction(prediction)

print(f"Incident ID:        {decision.incident_id}")
print(f"Attack Type:        {decision.attack_type}")
print(f"Confidence:         {decision.confidence}%")
print(f"Risk Score:         {decision.risk_score}")
print(f"Severity:           {decision.severity}")
print(f"Automation Level:   Level {decision.automation_level}")
print(f"Incident Status:    {decision.incident_status}")
print(f"Recommended Action: {decision.recommended_action}")
print(f"Actions Executed:   {decision.actions}")
```

### Expected Output

Because `10.0.0.5` is a critical tier 1 asset and confidence/risk is high:

```text
Incident ID:        INC-xxxxxxxx
Attack Type:        DoS SYN Flood
Confidence:         98.5%
Risk Score:         88.22
Severity:           CRITICAL
Automation Level:   Level 5
Incident Status:    AUTO_MITIGATED
Recommended Action: Automatically Applied Playbook Mitigations.
Actions Executed:   ['BLOCK_SOURCE_IP', 'SYN_PROTECTION', 'CREATE_INCIDENT']
```

### Simulating Other Scenarios

Simply adjust the dictionary values:
* **Fully Auto Mitigation**: High confidence attack on any monitored asset with matching policy.
* **Requires Analyst Approval**: Brute force attack (`Dictionary Brute Force`) or low confidence alerts (`confidence < 85.0`).
* **Ignore / Log Only (Level 0)**: Change `attack_type` to `"Benign Traffic"`.

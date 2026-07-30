# Global Configurations and Thresholds

# Risk Weights
WEIGHT_SEVERITY = 0.35
WEIGHT_CONFIDENCE = 0.25
WEIGHT_ASSET = 0.20
WEIGHT_INTEL = 0.10
WEIGHT_FREQUENCY = 0.10

# Base Severities mapping
BASE_SEVERITIES = {
    "Benign Traffic": 0,
    "Dictionary Brute Force": 70,
    "DoS DNS Flood": 85,
    "DoS ICMP Flood": 80,
    "DoS SYN Flood": 90,
    "DoS UDP Flood": 85
}

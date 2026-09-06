"""
Authoritative Registries for Enterprise Assets and Threat Intelligence.
Single source of truth used across ContextEnricher, IDSBridge, and demo stream generators.
"""

ASSET_REGISTRY = {
    "10.0.0.1": {
        "ip": "10.0.0.1",
        "name": "Enterprise-Domain-Controller",
        "role": "Enterprise Domain Controller",
        "criticality": 98,
        "criticality_label": "CRITICAL",
        "ports": [53, 88, 389, 445]
    },
    "10.0.0.5": {
        "ip": "10.0.0.5",
        "name": "Core-Database-Cluster",
        "role": "Core Production Database",
        "criticality": 95,
        "criticality_label": "HIGH",
        "ports": [3306, 5432, 1433, 22]
    },
    "10.0.0.10": {
        "ip": "10.0.0.10",
        "name": "Public-Web-Load-Balancer",
        "role": "Public Web Load Balancer",
        "criticality": 80,
        "criticality_label": "HIGH",
        "ports": [80, 443]
    },
    "10.0.0.12": {
        "ip": "10.0.0.12",
        "name": "DMZ-Web-Gateway",
        "role": "DMZ Web Gateway",
        "criticality": 75,
        "criticality_label": "MEDIUM",
        "ports": [80, 443, 8080]
    },
    "10.0.0.20": {
        "ip": "10.0.0.20",
        "name": "Internal-App-Server",
        "role": "Internal Application Server",
        "criticality": 60,
        "criticality_label": "MEDIUM",
        "ports": [8080, 8443]
    },
    "10.0.0.25": {
        "ip": "10.0.0.25",
        "name": "Internal-API-Service",
        "role": "Internal API Service",
        "criticality": 65,
        "criticality_label": "MEDIUM",
        "ports": [8000, 8443]
    },
    "10.0.0.50": {
        "ip": "10.0.0.50",
        "name": "Employee-Workstation",
        "role": "Employee Workstation",
        "criticality": 25,
        "criticality_label": "LOW",
        "ports": [22, 445]
    },
    "127.0.0.1": {
        "ip": "127.0.0.1",
        "name": "Local-SOC-Target-Host",
        "role": "Local Monitored Web Gateway",
        "criticality": 85,
        "criticality_label": "HIGH",
        "ports": [80, 443, 8000, 3001, 9999]
    }
}

MONITORED_ASSETS = list(ASSET_REGISTRY.values())

THREAT_INTEL_REGISTRY = {
    "203.0.113.50": {"score": 95, "category": "Known Malicious (Botnet C2)"},
    "203.0.113.100": {"score": 90, "category": "Known Malicious (DDoS Node)"},
    "198.51.100.22": {"score": 90, "category": "Known Malicious (Scanner)"},
    "198.51.100.75": {"score": 85, "category": "Known Malicious (Brute Force Bot)"},
    "192.0.2.15": {"score": 80, "category": "Suspicious (Recon Source)"},
    "192.0.2.88": {"score": 85, "category": "Known Malicious (Exploit Probe)"},
    "45.33.32.156": {"score": 95, "category": "Known Malicious (C2 Infrastructure)"},
    "185.220.101.5": {"score": 92, "category": "Known Malicious (Tor Exit Node / Scanner)"},
    "162.243.128.88": {"score": 88, "category": "Known Malicious (Mirai Variant Node)"},
    "192.168.1.200": {"score": 50, "category": "Suspicious (High connection rate)"},
}

PERSISTENT_ATTACKER_IPS = {
    "DoS SYN Flood": ["203.0.113.50", "198.51.100.22", "45.33.32.156"],
    "DoS UDP Flood": ["203.0.113.100", "185.220.101.5", "162.243.128.88"],
    "DoS ICMP Flood": ["192.0.2.15", "198.51.100.75"],
    "DoS DNS Flood": ["203.0.113.50", "162.243.128.88"],
    "Dictionary Brute Force": ["198.51.100.75", "192.0.2.88"],
    "MITM ARP Spoofing": ["192.168.1.200", "45.33.32.156"],
    "Recon Host Discovery": ["192.0.2.15", "203.0.113.100"],
    "Recon Ping Sweep": ["192.0.2.15", "198.51.100.22"],
    "Recon OS Scan": ["192.0.2.88", "185.220.101.5"],
    "default": ["203.0.113.50", "198.51.100.22", "45.33.32.156", "185.220.101.5"]
}

PERSISTENT_TARGET_MAP = {
    "203.0.113.50": "10.0.0.5",     # Core Database
    "198.51.100.22": "10.0.0.5",    # Core Database
    "45.33.32.156": "10.0.0.5",     # Core Database
    "203.0.113.100": "10.0.0.12",   # DMZ Web Gateway
    "185.220.101.5": "10.0.0.10",   # Web Load Balancer
    "162.243.128.88": "10.0.0.12",  # DMZ Web Gateway
    "192.0.2.15": "10.0.0.20",      # App Server
    "198.51.100.75": "10.0.0.1",    # Domain Controller
    "192.0.2.88": "10.0.0.1",       # Domain Controller
}


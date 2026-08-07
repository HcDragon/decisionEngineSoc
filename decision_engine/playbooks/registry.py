PLAYBOOK_REGISTRY = {
    "Benign": {
        "playbook_id": "PB-NET-000-BENIGN",
        "action": "Ignore."
    },
    "Benign Traffic": {
        "playbook_id": "PB-NET-000-BENIGN",
        "action": "Ignore."
    },
    "Brute Force": {
        "playbook_id": "PB-ID-001-BRUTEFORCE",
        "action": "Temporary IP block at firewall. Enforce MFA."
    },
    "Dictionary Brute Force": {
        "playbook_id": "PB-ID-001-BRUTEFORCE",
        "action": "Temporary IP block at firewall. Enforce MFA."
    },
    "DoS DNS Flood": {
        "playbook_id": "PB-NET-002-DNS-FLOOD",
        "action": "Implement DNS Rate Limiting (RRL)."
    },
    "DoS ICMP Flood": {
        "playbook_id": "PB-NET-003-ICMP-FLOOD",
        "action": "Drop external ICMP traffic at perimeter."
    },
    "DoS SYN Flood": {
        "playbook_id": "PB-NET-004-SYN-FLOOD",
        "action": "Enable TCP SYN Cookies on load balancer."
    },
    "DoS UDP Flood": {
        "playbook_id": "PB-NET-005-UDP-FLOOD",
        "action": "Rate limit UDP traffic. Null-route source IP."
    }
}

class PlaybookSelector:
    @staticmethod
    def get_playbook(attack_type: str) -> dict:
        return PLAYBOOK_REGISTRY.get(attack_type, {
            "playbook_id": "PB-GEN-000-UNKNOWN",
            "action": "Investigate manually."
        })

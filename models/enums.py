from enum import Enum

class AttackType(str, Enum):
    BENIGN = "Benign Traffic"
    BRUTE_FORCE = "Dictionary Brute Force"
    DNS_FLOOD = "DoS DNS Flood"
    ICMP_FLOOD = "DoS ICMP Flood"
    SYN_FLOOD = "DoS SYN Flood"
    UDP_FLOOD = "DoS UDP Flood"

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PlaybookID(str, Enum):
    PB_BENIGN = "PB-NET-000-BENIGN"
    PB_BRUTEFORCE = "PB-ID-001-BRUTEFORCE"
    PB_DNS_FLOOD = "PB-NET-002-DNS-FLOOD"
    PB_ICMP_FLOOD = "PB-NET-003-ICMP-FLOOD"
    PB_SYN_FLOOD = "PB-NET-004-SYN-FLOOD"
    PB_UDP_FLOOD = "PB-NET-005-UDP-FLOOD"

class IncidentStatus(str, Enum):
    LOGGED = "LOGGED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    AUTO_MITIGATED = "AUTO_MITIGATED"
    MANUAL_MITIGATED = "MANUAL_MITIGATED"

from models.enums import AttackType, PlaybookID

class PlaybookSelector:
    """
    Maps incoming Attack Types to the correct Playbook ID.
    """
    def __init__(self):
        self.mapping = {
            AttackType.BENIGN: PlaybookID.PB_BENIGN,
            AttackType.BRUTE_FORCE: PlaybookID.PB_BRUTEFORCE,
            AttackType.DNS_FLOOD: PlaybookID.PB_DNS_FLOOD,
            AttackType.ICMP_FLOOD: PlaybookID.PB_ICMP_FLOOD,
            AttackType.SYN_FLOOD: PlaybookID.PB_SYN_FLOOD,
            AttackType.UDP_FLOOD: PlaybookID.PB_UDP_FLOOD
        }
        
    def select(self, attack_type_str: str) -> PlaybookID:
        try:
            enum_val = AttackType(attack_type_str)
            return self.mapping[enum_val]
        except ValueError:
            return PlaybookID.PB_BENIGN # Safe default

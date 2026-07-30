import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ActionExecutor:
    """
    Action Simulator that mocks OS-level defense commands.
    """
    def block_ip_firewall(self, ip: str) -> None:
        """Simulates an iptables drop rule."""
        logger.info(f"[EXECUTOR] Executing iptables drop for IP: {ip}")
        print(f"🔥 [FIREWALL] IP {ip} has been blocked at the network level.")
        
    def apply_rate_limiting(self, ip: str) -> None:
        """Simulates applying a rate limit."""
        logger.info(f"[EXECUTOR] Applying rate limiting for IP: {ip}")
        print(f"⏳ [RATE LIMIT] Traffic from IP {ip} is now rate limited.")
        
    def reset_user_credentials(self, ip: str) -> None:
        """Simulates forcing a user credential reset."""
        logger.info(f"[EXECUTOR] Resetting credentials associated with IP: {ip}")
        print(f"🔑 [IAM] Forced password reset for accounts accessed from {ip}.")

    def execute_playbook(self, playbook: str, ip: str) -> None:
        """
        Routes execution to the correct simulation methods based on the playbook.
        """
        if playbook == "BLOCK_IP":
            self.block_ip_firewall(ip)
        elif playbook == "RATE_LIMIT":
            self.apply_rate_limiting(ip)
            self.reset_user_credentials(ip)
        elif playbook == "MANUAL_INVESTIGATION":
            logger.info(f"[EXECUTOR] Manual investigation ticket generated for IP: {ip}")
        else:
            logger.info(f"[EXECUTOR] No active response defined for playbook: {playbook}")

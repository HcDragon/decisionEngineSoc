import logging
from typing import List, Dict, Any

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class SimulationExecutor:
    """
    Action Simulator that safely mocks OS-level defense commands.
    """
    def _simulate_action(self, action_name: str, ip: str, message: str) -> Dict[str, str]:
        logger.info(f"[EXECUTOR] {message} for IP: {ip}")
        print(f"🔧 [SIMULATION] {action_name}: {message} ({ip})")
        return {
            "action": action_name,
            "mode": "SIMULATION",
            "status": "SUCCESS",
            "message": f"{message} for {ip}."
        }

    def execute_actions(self, actions: List[str], ip: str) -> List[Dict[str, str]]:
        """
        Executes a list of simulated actions.
        """
        results = []
        for action in actions:
            if action in ("BLOCK_SOURCE_IP", "TEMP_BLOCK_IP"):
                results.append(self._simulate_action(action, ip, "Source IP blocked at firewall"))
            elif action in ("DNS_RATE_LIMIT", "UDP_RATE_LIMIT", "RATE_LIMIT"):
                results.append(self._simulate_action(action, ip, "Traffic rate limited"))
            elif action == "RESET_CREDENTIALS":
                results.append(self._simulate_action(action, ip, "Forced password reset"))
            elif action in ("NOTIFY_SOC", "NOTIFY_ANALYST"):
                results.append(self._simulate_action(action, ip, "Notification sent to SOC analyst"))
            elif action == "CREATE_INCIDENT":
                results.append(self._simulate_action(action, ip, "Incident ticket created in ITSM"))
            elif action in ("ICMP_FILTER", "SYN_PROTECTION"):
                results.append(self._simulate_action(action, ip, "Protocol specific protection enabled"))
            elif action == "LOG_ONLY":
                results.append(self._simulate_action(action, ip, "Traffic logged for monitoring"))
            else:
                results.append({
                    "action": action,
                    "mode": "SIMULATION",
                    "status": "WARNING",
                    "message": f"Action {action} is not natively mapped to a simulation."
                })
        return results

class ActionExecutor(SimulationExecutor):
    """
    Backward-compatible alias for SimulationExecutor.
    """
    pass

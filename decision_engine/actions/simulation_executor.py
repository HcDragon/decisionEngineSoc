from typing import List, Dict, Any, Optional
from decision_engine.actions.adapters.simulation_adapter import SimulationAdapter
from decision_engine.models.action import ActionResult

class SimulationExecutor:
    """
    Direct Simulation Executor for backwards compatibility.
    """
    def __init__(self):
        self.adapter = SimulationAdapter()

    LEGACY_ACTION_MAP = {
        "BLOCK_SOURCE_IP": "BLOCK_IP_SIMULATION",
        "SYN_PROTECTION": "RATE_LIMIT_SIMULATION",
        "RATE_LIMIT_IP": "RATE_LIMIT_SIMULATION",
        "ISOLATE_PORT": "ISOLATE_HOST_SIMULATION"
    }

    def execute_actions(self, actions: List[str], ip: str) -> List[Dict[str, str]]:
        results = []
        for act in actions:
            target_act = self.LEGACY_ACTION_MAP.get(act, act)
            res: ActionResult = self.adapter.execute_action(action=target_act, target=ip)
            results.append({
                "action": act,
                "mode": res.mode.value,
                "status": res.status.value,
                "message": res.message
            })
        return results

class ActionExecutor(SimulationExecutor):
    """Alias for backwards compatibility."""
    pass

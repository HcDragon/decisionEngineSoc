from typing import List, Dict, Any, Optional
from decision_engine.actions.adapters.simulation_adapter import SimulationAdapter
from decision_engine.models.action import ActionResult

class SimulationExecutor:
    """
    Direct Simulation Executor for backwards compatibility.
    """
    def __init__(self):
        self.adapter = SimulationAdapter()

    def execute_actions(self, actions: List[str], ip: str) -> List[Dict[str, str]]:
        results = []
        for act in actions:
            res: ActionResult = self.adapter.execute_action(action=act, target=ip)
            results.append({
                "action": res.action,
                "mode": res.mode.value,
                "status": res.status.value,
                "message": res.message
            })
        return results

class ActionExecutor(SimulationExecutor):
    """Alias for backwards compatibility."""
    pass

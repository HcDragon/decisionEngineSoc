from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decision_engine.models.action import ActionResult

class BaseActionAdapter(ABC):
    """
    Abstract interface for security action executors.
    Concrete implementations can be SimulationAdapter, LinuxFirewallAdapter, WindowsFirewallAdapter, etc.
    """
    @abstractmethod
    def execute_action(
        self,
        action: str,
        target: str,
        parameters: Optional[Dict[str, Any]] = None,
        incident_id: Optional[str] = None
    ) -> ActionResult:
        """Execute a single security action on a specified target."""
        pass

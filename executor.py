"""
Backward-compatible re-export for ActionExecutor and SimulationExecutor.
Canonical implementations live in core.executor.
"""
from core.executor import SimulationExecutor, ActionExecutor

__all__ = ["SimulationExecutor", "ActionExecutor"]

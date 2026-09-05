import os
import yaml
from typing import List, Optional
from decision_engine.models.policy import PolicyDefinition

class PolicyLoader:
    """
    Loads and parses YAML policy definitions with caching to avoid repeated disk reads.
    """
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "policies.yaml")
        self.config_path = config_path
        self._policies: List[PolicyDefinition] = []
        self._last_mtime: float = 0.0
        self.reload()

    def reload(self) -> List[PolicyDefinition]:
        if not os.path.exists(self.config_path):
            self._policies = []
            return self._policies
            
        mtime = os.path.getmtime(self.config_path)
        if mtime == self._last_mtime and self._policies:
            return self._policies
            
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        raw_list = data.get("policies", [])
        loaded = []
        for item in raw_list:
            try:
                pol = PolicyDefinition(**item)
                loaded.append(pol)
            except Exception as e:
                pass
                
        self._policies = loaded
        self._last_mtime = mtime
        return self._policies

    @property
    def policies(self) -> List[PolicyDefinition]:
        return self._policies

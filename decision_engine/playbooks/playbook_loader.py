import os
import yaml
from typing import Dict, List, Optional
from decision_engine.models.playbook import PlaybookDefinition, PlaybookStep

class PlaybookLoader:
    """
    Loads and caches Playbook definitions from YAML configuration.
    """
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "playbooks.yaml")
        self.config_path = config_path
        self._playbooks: Dict[str, PlaybookDefinition] = {}
        self._last_mtime: float = 0.0
        self.reload()

    def reload(self) -> Dict[str, PlaybookDefinition]:
        if not os.path.exists(self.config_path):
            return self._playbooks
            
        mtime = os.path.getmtime(self.config_path)
        if mtime == self._last_mtime and self._playbooks:
            return self._playbooks
            
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        raw_list = data.get("playbooks", [])
        loaded = {}
        for item in raw_list:
            try:
                pb = PlaybookDefinition(**item)
                loaded[pb.playbook_id] = pb
            except Exception as e:
                pass
                
        self._playbooks = loaded
        self._last_mtime = mtime
        return self._playbooks

    def get_playbook(self, playbook_id: str) -> Optional[PlaybookDefinition]:
        self.reload()
        return self._playbooks.get(playbook_id) or self._playbooks.get("PB-DEFAULT")

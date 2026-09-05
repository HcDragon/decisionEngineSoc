from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

class PlaybookStep(BaseModel):
    step_number: int
    action: str
    description: Optional[str] = None
    required: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)

class PlaybookDefinition(BaseModel):
    playbook_id: str
    name: str
    description: Optional[str] = None
    steps: List[PlaybookStep] = Field(default_factory=list)

class PlaybookExecutionRecord(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"PBX-{uuid.uuid4().hex[:8]}")
    playbook_id: str
    incident_id: str
    current_step: int = 0
    total_steps: int = 0
    status: str = "IN_PROGRESS" # IN_PROGRESS, COMPLETED, FAILED, WAITING_APPROVAL
    step_results: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

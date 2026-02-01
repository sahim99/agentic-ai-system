from typing import List, Optional
from enum import Enum
from pydantic import BaseModel

class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentType(str, Enum):
    RETRIEVER = "retriever"
    ANALYZER = "analyzer"
    WRITER = "writer"

class Step(BaseModel):
    id: int
    title: str
    description: str
    assigned_agent: AgentType
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None

class TaskPlan(BaseModel):
    task_id: str
    original_prompt: str
    steps: List[Step]

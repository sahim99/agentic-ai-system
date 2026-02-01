from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class EventType(str, Enum):
    STATUS = "status"
    PARTIAL_OUTPUT = "partial_output"
    ERROR = "error"
    DONE = "done"

class EventSource(str, Enum):
    SYSTEM = "system"
    PLANNER = "planner"
    RETRIEVER = "retriever"
    ANALYZER = "analyzer"
    WRITER = "writer"

class Event(BaseModel):
    type: EventType
    source: EventSource
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.isoformat(datetime.now()))

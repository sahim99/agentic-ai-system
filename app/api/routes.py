import uuid
import logging
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from ..models.events import Event, EventType, EventSource
from ..queue.redis_client import redis_client
from ..streaming.sse import event_generator
from ..core.orchestrator import Orchestrator

router = APIRouter()
logger = logging.getLogger(__name__)
orchestrator = Orchestrator()

class TaskRequest(BaseModel):
    task: str

@router.post("/task")
async def submit_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Submits a new task.
    Triggers orchestration in the background.
    Returns the task_id.
    """
    task_id = str(uuid.uuid4())
    logger.info(f"Received new task request, generated ID: {task_id}")
    
    # Publish initial status event
    initial_event = Event(
        type=EventType.STATUS,
        source=EventSource.SYSTEM,
        message="Task received. Initializing planner..."
    )
    
    await redis_client.publish_event(task_id, initial_event)
    
    # Trigger Orchestrator in Background
    background_tasks.add_task(orchestrator.process_task, task_id, request.task)
    
    return {"task_id": task_id}

@router.get("/stream/{task_id}")
async def stream_task(task_id: str):
    """
    Streams updates for the given task_id using SSE.
    """
    logger.info(f"Client connected to stream for task: {task_id}")
    return EventSourceResponse(event_generator(task_id))

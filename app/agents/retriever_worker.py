import asyncio
import logging
from ..queue.redis_client import redis_client
from ..models.events import Event, EventType, EventSource
from ..models.task import AgentType
from .base_worker import BaseWorker

logger = logging.getLogger(__name__)

class RetrieverWorker(BaseWorker):
    def __init__(self):
        super().__init__(AgentType.RETRIEVER, redis_client)

    async def process_step(self, task_id: str, step_id: str, instruction: str, retry_count: int):
        # Failure Simulation
        if "SIMULATE_FAILURE" in instruction and retry_count == 0:
            raise Exception("Simulated Retriever Failure")

        # 1. Emit Status: Searching
        await self.redis.publish_event(task_id, Event(
            type=EventType.STATUS,
            source=EventSource.RETRIEVER,
            message=f"Searching for data: {instruction[:30]}..."
        ))
        
        # Simulate work
        await asyncio.sleep(2)
        
        # 2. Emit Status: Retrieved
        await self.redis.publish_event(task_id, Event(
            type=EventType.STATUS,
            source=EventSource.RETRIEVER,
            message=f"Retrieved 5 sources for step {step_id}."
        ))

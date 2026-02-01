import asyncio
import logging
from abc import ABC, abstractmethod
from ..queue.redis_client import RedisClient
from ..models.events import Event, EventType, EventSource
from ..models.task import AgentType

logger = logging.getLogger(__name__)

class BaseWorker(ABC):
    def __init__(self, agent_type: AgentType, redis: RedisClient):
        self.agent_type = agent_type
        self.redis = redis
        self.is_running = False
        # Queue name convention: queue:{agent_name}
        self.queue_name = f"queue:{agent_type.value}"
        self.agent_name = agent_type.value.capitalize()

    async def run(self):
        """
        Infinite loop to consume messages from the agent's Redis Stream.
        
        Architecture Note:
        - Workers act as independent async consumers.
        - Processing is "fire-and-forget" from the Orchestrator's perspective.
        - Each worker processes one message at a time (Manual Batching via Redis Streams).
        """
        self.is_running = True
        logger.info(f"[{self.agent_name}] Worker started listening on {self.queue_name}")
        
        last_id = "0-0"
        while self.is_running:
            try:
                # Read from own queue
                streams = await self.redis.redis.xread({self.queue_name: last_id}, count=1, block=2000)
                
                if not streams:
                    continue
                
                for stream_name, messages in streams:
                    for msg_id, data in messages:
                        last_id = msg_id
                        await self.process_message(data)
                        
            except Exception as e:
                logger.error(f"[{self.agent_name}] Infrastructure error: {e}")
                await asyncio.sleep(1)

    async def process_message(self, data: dict):
        """
        Orchestrate step processing with Retry Logic.
        """
        task_id = data.get("task_id")
        step_id = data.get("step_id")
        instruction = data.get("instruction")
        retry_count = int(data.get("retry_count", 0))
        
        if not task_id or not instruction:
            logger.warning(f"[{self.agent_name}] Invalid message format in {self.queue_name}: {data}")
            return

        logger.info(f"[{self.agent_name}] Processing step {step_id} for task {task_id} (Attempt {retry_count + 1})")
        
        try:
            # Execute the actual work
            await self.process_step(task_id, str(step_id), instruction, retry_count)
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Failed to process step {step_id} for task {task_id}: {e}")
            
            # Retry Logic
            if retry_count < 3:
                new_retry_count = retry_count + 1
                backoff_time = 2 ** retry_count  # 1s, 2s, 4s
                
                # Emit Error/Retry Event
                await self.redis.publish_event(task_id, Event(
                    type=EventType.ERROR,
                    source=EventSource(self.agent_type.value),
                    message=f"[{self.agent_name}] ERROR: {str(e)} (retry {new_retry_count}/3)"
                ))
                
                # Wait (Backoff)
                await asyncio.sleep(backoff_time)
                
                # Re-queue the message with updated retry_count
                await self.redis.redis.xadd(self.queue_name, {
                    "task_id": task_id,
                    "step_id": step_id,
                    "instruction": instruction,
                    "retry_count": new_retry_count
                })
                logger.info(f"[{self.agent_name}] Re-queued step {step_id} due to error.")
                
            else:
                # Dead Letter handling (Max Retries Exhausted)
                await self.redis.publish_event(task_id, Event(
                    type=EventType.ERROR,
                    source=EventSource(self.agent_type.value),
                    message=f"[{self.agent_name}] ERROR: Failed after max retries. Details: {str(e)}"
                ))
                logger.critical(f"[{self.agent_name}] Step {step_id} for task {task_id} moved to dead-letter (log only) after {retry_count} retries.")

    @abstractmethod
    async def process_step(self, task_id: str, step_id: str, instruction: str, retry_count: int):
        pass

    def stop(self):
        self.is_running = False

import logging
import asyncio
from ..models.task import TaskPlan, StepStatus
from ..models.events import Event, EventType, EventSource
from ..queue.redis_client import redis_client
from ..agents.planner import PlannerAgent

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.planner = PlannerAgent()

    async def process_task(self, task_id: str, task_input: str):
        """
        Orchestrates the entire lifecycle of a task.
        
        Architecture Note:
        - This method acts as a "Fire-and-Forget" dispatcher.
        - Steps are pushed to Redis Streams (queues).
        - Workers consume these independently and asynchronously.
        - No blocking wait for step completion here.
        
        1. Calls Planner to get steps.
        2. Dispatches steps to appropriate queues.
        """
        logger.info(f"Orchestrator processing task {task_id}")

        try:
            # 1. Planning Phase
            plan = await self.planner.plan(task_id, task_input)

            # 2. Execution Phase (Dispatching)
            for step in plan.steps:
                await self._dispatch_step(task_id, step)
                # In a real system, we'd wait for completion here or use a state machine.
                # For Phase 2, we just dispatch and verify the flow.
                await asyncio.sleep(0.5) 

            # 3. Completion (Dispatching Complete)
            logger.info(f"Task {task_id}: All steps dispatched.")
            # We do NOT emit DONE here because workers are still running asynchronously.
            # The last worker (Writer) will emit the DONE event.

        except Exception as e:
            logger.error(f"Orchestration failed for task {task_id}: {e}")
            await redis_client.publish_event(task_id, Event(
                type=EventType.ERROR,
                source=EventSource.SYSTEM,
                message=f"System error: {str(e)}"
            ))

    async def _dispatch_step(self, task_id: str, step):
        """
        Dispatches a single step to its agent's Redis stream.
        """
        # Publish to user stream that we are dispatching
        await redis_client.publish_event(task_id, Event(
            type=EventType.STATUS,
            source=EventSource.SYSTEM, # Marked as System/Orchestrator
            message=f"Step {step.id}: Dispatching '{step.title}' to {step.assigned_agent.value}"
        ))

        # Push to specific agent queue (Redis Stream)
        # e.g. "queue:retriever"
        agent_queue = f"queue:{step.assigned_agent.value}"
        
        # We put the task_id and step details in the queue
        await redis_client.redis.xadd(agent_queue, {
            "task_id": task_id,
            "step_id": step.id,
            "instruction": step.description
        })

        logger.info(f"Dispatched step {step.id} to {agent_queue}")

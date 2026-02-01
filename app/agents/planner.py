import asyncio
import logging
import json
from typing import List
from ..models.task import Step, StepStatus, AgentType, TaskPlan
from ..models.events import Event, EventType, EventSource
from ..queue.redis_client import redis_client
from ..core.groq_client import get_groq_client

logger = logging.getLogger(__name__)

class PlannerAgent:
    async def plan(self, task_id: str, task_input: str) -> TaskPlan:
        """
        Decomposes a user task into steps.
        Strategy:
        1. Attempt to use Groq LLM for intelligent decomposition.
        2. If Groq fails or is disabled (Resilient Fallback), use deterministic logic.
        """
        logger.info(f"Planner started for task {task_id}")

        # 1. Emit "Planning started" event
        await redis_client.publish_event(task_id, Event(
            type=EventType.STATUS,
            source=EventSource.PLANNER,
            message="Analyzing task requirements..."
        ))

        # 2. Try Groq (Cognitive Layer)
        steps = None
        try:
            groq = get_groq_client()
            if groq:
                logger.info("Attempting planning via Groq...")
                chat_completion = groq.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"""
                            You are a precise Task Planner.
                            Decompose the user's task into exactly 3 steps for these agents:
                            1. {AgentType.RETRIEVER.value}
                            2. {AgentType.ANALYZER.value} 
                            3. {AgentType.WRITER.value}
                            
                            Return ONLY valid JSON in this format:
                            [{{ "title": "...", "description": "...", "assigned_agent": "retriever" }}, ...]
                            """
                        },
                        {
                            "role": "user",
                            "content": task_input,
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )
                
                content = chat_completion.choices[0].message.content
                plan_data = json.loads(content)
                
                # Handle both list and wrapped dict formats
                items = plan_data if isinstance(plan_data, list) else plan_data.get("steps", [])
                
                if not items:
                     # Attempt to parse raw list if wrapped in keys like "steps"
                    if "steps" in plan_data:
                        items = plan_data["steps"]
                    else:
                         # Fallback for LLM weirdness
                        raise ValueError(f"Could not parse steps from JSON: {content}")
                        
                steps = []
                for i, item in enumerate(items):
                     steps.append(Step(
                         id=i+1,
                         title=item.get("title", f"Step {i+1}"),
                         description=item.get("description", "Perform task"),
                         assigned_agent=AgentType(item.get("assigned_agent").lower())
                     ))
                     
                logger.info(f"Groq successfully planned {len(steps)} steps.")

        except Exception as e:
            logger.warning(f"Groq planning failed: {e}. Falling back to deterministic logic.")
            steps = None

        # 3. Deterministic Fallback (Safety Net)
        if not steps:
            logger.info("Using deterministic planner fallback.")
            await asyncio.sleep(1.5) # Simulate thinking
            steps = [
                Step(
                    id=1,
                    title="Research Topic",
                    description=f"Gather information about: {task_input}",
                    assigned_agent=AgentType.RETRIEVER
                ),
                Step(
                    id=2,
                    title="Analyze Data",
                    description="Process and summarize the gathered information.",
                    assigned_agent=AgentType.ANALYZER
                ),
                Step(
                    id=3,
                    title="Draft Content",
                    description="Write the final response based on analysis.",
                    assigned_agent=AgentType.WRITER
                )
            ]

        # 4. Finalize Plan
        task_plan = TaskPlan(
            task_id=task_id,
            original_prompt=task_input,
            steps=steps
        )

        # 5. Emit "Planning complete" event
        await redis_client.publish_event(task_id, Event(
            type=EventType.STATUS,
            source=EventSource.PLANNER,
            message=f"Task decomposed into {len(steps)} steps."
        ))

        return task_plan

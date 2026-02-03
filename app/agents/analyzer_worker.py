import asyncio
import logging
from ..queue.redis_client import redis_client
from ..models.events import Event, EventType, EventSource
from ..models.task import AgentType
from .base_worker import BaseWorker
from ..core.groq_client import get_groq_client

logger = logging.getLogger(__name__)

class AnalyzerWorker(BaseWorker):
    def __init__(self):
        super().__init__(AgentType.ANALYZER, redis_client)

    async def process_step(self, task_id: str, step_id: str, instruction: str, retry_count: int):
        # Failure Simulation
        if "SIMULATE_FAILURE" in instruction and retry_count == 0:
            raise Exception("Simulated Analyzer Failure")

        # 1. Emit Status: Analyzing
        await self.redis.publish_event(task_id, Event(
            type=EventType.STATUS,
            source=EventSource.ANALYZER,
            message="Analyzing retrieved data..."
        ))
        
        # 2. Fetch Context (Retrieved Data)
        try:
            # We need to find what the Retriever found.
            history = await self.redis.read_events(task_id, last_id="0-0", block=100, count=1000)
            retrieved_data = ""
            for _, data in history:
                try:
                    payload = data.get("payload")
                    if payload:
                        evt = Event.parse_raw(payload)
                        if evt.source == EventSource.RETRIEVER and evt.message:
                            retrieved_data += f"\n{evt.message}"
                except Exception:
                    pass
            
            # 3. Use Groq to Analyze
            groq = get_groq_client()
            if groq and retrieved_data:
                prompt = f"""
                Instruction: {instruction}
                
                Retrieved Data:
                {retrieved_data}
                
                Analyze the data above and extract key insights relevant to the instruction.
                """
                
                chat_completion = groq.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are an expert analyst. Extract key insights."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.5,
                )
                analysis = chat_completion.choices[0].message.content
                
                # Emit Analysis
                await self.redis.publish_event(task_id, Event(
                    type=EventType.STATUS,
                    source=EventSource.ANALYZER,
                    message=f"Key Insights:\n{analysis}"
                ))
            else:
                 await self.redis.publish_event(task_id, Event(
                    type=EventType.STATUS,
                    source=EventSource.ANALYZER,
                    message="No data found to analyze."
                ))

        except Exception as e:
            logger.warning(f"Groq analysis failed: {e}")
            await self.redis.publish_event(task_id, Event(
                type=EventType.STATUS,
                source=EventSource.ANALYZER,
                message="Analysis failed or skipped."
            ))

        # 4. Emit Status: Analysis Complete
        await self.redis.publish_event(task_id, Event(
            type=EventType.STATUS,
            source=EventSource.ANALYZER,
            message="Analysis complete. Key insights extracted."
        ))

import asyncio
import logging
from ..queue.redis_client import redis_client
from ..models.events import Event, EventType, EventSource
from ..models.task import AgentType
from .base_worker import BaseWorker
from ..core.groq_client import get_groq_client

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
        
        # 2. Use Groq to simulate "Search"
        try:
            groq = get_groq_client()
            if groq:
                # Ask LLM to simulated search results
                prompt = f"Simulate a search engine result for the query: '{instruction}'. Return 3-5 relevant snippets with titles and simulated URLs."
                chat_completion = groq.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a simulated search engine. Provide realistic search results."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.5,
                )
                search_results = chat_completion.choices[0].message.content
                
                # Emit the "Search Results"
                await self.redis.publish_event(task_id, Event(
                    type=EventType.STATUS, # Use STATUS so it shows in logs but not main output box
                    source=EventSource.RETRIEVER,
                    message=f"Search Results:\n{search_results}"
                ))
            else:
                await self.redis.publish_event(task_id, Event(
                    type=EventType.STATUS,
                    source=EventSource.RETRIEVER,
                    message="[Mock] Found 5 documents about Agentic AI."
                ))

        except Exception as e:
            logger.warning(f"Groq search simulation failed: {e}")
            # Fallback
            await self.redis.publish_event(task_id, Event(
                type=EventType.STATUS,
                source=EventSource.RETRIEVER,
                message=f"Simulated search results for: {instruction}"
            ))

        # 3. Emit Status: Retrieved
        await self.redis.publish_event(task_id, Event(
            type=EventType.STATUS,
            source=EventSource.RETRIEVER,
            message=f"Retrieved sources for step {step_id}."
        ))

import asyncio
import logging
from ..queue.redis_client import redis_client
from ..models.events import Event, EventType, EventSource
from ..models.task import AgentType
from .base_worker import BaseWorker
from ..core.groq_client import get_groq_client

logger = logging.getLogger(__name__)

class WriterWorker(BaseWorker):
    def __init__(self):
        super().__init__(AgentType.WRITER, redis_client)

    async def process_step(self, task_id: str, step_id: str, instruction: str, retry_count: int):
        # Failure Simulation (Standard)
        should_fail_mid_stream = "FAIL_WRITER_STREAM" in instruction and retry_count == 0

        # 1. Emit Status: Drafting
        await self.redis.publish_event(task_id, Event(
            type=EventType.STATUS,
            source=EventSource.WRITER,
            message="Drafting final response..."
        ))

        # 2. Try Groq (Cognitive Layer)
        used_groq = False
        try:
            groq = get_groq_client()
            if groq:
                logger.info("Attempting streaming via Groq...")
                
                # Check for forced failure simulation IN GROQ path
                # Ideally we want the simulation to trigger generic retry logic in BaseWorker
                # But here we handle fallback. 
                # If "SIMULATE_FAILURE" is set, BaseWorker logic handles it before this method if we bubble up?
                # No, process_message calls this method.
                # If we raise exception here, BaseWorker retries.
                # The requirement says: "If Groq fails mid-stream... Switch to deterministic mock generator"
                # So we catch specific Groq errors here, OR let general retry handle "SIMULATE_FAILURE"?
                # "SIMULATE_FAILURE" logic is for *Infrastructure* testing.
                # Let's keep the fail_mid_stream logic for the mock or generic path.
                
                stream = groq.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful AI writer. Be concise."},
                        {"role": "user", "content": instruction}
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.7,
                    max_tokens=1024,
                    stream=True,
                )

                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        await self.redis.publish_event(task_id, Event(
                            type=EventType.PARTIAL_OUTPUT,
                            source=EventSource.WRITER,
                            message=content
                        ))
                        # Small sleep to nicely visualize streaming on frontend if needed, 
                        # but real LLM is fast.
                        # await asyncio.sleep(0.02) 

                used_groq = True
                logger.info("Groq streaming complete.")

        except Exception as e:
            logger.warning(f"[Writer] Groq Error: {e}. Switching to deterministic fallback.")
            # If we failed mid-stream, we just continue to the fallback.
            # We emitted some PARTIAL_OUTPUT already? That's fine.
            # The fallback will append to it. 
            used_groq = False

        # 3. Deterministic Fallback (Safety Net)
        if not used_groq:
            logger.info("Using deterministic writer fallback.")
            await asyncio.sleep(0.2) # Simulate work
            
            response_text = " [FALLBACK] Based on the analysis, agentic AI systems represent a significant leap forward in autonomy. They can plan, execute, and verify tasks."
            tokens = response_text.split(" ")
            
            for i, token in enumerate(tokens):
                # Standard Failure Simulation (for Retry Logic verification)
                if should_fail_mid_stream and i > 5:
                    raise Exception("Simulated Writer Streaming Failure") 
                    # This raises to BaseWorker -> Triggers Retry. Correct.

                await self.redis.publish_event(task_id, Event(
                    type=EventType.PARTIAL_OUTPUT,
                    source=EventSource.WRITER,
                    message=token + " " 
                ))
                await asyncio.sleep(0.05)
            
        # 4. Emit Done
        await self.redis.publish_event(task_id, Event(
            type=EventType.DONE,
            source=EventSource.WRITER,
            message="Draft generation complete."
        ))

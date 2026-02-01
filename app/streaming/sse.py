import asyncio
import logging
import json
from sse_starlette.sse import ServerSentEvent
from ..queue.redis_client import redis_client
from ..models.events import Event, EventType

logger = logging.getLogger(__name__)

async def event_generator(task_id: str):
    """
    Async generator for SSE.
    Listens to Redis Stream and yields SSE events.
    """
    last_id = "0-0"
    
    # We yield an initial comment to keep connection alive or signal start if needed
    # yield ServerSentEvent(comment="Connected to stream")

    while True:
        # Read from Redis
        # We use a blocking read (handled inside read_events via xread block)
        # to avoid tight loops.
        messages = await redis_client.read_events(task_id, last_id=last_id, block=2000)
        
        if not messages:
            # If no new messages, we can yield a comment to keep connection alive (heartbeat)
            # or just continue waiting.
            # yield ServerSentEvent(comment="heartbeat")
            # For now, we just continue loop to check again or handle shutdown
            await asyncio.sleep(0.1) 
            continue

        for msg_id, data in messages:
            last_id = msg_id
            payload_json = data.get("payload")
            
            if payload_json:
                try:
                    # Parse JSON to validate/ensure it's correct
                    # We pass the raw JSON string as the data for the SSE
                    event_data = Event.parse_raw(payload_json)
                    
                    yield ServerSentEvent(
                        data=event_data.json(),
                        event="message" # standard event name
                    )

                    # Stop streaming if DONE event received
                    if event_data.type == EventType.DONE:
                        logger.info(f"Task {task_id} done. Closing stream.")
                        return 
                        
                except Exception as e:
                    logger.error(f"Error parsing event {msg_id}: {e}")
                    yield ServerSentEvent(
                        data=json.dumps({"error": "Failed to parse event"}),
                        event="error"
                    )

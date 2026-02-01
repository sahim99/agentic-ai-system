import os
import json
import logging
import asyncio
import redis.asyncio as redis
from typing import List, Optional
from ..models.events import Event
from dotenv import load_dotenv

# Only load .env if environment variables are missing (Local Dev)
# In Docker, REDIS_URL is injected by docker-compose, so we skip .env to avoid override by volume mount.
if not os.getenv("REDIS_URL"):
    load_dotenv()

logger = logging.getLogger(__name__)

# Redis URL - assuming localhost:6379 as per requirements
# Fallback to localhost if not set, but we will validate connectivity.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class RedisClient:
    def __init__(self):
        # Case-insensitive environment check
        self.use_fake = os.getenv("USE_FAKE_REDIS", "false").lower() == "true"
        self.redis = None
        
        if self.use_fake:
            try:
                import fakeredis.aioredis
                logger.warning("⚠️ USING FAKE REDIS (IN-MEMORY) - FOR TESTING ONLY ⚠️")
                self.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
            except ImportError:
                logger.error("fakeredis not installed but USE_FAKE_REDIS=true. Run `pip install fakeredis`.")
                raise
        else:
            logger.info(f"🔌 Initializing Real Redis Client at {REDIS_URL}")
            # Validate URL format implicitly by creating connection pool
            try:
                self.redis = redis.from_url(
                    REDIS_URL, 
                    encoding="utf-8", 
                    decode_responses=True,
                    health_check_interval=30 # Keep-alive
                )
            except Exception as e:
                logger.critical(f"❌ Invalid REDIS_URL or configuration: {e}")
                raise

    async def check_connection(self):
        """
        Verifies connection to Redis. 
        Should be called on startup to fail fast if Redis is down (in Real mode).
        """
        if self.use_fake:
            return True
            
        try:
            await self.redis.ping()
            logger.info("✅ Redis Connection Verified.")
            return True
        except Exception as e:
            logger.critical(f"❌ FAILED to connect to Real Redis at {REDIS_URL}: {e}")
            logger.critical("👉 Please start Redis (e.g., `docker run -p 6379:6379 redis`) or set USE_FAKE_REDIS=true")
            # We don't raise here to allow the app to start, but likely it will fail later.
            # Ideally, startup logic should call this and decide to crash or not.
            return False

    async def publish_event(self, task_id: str, event: Event):
        """
        Publishes an event to the task's Redis Stream.
        Ensures payload is JSON-serializable and logs the action.
        """
        stream_key = f"task_events:{task_id}"
        
        try:
            # Validate payload serialization
            # Event.json() returns a string. Redis Streams XADD takes a dict {field: value}.
            # We wrap it in 'payload' to avoid field explosion and ensure schema consistency.
            payload_str = event.json()
            
            # Additional safety: ensure it's valid JSON (Pydantic does this, but defensive coding)
            # json.loads(payload_str) 

            await self.redis.xadd(stream_key, {"payload": payload_str})
            logger.info(f"📤 Published to {stream_key}: [{event.type}] {event.message[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish event to {stream_key}: {e}")
            # In a real system, you might raise here or push to a dead-letter queue locally.
            # For this agentic system, logging is critical.
            raise e

    async def read_events(self, task_id: str, last_id: str = "0-0", block: int = 5000) -> List[tuple]:
        """
        Reads new events from the stream.
        Returns a list of (stream_id, payload_dict).
        Handles connectivity errors gracefully.
        """
        stream_key = f"task_events:{task_id}"
        
        try:
            # xread returns: [[stream_key, [(msg_id, data), ...]], ...]
            # We ask for COUNT 10 just to be safe, but usually consume linear stream.
            streams = await self.redis.xread({stream_key: last_id}, count=10, block=block)
            
            if not streams:
                return []
            
            # Extract messages from the first (and only) stream
            _, messages = streams[0]
            return messages
            
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis Connection Lost during read: {e}")
            # Potentially wait/backoff? 
            # For now, return empty to not crash the consumer loop, user will just see pause.
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error reading stream {stream_key}: {e}")
            return []

    async def get_stream_length(self, task_id: str) -> int:
        """Helper to check stream depth (for validation)."""
        stream_key = f"task_events:{task_id}"
        try:
            return await self.redis.xlen(stream_key)
        except Exception:
            return 0

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.info("🔌 Redis Client Closed.")

# Global instance
redis_client = RedisClient()

async def get_redis_client() -> RedisClient:
    return redis_client

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .queue.redis_client import redis_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agentic AI System", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(router)

import asyncio
from .agents import RetrieverWorker, AnalyzerWorker, WriterWorker

# Global worker tasks
worker_tasks = []
workers = []

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    
    # Check Redis Connection
    is_connected = await redis_client.check_connection()
    if not is_connected:
        logger.warning("⚠️ Redis connection failed. Workers might loop with errors.")

    # Initialize Workers
    retriever = RetrieverWorker()
    analyzer = AnalyzerWorker()
    writer = WriterWorker()
    workers.extend([retriever, analyzer, writer])

    # Start Workers as Background Tasks
    for worker in workers:
        task = asyncio.create_task(worker.run())
        worker_tasks.append(task)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    
    # Stop workers
    for worker in workers:
        worker.stop()
    
    # Cancel tasks
    for task in worker_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
            
    await redis_client.close()

@app.get("/")
async def root():
    return {"message": "Agentic AI System API is running"}

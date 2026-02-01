# Agentic AI System for Multi Tasks

An advanced multi-agent AI system designed to plan, execute, and stream complex tasks with resilience and reliability.

## System Architecture

### Task Lifecycle
1.  **Submit**: User POSTs a request (`/task`).
2.  **Plan**: `PlannerAgent` decomposes request into steps.
3.  **Dispatch**: `Orchestrator` pushes steps to Redis Streams (`queue:retriever`, `queue:writer`).
4.  **Execute**: Async workers consume messages independently (Manual Batching).
5.  **Stream**: Real-time updates (Status, Partial Output, Errors) pushed to user via SSE.

### Technical Highlights
-   **Explicit Agent Boundaries**: Dedicated worker modules (`retriever_worker.py`, etc.).
-   **Cognitive Layer (Groq)**: Optional LLM integration for Planner (reasoning) and Writer (streaming), with automatic deterministic fallback.
-   **Resilience**: `BaseWorker` handles retries (exponential backoff) and dead-letters.
-   **Streaming**: `WriterWorker` emits tokens character-by-character.
-   **Testing**: Auto-fallback to `fakeredis` (in-memory) if Redis needs to be mocked.

## Requirements

- Python 3.9+
- Redis (standard or `fakeredis` fallback)
- (Optional) Groq API Key

## Configuration

To enable the cognitive layer (LLMs), set the environment variable:

```bash
set GROQ_API_KEY=gsk_...
set USE_GROQ=true
```
Groq is preferred but optional. The system always produces output, even when running fully offline.

If these are missing, the system automatically runs in **Deterministic Mode** (Mock Logic).

## Installation

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Start Redis** (Optional - system falls back to fake redis if missing):
    ```bash
    docker-compose up -d
    ```

## Running the Server

**Important**: Run all commands from the project root (`Agentic AI System for Multi Tasks`).

```bash
python -m uvicorn app.main:app --reload
```

Server will run at `http://localhost:8000`.

To start the **Live UI Dashboard**:

```bash
python -m streamlit run ui/app.py
```

The UI will open at `http://localhost:8501`.

## Testing & Verification

Integration tests verify the entire flow including failure handling.

```bash
python tests/integration_test.py
```

## Architecture

See `docs/system_design.md` for detailed architecture diagrams.

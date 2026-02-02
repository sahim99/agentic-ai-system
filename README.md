# Agentic AI System for Multi Tasks

![Agentic AI Dashboard](docs/images/dashboard_preview.png)

An advanced, event-driven multi-agent system designed to plan, execute, and stream complex tasks with resilience and reliability. Built with **FastAPI**, **Redis Streams**, and **Streamlit**.

## 🏗️ High-Level Architecture

The system follows a scalable, event-driven architecture using Redis Streams as the central message bus.

```text
User (Streamlit UI)
       ↓
FastAPI Backend (/task)
       ↓
PlannerAgent (Decomposes Task)
       ↓
Redis Streams (Event Bus)
       ↓
[ Orchestrator ] → Dispatch to Workers
       ↓
Agent Workers (Retriever, Analyzer, Writer)
       ↓
WriterWorker (SSE Stream)
       ↓
User (Live Updates)
```

## 🚀 Key Features

*   **Event-Driven Architecture**: Decoupled agents communicate exclusively via Redis Streams.
*   **Resilient Workers**: Automatic retries with exponential backoff and dead-letter handling.
*   **Real-Time Streaming**: Server-Sent Events (SSE) provide character-by-character updates to the UI.
*   **Hybrid Cognitive Layer**: Optional integration with **Groq LLMs** for reasoning, with automatic fallback to deterministic (mock) logic for offline reliability.
*   **Containerized**: Fully Dockerized stack with internal networking.

## 🛠️ Requirements

*   **Docker** (Recommended)
*   *Alternative:* Python 3.9+ and Redis Server

## ⚡ Quick Start (Recommended)

Run the entire system (Redis + Backend + Frontend) with a single command:

```bash
docker-compose up --build
```

Access the application:
*   **Frontend Dashboard**: [http://localhost:8501](http://localhost:8501)
*   **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

> **Note**: This runs a production-grade configuration where services communicate over an internal Docker network.

## ⚙️ Configuration

The system is designed to run out-of-the-box in **Deterministic Mode** (Mock Logic).
To enable LLM capabilities, create a `.env` file or set environment variables:

```env
GROQ_API_KEY=gsk_...
USE_GROQ=true
```

## 💻 Local Development

If you prefer running services individually (without Docker Compose):

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Start Redis**:
    Ensure Redis is running on port `6379`.

3.  **Run Backend**:
    ```bash
    python -m uvicorn app.main:app --reload
    ```
    (Runs at `http://localhost:8000`)

4.  **Run Frontend**:
    ```bash
    python -m streamlit run ui/app.py
    ```
    (Opens at `http://localhost:8501`)

## ✅ Testing

Run integration tests to verify the pipeline and failure handling:

```bash
python tests/integration_test.py
```

# Post Mortem - Phase 6

## Summary

Phase 6 successfully integrated a Cognitive Layer (Groq LLM) into the existing Event-Driven architecture without compromising stability. The system now supports "Hybrid Intelligence"—using LLMs for reasoning and drafting when available, but seamlessly falling back to deterministic logic when offline or failing.

## What Went Well

*   **Architecture Resilience**: The decision to keep `BaseWorker` and `Redis Streams` as the backbone meant that adding Groq was purely additive. The core loop (`fetch -> process -> ack`) remained untouched.
*   **Streaming Compatibility**: The `WriterWorker` was able to switch between an LLM stream (token chunks) and a mock stream (split string) using the same `PARTIAL_OUTPUT` event contract. The frontend/SSE consumer required 0 changes.
*   **Fallback Mechanism**: The "check-and-fail-over" pattern in `planner.py` and `writer_worker.py` proved robust. Tests showed that even mid-stream failures in Groq correctly triggered the deterministic fallback.

## Challenges

*   **Async Streaming**: Managing async iterators for the LLM stream while maintaining the ability to interrupt/fail gracefully was complex. We had to ensure that an exception in the stream generator didn't crash the worker but instead triggered the fallback.
*   **Testing Determinism**: Verifying that the system *doesn't* use the LLM when configured not to (or when keys are invalid) required careful environment variable management in the test suite (`tests/integration_test.py`).

## Mitigation Strategies

*   **Explicit State**: We use the `USE_GROQ` flag to explicitly control this behavior, preventing accidental usage in dev/test environments.

## Phase 7: UI & Reliability Overhaul

### Summary
We transformed the system from a backend-only API into a full-stack product with a **Professional Streamlit Dashboard**. The key challenge was bridging the gap between an **Event-Driven Backend** (Push) and **Streamlit's Rerun Architecture** (Pull/Reactive).

### What Went Well
*   **Visual Telemetry**: The "Live Execution Flow" (Graphviz) proved incredibly valuable for debugging. Seeing the `Orchestrator -> Retriever` edge light up green gave immediate confirmation of internal state.
*   **Single-Screen Experience**: Moving the architecture diagram to the sidebar and using a "Mission Report" layout successfully decluttered the UI, fixing the "scroll fatigue" issue.

### Lessons Learned (The "Infinite Rerun" Bug)
*   **Problem**: Initially, the UI would loop infinitely at the end of a task. The `DONE` event triggered a state update, which triggered a rerun, which re-read the event history, which again saw `DONE`.
*   **Fix**: We introduced a specific state flag `st.session_state.stream_completed`. Once `True`, the SSE consumer loop is structurally skipped in subsequent reruns.
*   **Takeaway**: In Streamlit, *never* drive control flow purely from derived data (like "is the last event distinct?"). Always use explicit boolean flags in `session_state` to latch state transitions.

## Phase 8: Production Dockerization

### Summary
We moved from a local Python script execution model to a fully containerized **Production Stack** using `docker-compose`. This involved orchestrating three distinct services (Redis, Backend, Frontend) and ensuring seamless communication over a private bridge network.

### Challenges
*   **Networking confusion**: The most significant challenge was the difference between `localhost` inside a container (which refers to itself) vs. `localhost` on the host machine. The Frontend initially failed to talk to the Backend because it was trying to connect to `127.0.0.1` instead of the Docker alias `backend`.
*   **Environment var precedence**: We discovered a critical bug where `python-dotenv` loaded the local `.env` file (mounted via volumes), overriding the `REDIS_URL` set by Docker Compose. This caused the container to try connecting to `localhost:6379` (where no Redis existed) instead of `redis:6379`.

### Mitigation
*   **Smart Config Loading**: We patched `redis_client.py` to only load `.env` if `REDIS_URL` is missing. This allows Docker's injected variables to take precedence while preserving local dev convenience.
*   **Internal vs Browser URLs**: We separated the `BACKEND_URL` (internal Docker DNS for server-side calls) from the Browser URL (external `localhost` for user access).

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

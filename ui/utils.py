from datetime import datetime

def format_timestamp(ts: str = None) -> str:
    """Returns formatted timestamp string."""
    if not ts:
        return datetime.now().strftime("%H:%M:%S")
    # You might want to parse actual ISO strings here if backend sends them
    return ts

def status_color(step_state: str) -> str:
    """
    Returns color for status badges.
    """
    if step_state == "running":
        return "blue"
    if step_state == "completed":
        return "green"
    if step_state == "pending":
        return "grey"
    return "grey"

def event_to_step_index(event) -> int:
    """
    Maps an event to the corresponding step index in the visual flow.
    Steps:
    0. Task Created
    1. Planning
    2. Dispatch
    3. Worker Execution
    4. Streaming Output
    5. Done
    """
    msg = event.get("message", "").lower()
    src = event.get("source", "").lower()
    evt_type = event.get("type", "").lower()

    if evt_type == "done":
        return 5
    if evt_type == "partial_output":
        return 4
    
    if src == "system":
        if "dispatching" in msg:
            return 2
        return 0 # Task created / System init
        
    if src == "planner":
        return 1
        
    if src in ["retriever", "analyzer", "writer"]:
        return 3
        
    return 0

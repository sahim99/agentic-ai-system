import requests
import json

BASE_URL = "http://localhost:8000"

def stream_events(task_id: str):
    """
    Yields events from the SSE stream for a given task ID.
    Reads line by line to strictly follow the 'Reads line by line' requirement.
    """
    url = f"{BASE_URL}/stream/{task_id}"
    try:
        # stream=True is crucial
        with requests.get(url, stream=True, timeout=120) as response:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    
                    # Parse SSE format
                    if decoded_line.startswith("data:"):
                        json_str = decoded_line[5:].strip()
                        try:
                            yield json.loads(json_str)
                        except json.JSONDecodeError:
                            pass 
                            
    except Exception as e:
        yield {"type": "error", "source": "ui", "message": f"Stream disconnected: {str(e)}"}

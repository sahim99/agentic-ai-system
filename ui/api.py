import requests

BASE_URL = "http://localhost:8000"

def check_backend():
    """Checks if the backend is reachable."""
    try:
        resp = requests.get(f"{BASE_URL}/")
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def submit_task(prompt: str) -> str:
    """Submits a task to the backend and returns the task ID."""
    try:
        resp = requests.post(f"{BASE_URL}/task", json={"task": prompt})
        resp.raise_for_status()
        return resp.json()["task_id"]
    except Exception as e:
        return None

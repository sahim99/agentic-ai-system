import requests
import subprocess
import time
import sys
import os
import socket
import signal

# Configuration
BASE_URL = "http://localhost:8000"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

def is_port_open(host, port):
    """Check if a port is open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0

def start_server(use_fake_redis=False):
    """Starts the Uvicorn server in a subprocess."""
    env = os.environ.copy()
    if use_fake_redis:
        env["USE_FAKE_REDIS"] = "true"
        print("🚀 Starting server with FAKE REDIS mode...")
    else:
        print("🚀 Starting server with REAL REDIS mode...")

    # Using python -m uvicorn to ensure correct python environment
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        env=env,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
        # We capture output to avoid clutter, but might need it for debugging tasks if it fails
    )
    return process

def wait_for_server(url, timeout=10):
    """Waits for the server to be responsive."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url)
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
    return False

def test_integration():
    server_process = None
    use_fake = False

    # 1. Detect Redis
    if is_port_open(REDIS_HOST, REDIS_PORT):
        print(f"✅ Redis detected at {REDIS_HOST}:{REDIS_PORT}. Using REAL Redis.")
    else:
        print(f"⚠️ Redis NOT detected at {REDIS_HOST}:{REDIS_PORT}.")
        print("⚠️ Switching to FAKE REDIS for verification.")
        use_fake = True

    try:
        # 2. Start Server
        server_process = start_server(use_fake_redis=use_fake)
        
        if not wait_for_server(BASE_URL):
            print("❌ Server failed to start within timeout.")
            # Print logs if failed
            outs, errs = server_process.communicate(timeout=1)
            print(f"Server STDOUT: {outs.decode()}")
            print(f"Server STDERR: {errs.decode()}")
            return

        print("✅ Server is up.")

        # 3. Create Task
        print("Creating task with SIMULATE_FAILURE...")
        # We inject the trigger string "SIMULATE_FAILURE" into the task prompt.
        # The Planner (mock) will pass this prompt into the instructions in `planner.py`.
        # However, the planner currently generates fixed steps steps...
        # Wait, the planner in Phase 2 takes the `task_input` and puts it into the description of Step 1:
        # Step(id=1, description=f"Gather information about: {task_input}", ...)
        # So passing it here is sufficient for Step 1 (Retriever) to see it.
        task_payload = {"task": "SIMULATE_FAILURE: Research agentic AI systems"}
        resp = requests.post(f"{BASE_URL}/task", json=task_payload)
        resp.raise_for_status()
        data = resp.json()
        task_id = data["task_id"]
        print(f"✅ Task created: {task_id}")

        # 4. Listen to Stream (Verification)
        print(f"Listening to stream: {BASE_URL}/stream/{task_id}")
        url = f"{BASE_URL}/stream/{task_id}"
        
        events_received = []
        required_patterns = {
            "retriever_retry": False,  # Expect "Retrying" message
            "retriever_success": False, # Expect it to eventually handle it
            "writer_stream": False
        }
        
        try:
            with requests.get(url, stream=True, timeout=30) as response:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        print(f"Received: {decoded_line}")
                        events_received.append(decoded_line)
                        
                        # Check for specific milestones
                        if "Retrying" in decoded_line and "Retriever" in decoded_line: # Assuming source field is Retriever
                             # The source field is technically lowercase "retriever" in JSON
                            required_patterns["retriever_retry"] = True
                            
                        if "Retrieved 5 sources" in decoded_line:
                            required_patterns["retriever_success"] = True

                        if 'type":"partial_output"' in decoded_line:
                            required_patterns["writer_stream"] = True
                            
                        # Assuming Writer is the last step and it finishes
                        if "Draft generation complete" in decoded_line:
                            print("✅ Writer finished.")
                            break
        except Exception as e:
            print(f"⚠️ Stream interrupted: {e}")

        # 5. Assertions
        print("\n--- Failure Resilience Verification Results ---")
        
        if required_patterns["retriever_retry"]:
            print("✅ Retriever Retry Logic: SUCCESS (Error event seen)")
        else:
            print("❌ Retriever Retry Logic: FAILED (No retry event)")

        if required_patterns["retriever_success"]:
            print("✅ Retriever Resilience: SUCCESS (Eventually succeeded)")
        else:
            print("❌ Retriever Resilience: FAILED (Did not recover)")

        if required_patterns["writer_stream"]:
             print("✅ System Stability: SUCCESS (Reached Writer)")
        else:
             print("❌ System Stability: FAILED (Did not reach writer)")

    except Exception as e:
        print(f"❌ critical failure: {e}")
    finally:
        # ALWAYS Print logs for debugging
        if server_process:
             try:
                # terminate first to flush?
                server_process.terminate()
                outs, errs = server_process.communicate(timeout=5)
                print(f"\n[{'FAKE' if use_fake else 'REAL'} REDIS LOGS] Server STDOUT:\n{outs.decode()}")
                print(f"[{'FAKE' if use_fake else 'REAL'} REDIS LOGS] Server STDERR:\n{errs.decode()}")
             except Exception as e:
                 print(f"Error reading logs: {e}")

if __name__ == "__main__":
    test_integration()

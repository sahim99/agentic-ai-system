
import asyncio
import requests
import time
import sys
import subprocess
import os

BASE_URL = "http://localhost:8000"

def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url)
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
    return False

def test_full_lifecycle():
    print("🧪 Starting End-to-End Validation (Real Redis Mode)...")
    
    # Check if server is up
    if not wait_for_server(BASE_URL):
        print("❌ Server not running. Please start it with `python -m uvicorn app.main:app`")
        return

    # 1. Create Task
    print("1️⃣ Creating Task...")
    try:
        resp = requests.post(f"{BASE_URL}/task", json={"task": "Explain quantum computing"})
        resp.raise_for_status()
        data = resp.json()
        task_id = data["task_id"]
        print(f"   ✅ Task Created: {task_id}")
    except Exception as e:
        print(f"   ❌ Task Creation Failed: {e}")
        return

    # 2. Listen to Stream (SSE)
    print(f"2️⃣ Listening to Event Stream for Task {task_id}...")
    stream_url = f"{BASE_URL}/stream/{task_id}"
    
    events_received = []
    
    try:
        with requests.get(stream_url, stream=True, timeout=30) as response:
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if "event: message" in decoded:
                        continue # Skip event type line
                    if "data:" in decoded:
                        print(f"   📥 Received: {decoded[:100]}...") # truncate for clean log
                        events_received.append(decoded)
                        
                        if "Done" in decoded or "Draft generation complete" in decoded:
                            print("   ✅ DONE event received.")
                            break
    except Exception as e:
        print(f"   ⚠️ Stream Interrupted: {e}")

    # 3. Validation Logic
    print("\n🧐 Validating Event Sequence...")
    has_status = any("status" in e.lower() for e in events_received)
    has_partial = any("partial_output" in e.lower() for e in events_received)
    
    if has_status:
        print("   ✅ Status Events Present")
    else:
        print("   ❌ Missing Status Events")
        
    if has_partial:
        print("   ✅ Partial Output Present (Streaming working)")
    else:
        print("   ❌ Missing Partial Output")

    print("\n🎉 Validation Complete.")

if __name__ == "__main__":
    test_full_lifecycle()

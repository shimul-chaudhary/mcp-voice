#!/usr/bin/env python3
"""Test the gateway invoke flow with an assistant."""
import json
import os
import urllib.request

# Load .env
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v

TENANT_URL = os.environ["TENANT_URL"]
API_KEY = os.environ["API_KEY"]
ASSISTANT_ID = os.environ["ASSISTANT_ID"]  # Set in .env


def api(method, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{TENANT_URL}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")[:500]
        return e.code, body_text


print(f"Host: {TENANT_URL}")
print(f"Assistant: {ASSISTANT_ID}")
print()

# Step 1: Create thread on the assistants endpoint
print("1. Creating thread...")
status, thread = api("POST", f"/api/v1/assistants/{ASSISTANT_ID}/threads", {
    "name": "voice-test",
})
print(f"   Status: {status}")
if status >= 400:
    print(f"   Error: {thread}")
    # Try an existing thread instead
    print("   Falling back to existing thread...")
    status, threads = api("GET", f"/api/v1/assistants/{ASSISTANT_ID}/threads")
    thread = threads["data"][0]
    print(f"   Using thread: {thread['id']} ({thread['name']})")

thread_id = thread["id"]
print(f"   Thread ID: {thread_id}")

# Step 2: Try invoke on various endpoint patterns
endpoints = [
    f"/api/v1/assistants/{ASSISTANT_ID}/threads/{thread_id}/actions/invoke",
    f"/api/v1/ai/threads/{thread_id}/actions/invoke",
    f"/api/v1/assistants/{ASSISTANT_ID}/actions/invoke",
]

question = "how do I create a bookmark?"
for ep in endpoints:
    print(f"\n2. Trying: {ep}")
    # Executor expects {"input": {"prompt": ...}}
    status, result = api("POST", ep, {
        "input": {"prompt": question},
    }, timeout=120)
    print(f"   Status: {status}")
    if status < 400:
        print(f"   Response: {json.dumps(result, indent=2)[:1500]}")
        break
    else:
        print(f"   Error: {str(result)[:500]}")
        # Also try {"prompt": ...} directly
        status2, result2 = api("POST", ep, {
            "prompt": question,
        }, timeout=120)
        print(f"   Alt format status: {status2}")
        if status2 < 400:
            print(f"   Response: {json.dumps(result2, indent=2)[:1500]}")
            break
        print(f"   Alt error: {str(result2)[:500]}")

#!/usr/bin/env python3
"""Test KB search with current API key."""
import json
import os
import sys
import urllib.request

# Load .env manually
with open(os.path.join(os.path.dirname(__file__), ".env")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v

TENANT_URL = os.environ["TENANT_URL"]
API_KEY = os.environ["API_KEY"]

def search_kb(kb_id, prompt="how to create a bookmark", top_n=3):
    req = urllib.request.Request(
        f"{TENANT_URL}/api/v1/knowledgebases/{kb_id}/actions/search",
        data=json.dumps({"prompt": prompt, "top_n": top_n, "searchMode": "FULL"}).encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            d = json.loads(resp.read())
            chunks = d.get("chunks", [])
            return len(chunks), chunks
    except Exception as e:
        return -1, str(e)

kbs_env = os.environ.get("TEST_KB_IDS", "")
if not kbs_env:
    print("Set TEST_KB_IDS in .env as comma-separated id:label pairs")
    print("Example: TEST_KB_IDS=abc-123:My KB,def-456:Other KB")
    sys.exit(1)

kbs = []
for entry in kbs_env.split(","):
    entry = entry.strip()
    if ":" in entry:
        kb_id, name = entry.split(":", 1)
        kbs.append((kb_id.strip(), name.strip()))
    else:
        kbs.append((entry, entry))

print(f"Using key ending: ...{API_KEY[-20:]}")
print()

for kb_id, name in kbs:
    count, data = search_kb(kb_id)
    if count > 0:
        preview = data[0].get("text", "")[:80]
        print(f"  {count} chunks  {name}")
        print(f"           -> {preview}...")
    elif count == 0:
        print(f"  0 chunks  {name}")
    else:
        print(f"  ERROR     {name}: {data}")

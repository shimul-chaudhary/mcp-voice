#!/usr/bin/env python3
"""Check KB indexing status on the tenant."""
import json
import os
import urllib.request

TENANT_URL = os.environ["TENANT_URL"]  # e.g. https://your-tenant.example.com
API_KEY = os.environ["API_KEY"]

def api_get(path):
    req = urllib.request.Request(
        f"{TENANT_URL}{path}",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def api_post(path, body):
    req = urllib.request.Request(
        f"{TENANT_URL}{path}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# List all KBs
data = api_get("/api/v1/knowledgebases?limit=50")
kbs_with_files = []
for kb in data.get("data", []):
    fc = kb.get("contentSummary", {}).get("fileCount", 0)
    if fc == 0:
        continue
    mig = kb.get("requiresMigration", False)
    adv = kb.get("advancedIndexing", False)
    hyb = kb.get("requiresHybridSearchMigration", False)
    name = kb.get("name", "")
    kid = kb.get("id", "")
    print(f"files={fc:5}  migration={str(mig):5}  advanced={str(adv):5}  hybridMig={str(hyb):5}  {kid}  {name}")
    kbs_with_files.append(kb)

print(f"\n--- Found {len(kbs_with_files)} KBs with files ---\n")

# Try searching KBs that don't require migration
for kb in kbs_with_files:
    mig = kb.get("requiresMigration", False)
    if mig:
        continue
    kid = kb.get("id", "")
    name = kb.get("name", "")
    fc = kb.get("contentSummary", {}).get("fileCount", 0)
    print(f"Testing search on: {name} ({kid}, {fc} files)...")
    try:
        result = api_post(f"/api/v1/knowledgebases/{kid}/actions/search", {
            "prompt": "how to create a bookmark",
            "top_n": 3,
            "searchMode": "FULL"
        })
        chunks = result.get("chunks", [])
        print(f"  -> Got {len(chunks)} chunks")
        if chunks:
            print(f"  -> First chunk: {chunks[0].get('text', '')[:100]}...")
    except Exception as e:
        print(f"  -> Error: {e}")

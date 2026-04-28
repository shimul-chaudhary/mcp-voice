"""Create or update a Vapi voice assistant backed by an MCP server.

Vapi's phone/Twilio path has a bug where native MCP tools are called as a single
bundled tool instead of individual tools. This script configures the assistant
with function-type tools that hit proxy.py, which then forwards to the MCP server.

Usage:
    python setup_assistant.py                  # auto-detect ngrok URL
    python setup_assistant.py --url <base_url> # explicit public base URL
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx
from dotenv import load_dotenv

VAPI_BASE = "https://api.vapi.ai"
ASSISTANT_NAME = os.getenv("VAPI_ASSISTANT_NAME", "MCP Voice Assistant")
STATE_FILE = ".vapi_state.json"

# Proxy runs on port 8001, ngrok points to 8001
PROXY_PORT = 8001


def get_ngrok_url() -> str | None:
    """Try to get the public URL from a running ngrok instance."""
    try:
        resp = httpx.get("http://127.0.0.1:4040/api/tunnels", timeout=3)
        resp.raise_for_status()
        tunnels = resp.json().get("tunnels", [])
        for t in tunnels:
            if t.get("proto") == "https":
                return t["public_url"]
        if tunnels:
            return tunnels[0]["public_url"]
    except (httpx.ConnectError, httpx.ReadError, httpx.HTTPStatusError):
        pass
    return None


def resolve_base_url(explicit: str | None) -> str:
    """Return the public base URL, preferring explicit > ngrok > localhost."""
    if explicit:
        return explicit.rstrip("/")

    ngrok = get_ngrok_url()
    if ngrok:
        print(f"Detected ngrok tunnel: {ngrok}")
        return ngrok

    print("No ngrok detected - using http://localhost:8001")
    print("(Vapi can only reach this if you expose it publicly via ngrok or similar)")
    return f"http://localhost:{PROXY_PORT}"


def fetch_proxy_tools(base_url: str) -> list[dict]:
    """Fetch MCP tools from the local proxy and convert to Vapi function tools."""
    from proxy import session, VOICE_TOOLS, _sanitize_schema
    session.ensure_ready()

    tools = []
    for mcp_tool in session.tools:
        name = mcp_tool.get("name", "")
        if name not in VOICE_TOOLS:
            continue
        schema = _sanitize_schema(dict(mcp_tool.get("inputSchema", {})))
        tool = {
            "type": "function",
            "function": {
                "name": name,
                "description": mcp_tool.get("description", ""),
                "parameters": schema,
            },
            "server": {
                "url": f"{base_url}/tool-call",
                "timeoutSeconds": 30,
            },
        }
        tools.append(tool)
    return tools


def build_assistant_payload(base_url: str, tools: list[dict]) -> dict:
    """Build the Vapi assistant configuration with function tools."""
    kb_id = os.getenv("KNOWLEDGEBASE_ID", "YOUR_KNOWLEDGEBASE_ID")
    tool_names = [t["function"]["name"] for t in tools]
    # Build tool selection rules dynamically from the available tools
    tool_rules = []
    if "search" in str(tool_names):
        tool_rules.append("- To find/list resources (apps, datasets, spaces, users): use the search tool")
    if "describe_app" in str(tool_names):
        tool_rules.append("- To describe an app: use the describe_app tool with the app ID")
    if "get_data_model" in str(tool_names):
        tool_rules.append("- To get an app's data model: first search to find the app, then use get_data_model with the app ID")
    if "get_fields" in str(tool_names):
        tool_rules.append("- To get fields in an app: use get_fields with the app ID")
    if "search_knowledgebase_chunks" in str(tool_names):
        tool_rules.append(f"- To answer documentation questions: use search_knowledgebase_chunks with knowledgeBaseId '{kb_id}' and the user's question as the prompt")
    tool_rules_text = "\n".join(tool_rules)

    return {
        "name": ASSISTANT_NAME,
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful cloud analytics voice assistant. "
                        "You can search for resources, explore analytics apps, "
                        "and answer questions about the platform.\n\n"
                        "PRONUNCIATION: This is a voice conversation read aloud by text-to-speech. "
                        "Keep technical terms clear and spell out abbreviations.\n\n"
                        f"TOOL SELECTION RULES:\n{tool_rules_text}\n"
                        "- NEVER use 'get_data_product' when the user asks about an app's data model. "
                        "Apps and data products are different things.\n\n"
                        "IMPORTANT: When the user says 'pick a random app', first search to list apps, "
                        "then pick one from the results.\n\n"
                        "Keep responses concise since this is a voice conversation. "
                        "Summarize results verbally rather than listing every detail. "
                        "If a tool returns long data, pick the most relevant highlights."
                    ),
                }
            ],
            "tools": tools,
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "21m00Tcm4TlvDq8ikWAM",
        },
        "firstMessage": "Hi, I'm your cloud analytics assistant. What can I help you with?",
        "endCallMessage": "Goodbye!",
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 600,
    }


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def create_assistant(api_key: str, payload: dict) -> dict:
    resp = httpx.post(
        f"{VAPI_BASE}/assistant",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def update_assistant(api_key: str, assistant_id: str, payload: dict) -> dict:
    resp = httpx.patch(
        f"{VAPI_BASE}/assistant/{assistant_id}",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Set up Vapi assistant backed by an MCP server")
    parser.add_argument("--url", help="Public base URL (default: auto-detect ngrok)")
    args = parser.parse_args()

    api_key = os.getenv("VAPI_API_KEY")
    if not api_key:
        print("Error: VAPI_API_KEY not set in .env")
        sys.exit(1)

    base_url = resolve_base_url(args.url)

    print("Fetching MCP tools from proxy...")
    tools = fetch_proxy_tools(base_url)
    if not tools:
        print("Error: No tools loaded from proxy. Is proxy.py running?")
        sys.exit(1)
    print(f"Loaded {len(tools)} tools: {[t['function']['name'] for t in tools]}")

    payload = build_assistant_payload(base_url, tools)

    state = load_state()
    assistant_id = state.get("assistant_id")

    if assistant_id:
        print(f"Updating existing assistant {assistant_id}...")
        result = update_assistant(api_key, assistant_id, payload)
        print(f"Updated assistant: {result['id']}")
    else:
        print("Creating new assistant...")
        result = create_assistant(api_key, payload)
        assistant_id = result["id"]
        save_state({"assistant_id": assistant_id, "base_url": base_url})
        print(f"Created assistant: {assistant_id}")

    print(f"\nProxy URL:    {base_url}")
    print(f"Assistant ID: {assistant_id}")
    print(f"\nCall this assistant:")
    print(f"  python call.py")
    print(f"  python call.py --web   (browser-based call)")


if __name__ == "__main__":
    main()

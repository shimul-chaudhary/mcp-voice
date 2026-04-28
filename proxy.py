"""Proxy server that bridges Vapi function-tool webhooks to a local MCP server.

Vapi's phone/Twilio path has a bug where it calls MCP tools as a single bundled
tool instead of individual tool names. This proxy works around that by exposing
the MCP tools as standard Vapi function tools backed by a webhook, then
forwarding each tool call to the local MCP server.

Usage:
    python proxy.py              # runs on port 8001, connects to MCP on 8000
    python proxy.py --port 8001  # explicit port
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx

MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp")


class McpSession:
    """Manages a persistent MCP session for forwarding tool calls."""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url
        self.session_id: str | None = None
        self.tools: list[dict] = []
        self._lock = threading.Lock()

    def initialize(self) -> None:
        with self._lock:
            resp = httpx.post(
                self.mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "mcp-voice-proxy", "version": "1.0.0"},
                    },
                },
                headers={"Accept": "application/json, text/event-stream"},
                timeout=30,
            )
            resp.raise_for_status()
            self.session_id = resp.headers.get("mcp-session-id")

            # Send initialized notification
            httpx.post(
                self.mcp_url,
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Mcp-Session-Id": self.session_id or "",
                },
                timeout=10,
            )

            # Fetch tools list
            resp2 = httpx.post(
                self.mcp_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Mcp-Session-Id": self.session_id or "",
                },
                timeout=30,
            )
            resp2.raise_for_status()
            tools_data = _parse_sse_response(resp2.text)
            self.tools = tools_data.get("result", {}).get("tools", [])
            print(f"MCP session {self.session_id}: {len(self.tools)} tools loaded")

    def call_tool(self, name: str, arguments: dict) -> dict:
        if not self.session_id:
            self.initialize()

        resp = httpx.post(
            self.mcp_url,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
            headers={
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": self.session_id or "",
            },
            timeout=60,
        )
        resp.raise_for_status()
        return _parse_sse_response(resp.text)

    def ensure_ready(self) -> None:
        if not self.session_id:
            self.initialize()


def _parse_sse_response(text: str) -> dict:
    """Parse SSE-formatted MCP response to extract JSON-RPC result."""
    for line in text.split("\n"):
        if line.startswith("data: "):
            return json.loads(line[6:])
    # Try parsing as plain JSON
    return json.loads(text)


def _sanitize_schema(schema: dict) -> dict:
    """Make MCP tool schemas compatible with Vapi's stricter JSON Schema validation.

    Vapi rejects anyOf/oneOf with null types, $defs, and other advanced features.
    Flatten them into simple type + description schemas.
    """
    if not isinstance(schema, dict):
        return schema

    # Remove $defs (Vapi doesn't support references)
    schema.pop("$defs", None)

    # Handle anyOf with null (optional field pattern)
    if "anyOf" in schema:
        non_null = [s for s in schema["anyOf"] if s.get("type") != "null"]
        if len(non_null) == 1:
            # Simple optional: anyOf[string, null] -> string
            merged = {**schema, **non_null[0]}
            merged.pop("anyOf", None)
            return _sanitize_schema(merged)
        elif non_null:
            # Multiple types: pick the first concrete one
            merged = {**schema, **non_null[0]}
            merged.pop("anyOf", None)
            return _sanitize_schema(merged)
        else:
            schema.pop("anyOf", None)
            schema["type"] = "string"

    # Handle $ref (inline it if possible, otherwise drop)
    if "$ref" in schema:
        schema.pop("$ref", None)
        if "type" not in schema:
            schema["type"] = "string"

    # Recursively sanitize properties
    if "properties" in schema:
        schema["properties"] = {
            k: _sanitize_schema(v) for k, v in schema["properties"].items()
        }

    # Sanitize array items
    if schema.get("type") == "array" and "items" in schema:
        schema["items"] = _sanitize_schema(schema["items"])

    return schema


# Global session
session = McpSession(MCP_URL)

# Tools to expose to Vapi (subset most useful for voice).
# These names must match what the MCP server returns from tools/list.
# Override via VOICE_TOOLS env var (comma-separated).
_default_voice_tools = [
    "search",
    "describe_app",
    "get_data_model",
    "get_fields",
    "search_knowledgebase_chunks",
    "list_sheets",
    "get_chart_data",
    "get_script",
]
_voice_tools_env = os.getenv("VOICE_TOOLS", "")
VOICE_TOOLS = [t.strip() for t in _voice_tools_env.split(",") if t.strip()] if _voice_tools_env else _default_voice_tools


def get_vapi_function_tools(base_url: str) -> list[dict]:
    """Convert MCP tools into Vapi function tool definitions."""
    session.ensure_ready()
    tools = []
    for mcp_tool in session.tools:
        name = mcp_tool.get("name", "")
        if not any(name == vt or name.endswith(f"_{vt}") for vt in VOICE_TOOLS):
            continue
        schema = _sanitize_schema(dict(mcp_tool.get("inputSchema", {})))
        # Build Vapi function tool
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


class ProxyHandler(BaseHTTPRequestHandler):
    """Handles Vapi webhook calls and forwards to MCP."""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if self.path == "/tool-call":
            self._handle_tool_call(body)
        elif self.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "not found"})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "tools": len(session.tools)})
        elif self.path == "/tools":
            session.ensure_ready()
            tool_names = [t["name"] for t in session.tools if any(t["name"] == vt or t["name"].endswith(f"_{vt}") for vt in VOICE_TOOLS)]
            self._respond(200, {"tools": tool_names})
        else:
            self._respond(404, {"error": "not found"})

    def _handle_tool_call(self, body: bytes):
        try:
            payload = json.loads(body)
            # Vapi sends: {"message": {"type": "tool-calls", "toolCallList": [...]}}
            message = payload.get("message", {})
            tool_calls = message.get("toolCallList", [])

            results = []
            for tc in tool_calls:
                tool_name = tc.get("function", {}).get("name", "")
                arguments = tc.get("function", {}).get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)

                print(f"  -> MCP tools/call: {tool_name}({json.dumps(arguments)[:100]})")

                try:
                    mcp_result = session.call_tool(tool_name, arguments)
                    content = mcp_result.get("result", {}).get("content", [])
                    # Extract text from MCP result
                    text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    result_text = "\n".join(text_parts) if text_parts else json.dumps(content)
                except Exception as e:
                    result_text = json.dumps({"error": str(e)})
                    print(f"  !! MCP error: {e}")
                    # Re-initialize session on error
                    session.session_id = None

                results.append({
                    "toolCallId": tc.get("id", ""),
                    "result": result_text,
                })

            self._respond(200, {"results": results})

        except Exception as e:
            print(f"Error handling tool call: {e}")
            self._respond(500, {"error": str(e)})

    def _respond(self, status: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[proxy] {args[0]}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MCP-to-Vapi proxy")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    print(f"Initializing MCP session at {MCP_URL}...")
    try:
        session.initialize()
        matched = [t["name"] for t in session.tools if any(t["name"] == vt or t["name"].endswith(f"_{vt}") for vt in VOICE_TOOLS)]
        print(f"Available voice tools: {matched}")
    except Exception as e:
        print(f"Warning: Could not initialize MCP session: {e}")
        print("Will retry on first tool call.")

    server = HTTPServer(("0.0.0.0", args.port), ProxyHandler)
    print(f"Proxy server listening on http://0.0.0.0:{args.port}")
    print(f"  Tool webhook: http://0.0.0.0:{args.port}/tool-call")
    print(f"  Health check: http://0.0.0.0:{args.port}/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down proxy.")
        server.shutdown()


if __name__ == "__main__":
    main()

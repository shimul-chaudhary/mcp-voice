# Architecture

## Overview

MCP Voice connects spoken language to live APIs through a pipeline of four components:

```
Phone / Browser
  -> Vapi (STT + LLM + TTS)
    -> proxy.py (webhook bridge)
      -> MCP server (API gateway)
        -> Cloud APIs
```

Each component has a single job and communicates over HTTP.

## Components

### Vapi

Vapi handles the voice layer: speech-to-text, LLM reasoning (GPT-4o), and text-to-speech (ElevenLabs). It supports both browser-based calls via its dashboard and phone calls via Twilio.

When the LLM decides to call a tool, Vapi sends an HTTP POST to the tool's webhook URL with the function name and arguments.

### Proxy (proxy.py)

The proxy is a lightweight HTTP server (port 8001) that translates between Vapi's webhook format and the MCP protocol. It exists because of a Vapi bug: on the Twilio phone path, native MCP tools get bundled into a single call instead of being invoked individually.

The proxy:

1. Initializes an MCP session at startup (JSON-RPC `initialize` + `notifications/initialized`)
2. Fetches the tool list via `tools/list`
3. Exposes a `/tool-call` endpoint that receives Vapi webhook POSTs
4. Forwards each tool call to the MCP server via `tools/call`
5. Parses the SSE response and returns plain JSON to Vapi

### MCP Server

Any MCP-compatible server that supports the `streamable-http` transport. The server exposes tools via the standard MCP protocol (JSON-RPC 2.0 over HTTP with SSE responses).

### Cloud APIs

The MCP server translates tool calls into actual API requests against the cloud platform (search, app metadata, knowledge base queries, etc.).

## Session Management

The proxy maintains a single MCP session (stored in `McpSession`). The session ID from the `initialize` response is sent as the `Mcp-Session-Id` header on all subsequent requests. If a tool call fails, the session is reset and re-initialized on the next request.

## Schema Sanitization

Vapi has stricter JSON Schema requirements than the MCP spec allows. The `_sanitize_schema()` function handles:

- `anyOf` with null types (optional field pattern) -- flattened to a single type
- `$defs` and `$ref` -- removed since Vapi doesn't support schema references
- Nested properties -- recursively sanitized
- Array items -- sanitized for Vapi compatibility

## Port Layout

| Port | Service | Protocol |
|------|---------|----------|
| 8000 | MCP server | HTTP (JSON-RPC + SSE) |
| 8001 | Proxy | HTTP (Vapi webhooks) |
| 4040 | ngrok inspector | HTTP (local only) |

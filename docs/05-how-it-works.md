# How It Works

A walkthrough of what happens when you ask a question over the phone.

## Example: "What apps do I have?"

### 1. You speak into the phone

Vapi's Twilio integration receives the audio stream and runs speech-to-text, producing: `"What apps do I have?"`

### 2. The LLM decides to use a tool

GPT-4o receives the transcribed text along with the system prompt and available tool definitions. It decides to call the `search` tool with a query for apps.

Vapi sends an HTTP POST to the proxy's webhook URL:

```json
{
  "message": {
    "type": "tool-calls",
    "toolCallList": [
      {
        "id": "call_abc123",
        "function": {
          "name": "search",
          "arguments": {"query": "apps", "resourceType": "app"}
        }
      }
    ]
  }
}
```

### 3. The proxy forwards to MCP

The proxy extracts the tool name and arguments, then sends a JSON-RPC request to the MCP server:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {"query": "apps", "resourceType": "app"}
  }
}
```

The MCP server responds with an SSE stream containing the result.

### 4. The proxy returns results to Vapi

The proxy parses the SSE response, extracts the text content, and returns it as a Vapi-compatible JSON response:

```json
{
  "results": [
    {
      "toolCallId": "call_abc123",
      "result": "Found 12 apps: Sales Dashboard, HR Analytics, ..."
    }
  ]
}
```

### 5. The LLM generates a spoken response

GPT-4o takes the tool result and generates a natural language response: "You have 12 apps. Some of them are Sales Dashboard, HR Analytics..."

### 6. You hear the answer

ElevenLabs converts the text to speech and Vapi streams the audio back to your phone.

## Latency Breakdown

Typical round-trip for a single tool call:

| Step | Time |
|------|------|
| Speech-to-text | ~500ms |
| LLM reasoning | ~1-2s |
| Proxy + MCP tool call | ~1-3s |
| LLM response generation | ~1s |
| Text-to-speech | ~500ms |
| **Total** | **~4-7s** |

The main variable is the MCP tool call duration, which depends on the API being queried.

## Multi-tool Conversations

The LLM can chain multiple tool calls in a single conversation turn. For example:

> "Describe the Sales app and show me its data model"

1. LLM calls `describe_app` with the app ID
2. LLM calls `get_data_model` with the same app ID
3. LLM combines both results into a single spoken response

If the user asks about an app by name (not ID), the LLM first calls `search` to find the app, then uses the returned ID for subsequent calls.

## Screenshots

<!-- Add your screenshots here -->
<!-- ![Vapi Dashboard](screenshots/vapi-dashboard.png) -->
<!-- ![Call in Progress](screenshots/call-in-progress.png) -->
<!-- ![Terminal Output](screenshots/terminal-output.png) -->

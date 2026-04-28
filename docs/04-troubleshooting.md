# Troubleshooting

## Common Issues

### "No tools loaded from proxy"

**Symptom**: `setup_assistant.py` fails with "No tools loaded from proxy."

**Cause**: The MCP server isn't running or the proxy can't connect to it.

**Fix**:
1. Check that the MCP server is running: `curl http://localhost:8000/mcp -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'`
2. Check the proxy health: `curl http://localhost:8001/health`
3. Verify `MCP_URL` in your `.env` points to the correct endpoint

### Vapi calls the wrong tool name

**Symptom**: Phone calls invoke a bundled tool name (e.g., "mcpTools") instead of individual tools.

**Cause**: This is the known Vapi/Twilio bug that the proxy exists to work around. The assistant is likely configured with MCP-type tools instead of function-type tools.

**Fix**: Re-run `python setup_assistant.py` to reconfigure the assistant with function-type tools backed by the proxy webhook.

### ngrok tunnel not detected

**Symptom**: `setup_assistant.py` says "No ngrok detected - using http://localhost:8001"

**Fix**: 
1. Make sure ngrok is running: `ngrok http 8001`
2. Verify the ngrok API is accessible: `curl http://127.0.0.1:4040/api/tunnels`
3. Or pass the URL explicitly: `python setup_assistant.py --url https://your-ngrok-url.ngrok-free.dev`

### TTS mispronounces brand names

**Symptom**: Text-to-speech reads technical terms or brand names incorrectly.

**Fix**: Add pronunciation overrides to the system prompt in `setup_assistant.py`. The pattern is to instruct the LLM to write a phonetically correct spelling:

```
"ALWAYS write 'Click' instead of 'Qlik' in your responses"
```

This works because the TTS engine reads the LLM's written output, not the original term.

### Tool call times out

**Symptom**: Vapi says the tool didn't respond in time.

**Fix**:
1. Increase the timeout in `setup_assistant.py` (default is 30s per tool):
   ```python
   "server": {
       "url": f"{base_url}/tool-call",
       "timeoutSeconds": 60,  # increase this
   },
   ```
2. Check if the MCP server is slow to respond (network, cold start, etc.)
3. The proxy forwards with a 60-second timeout -- increase in `proxy.py` if needed

### MCP session expires

**Symptom**: Tool calls fail with connection errors after working initially.

**Cause**: The MCP session may have timed out or the server was restarted.

**Fix**: The proxy auto-recovers by resetting `session_id` on error and re-initializing on the next call. If issues persist, restart the proxy.

## Diagnostic Scripts

### check_kbs.py

Lists all knowledge bases on the tenant and tests search on each:

```bash
TENANT_URL=https://your-tenant.example.com API_KEY=your_key python check_kbs.py
```

### test_invoke.py

Tests the assistant invoke endpoint (thread creation + invoke):

```bash
# Reads from .env
python test_invoke.py
```

Requires `ASSISTANT_ID` set in `.env`.

### test_kbs.py

Tests KB search across multiple knowledge bases:

```bash
# Reads from .env, requires TEST_KB_IDS
python test_kbs.py
```

## Logs

- **Proxy**: Prints to stdout. Each tool call is logged with name and truncated arguments.
- **MCP server**: Check its own logs (varies by server).
- **Vapi**: View call logs at [dashboard.vapi.ai](https://dashboard.vapi.ai/) under the assistant's call history.

# Customization

## Changing the Voice Tools

The proxy exposes a subset of MCP tools to Vapi. You can control which tools are available in two ways:

### Via environment variable

Set `VOICE_TOOLS` in your `.env` as a comma-separated list of tool name suffixes:

```
VOICE_TOOLS=search,describe_app,get_data_model,get_fields
```

The proxy matches each MCP tool name against these suffixes, so `search` matches `qlik_search`, `my_search`, etc.

### Via code

Edit the `_default_voice_tools` list in `proxy.py`:

```python
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
```

After changing tools, re-run `setup_assistant.py` to update the Vapi assistant.

## Changing the Voice

Edit `setup_assistant.py` and modify the `voice` section in `build_assistant_payload()`:

```python
"voice": {
    "provider": "11labs",
    "voiceId": "21m00Tcm4TlvDq8ikWAM",  # Rachel (default)
},
```

Browse voices at [ElevenLabs](https://elevenlabs.io/voice-library) and use any voice ID.

Other supported providers: `azure`, `playht`, `deepgram`, `rime`.

## Changing the LLM

Edit the `model` section in `build_assistant_payload()`:

```python
"model": {
    "provider": "openai",
    "model": "gpt-4o",
    ...
},
```

Vapi supports: `openai` (gpt-4o, gpt-4-turbo), `anthropic` (claude-3-opus, claude-3-sonnet), `together`, `groq`, and others.

## Customizing the System Prompt

The system prompt is built dynamically in `build_assistant_payload()`. It includes:

1. A persona description
2. Pronunciation rules (for TTS clarity)
3. Tool selection rules (generated from the available tools)
4. Response style guidelines

Modify the `content` string to change behavior. For voice, keep instructions concise -- the LLM needs to respond quickly.

## Adding a Knowledge Base

To enable documentation search:

1. Set `KNOWLEDGEBASE_ID` in your `.env` to your KB's ID
2. Include `search_knowledgebase_chunks` in your voice tools
3. Re-run `setup_assistant.py`

The system prompt automatically includes a tool rule for KB search when the tool is available.

## Changing the Proxy Port

```bash
python proxy.py --port 9001
```

Update your ngrok command accordingly: `ngrok http 9001`

## Using a Different MCP Server

Set these in your `.env`:

```
MCP_SERVER_DIR=/path/to/your/mcp-server
MCP_MODULE=your_module_name
```

The proxy connects to `http://localhost:8000/mcp` by default. Override with:

```
MCP_URL=http://localhost:9000/mcp
```

Any MCP server supporting `streamable-http` transport will work.

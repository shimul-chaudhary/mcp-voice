# MCP Voice

Voice interface for cloud analytics using [Vapi.ai](https://vapi.ai) and an MCP server.

Call a phone number or use the Vapi web dashboard to talk to your cloud tenant -- ask about apps, data models, help documentation, and more.

## Architecture

```
You speak
  -> Vapi (speech-to-text + LLM)
    -> function-tool webhook
      -> proxy.py (port 8001, exposed via ngrok)
        -> MCP tools/call
          -> MCP server (port 8000)
            -> Cloud APIs
          <- tool result
        <- JSON response
      <- webhook response
    <- LLM generates spoken response
  -> Vapi (text-to-speech)
You hear the answer
```

A lightweight proxy (`proxy.py`) sits between Vapi and the MCP server. The proxy
receives Vapi function-tool webhook calls and translates them into MCP `tools/call`
requests. This is needed because Vapi's native MCP tool type has a bug on the
Twilio phone path where it bundles all tools into a single call instead of invoking
them individually.

The proxy auto-discovers all available tools from the MCP server at startup and
exposes a configurable subset as Vapi function tools.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (for running the MCP server)
- [ngrok](https://ngrok.com/) account and CLI installed
- [Vapi](https://vapi.ai) account and API key
- Cloud tenant API key

## Setup

### 1. Configure environment

```bash
cp .env.template .env
# Edit .env with your credentials
```

### 2. Install dependencies

```bash
cd mcp-voice
uv sync

# Also ensure MCP server deps are installed
cd ../mcp-server
uv sync
```

### 3. Start MCP server + proxy

Terminal 1:
```bash
./start.sh
```

This starts the MCP server on port 8000 and the proxy on port 8001.

### 4. Expose via ngrok

Terminal 2:
```bash
ngrok http 8001
```

### 5. Create/update the Vapi assistant

Terminal 3:
```bash
# Auto-detects ngrok URL
python setup_assistant.py
```

### 6. Make a call

```bash
# Opens Vapi dashboard - click "Talk" to start a web call
python call.py --web
```

Or call the Twilio phone number linked to the assistant in the Vapi dashboard.

## Available voice commands (examples)

- "What apps do I have?"
- "How do I create a master measure?"
- "Describe the Sales app"
- "What's the data model in my HR app?"
- "Search for datasets about revenue"
- "What fields are in the Sales app?"

## Files

| File | Purpose |
|------|---------|
| `proxy.py` | Bridges Vapi function-tool webhooks to MCP `tools/call` |
| `setup_assistant.py` | Creates/updates the Vapi assistant with function tools |
| `start.sh` | Starts both MCP server (port 8000) and proxy (port 8001) |
| `start_mcp.sh` | Starts only the MCP server in streamable-http mode |
| `call.py` | Opens the Vapi dashboard to start a web call |
| `check_kbs.py` | Diagnostic: checks KB indexing status on the tenant |
| `test_invoke.py` | Diagnostic: tests the assistants invoke endpoint |
| `test_kbs.py` | Diagnostic: tests KB search across multiple KBs |
| `.env.template` | Environment variable template |

## Customizing tools

Edit the `VOICE_TOOLS` environment variable or the default list in `proxy.py`
to control which MCP tools are exposed to the voice assistant. The tool names
must match what the MCP server returns from `tools/list`.

You can also set `VOICE_TOOLS` in your `.env` as a comma-separated list:
```
VOICE_TOOLS=search,describe_app,get_data_model,get_fields,search_knowledgebase_chunks
```

To change which tools the MCP server loads, edit `start.sh` / `start_mcp.sh`
and change `--tools all` to specific tool sets.

## Documentation

| Doc | Topic |
|-----|-------|
| [Architecture](docs/01-architecture.md) | Component diagram, session management, schema handling |
| [Getting Started](docs/02-getting-started.md) | Step-by-step setup guide |
| [Customization](docs/03-customization.md) | Changing tools, voice, LLM, system prompt |
| [Troubleshooting](docs/04-troubleshooting.md) | Common issues and diagnostic scripts |
| [How It Works](docs/05-how-it-works.md) | End-to-end walkthrough of a voice query |

## Demo: voice Q&A over project docs

The voice assistant can answer questions about this project itself. Point [knowledgebase-mcp](https://github.com/shimul-chaudhary/knowledgebase-mcp) at the `docs/` folder and the agent uses semantic search to answer questions about architecture, setup, customization, troubleshooting, and internals — all via voice.

**Asking about voice/LLM customization and schema sanitization:**

![Customization and schema sanitization queries](docs/screenshots/Screenshot%202026-04-27%20at%208.16.01%20PM.png)

**Listing all indexed documents:**

![List documents query](docs/screenshots/Screenshot%202026-04-27%20at%208.16.21%20PM.png)

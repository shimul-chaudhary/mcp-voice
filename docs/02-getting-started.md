# Getting Started

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Python 3.12+ | Runtime | [python.org](https://www.python.org/) |
| uv | Package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| ngrok | Public tunnel | [ngrok.com](https://ngrok.com/) |
| Vapi account | Voice platform | [vapi.ai](https://vapi.ai/) |
| Cloud API key | Tenant access | Generate from your tenant settings |

## Step-by-step Setup

### 1. Clone and install

```bash
git clone git@github.com:shimul-chaudhary/mcp-voice.git
cd mcp-voice
uv sync
```

### 2. Install the MCP server

Clone and install your MCP server in a sibling directory:

```bash
cd ..
git clone <your-mcp-server-repo> mcp-server
cd mcp-server
uv sync
```

### 3. Configure environment

```bash
cd ../mcp-voice
cp .env.template .env
```

Edit `.env` with your credentials:

```
TENANT_URL=https://your-tenant.example.com
API_KEY=your_api_key_here
VAPI_API_KEY=your_vapi_key_here
MCP_MODULE=your_mcp_module
```

### 4. Start the services

Terminal 1 -- MCP server + proxy:
```bash
./start.sh
```

Terminal 2 -- ngrok tunnel:
```bash
ngrok http 8001
```

### 5. Create the Vapi assistant

Terminal 3:
```bash
python setup_assistant.py
```

This auto-detects your ngrok URL and creates (or updates) the assistant in Vapi.

### 6. Make a call

```bash
# Opens the Vapi dashboard -- click "Talk"
python call.py --web
```

Or call the Twilio phone number linked to your assistant in the Vapi dashboard.

## Verifying the Setup

Check that everything is running:

```bash
# MCP server health
curl http://localhost:8000/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Proxy health
curl http://localhost:8001/health

# List available voice tools
curl http://localhost:8001/tools
```

## Directory Structure

```
mcp-voice/
  .env.template    # Environment variable template
  .env             # Your local config (gitignored)
  proxy.py         # Vapi-to-MCP bridge
  setup_assistant.py  # Vapi assistant provisioning
  call.py          # Start a call
  start.sh         # Launch MCP server + proxy
  start_mcp.sh     # Launch MCP server only
  check_kbs.py     # Diagnostic: list knowledge bases
  test_invoke.py   # Diagnostic: test invoke endpoint
  test_kbs.py      # Diagnostic: test KB search
  docs/            # Documentation
```

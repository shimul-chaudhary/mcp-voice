#!/usr/bin/env bash
set -euo pipefail

# Start MCP server + proxy for Vapi function-tool webhooks.
# Run this in one terminal, then ngrok in another, then setup_assistant.py.
#
# Architecture:
#   Vapi (dashboard/phone) --> ngrok:8001 --> proxy.py --> MCP server:8000
#
# The proxy translates Vapi's function-tool webhook calls into MCP tools/call.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MCP_SERVER_DIR="${MCP_SERVER_DIR:-$(dirname "$SCRIPT_DIR")/mcp-server}"
MCP_MODULE="${MCP_MODULE:?Set MCP_MODULE in .env}"

if [[ ! -d "$MCP_SERVER_DIR" ]]; then
    echo "Error: MCP server directory not found at $MCP_SERVER_DIR"
    echo "Set MCP_SERVER_DIR to override."
    exit 1
fi

# Load .env from this project
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

if [[ -z "${TENANT_URL:-}" || -z "${API_KEY:-}" ]]; then
    echo "Error: TENANT_URL and API_KEY must be set in .env"
    exit 1
fi

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $MCP_PID 2>/dev/null || true
    kill $PROXY_PID 2>/dev/null || true
    wait 2>/dev/null
}
trap cleanup EXIT INT TERM

# Start MCP server in background
echo "Starting MCP server on port 8000..."
cd "$MCP_SERVER_DIR"
uv run -m "$MCP_MODULE" --transport streamable-http --tools all &
MCP_PID=$!
cd "$SCRIPT_DIR"

# Wait for MCP to be ready
echo "Waiting for MCP server..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null -w "" http://localhost:8000/mcp -X POST \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}' 2>/dev/null; then
        echo "MCP server ready."
        break
    fi
    sleep 1
done

# Start proxy
echo "Starting proxy on port 8001..."
python3 "$SCRIPT_DIR/proxy.py" --port 8001 &
PROXY_PID=$!

# Wait for proxy to be ready
sleep 2
if curl -s -o /dev/null http://localhost:8001/health 2>/dev/null; then
    echo "Proxy ready."
else
    echo "Warning: proxy may not be ready yet."
fi

echo ""
echo "Both services running:"
echo "  MCP server: http://localhost:8000/mcp"
echo "  Proxy:      http://localhost:8001"
echo ""
echo "Expose with: ngrok http 8001"
echo "Then run:    python3 setup_assistant.py"

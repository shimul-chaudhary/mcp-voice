#!/usr/bin/env bash
set -euo pipefail

# Start MCP server in streamable-http mode.
# Run this in one terminal, then ngrok in another, then setup_assistant.py.

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

echo "Starting MCP server..."
echo "  Transport: streamable-http"
echo "  Tenant:    $TENANT_URL"
echo "  Tools:     all"
echo ""
echo "MCP endpoint will be at: http://localhost:8000/mcp"
echo "Expose with: ngrok http 8000"
echo ""

cd "$MCP_SERVER_DIR"
exec uv run -m "$MCP_MODULE" --transport streamable-http --tools all

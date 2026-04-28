"""Start a voice call with the MCP voice assistant.

Usage:
    python call.py          # phone call (requires phone number config)
    python call.py --web    # open Vapi web call in browser
"""

import argparse
import json
import os
import sys
import webbrowser

import httpx
from dotenv import load_dotenv

VAPI_BASE = "https://api.vapi.ai"
STATE_FILE = ".vapi_state.json"


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def start_web_call(api_key: str, assistant_id: str) -> None:
    """Open the Vapi web call interface."""
    url = f"https://dashboard.vapi.ai/assistants/{assistant_id}"
    print(f"Opening Vapi dashboard for assistant {assistant_id}...")
    print(f"Click 'Talk' in the dashboard to start a web call.")
    print(f"\nDashboard URL: {url}")
    webbrowser.open(url)


def start_phone_call(api_key: str, assistant_id: str, phone_number: str) -> None:
    """Create an outbound phone call via Vapi API."""
    payload = {
        "assistantId": assistant_id,
        "customer": {"number": phone_number},
    }
    resp = httpx.post(
        f"{VAPI_BASE}/call/phone",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"Call initiated: {result.get('id', 'unknown')}")
    print(f"Status: {result.get('status', 'unknown')}")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Call the MCP voice assistant")
    parser.add_argument("--web", action="store_true", help="Open web call in browser")
    parser.add_argument("--phone", help="Phone number to call (E.164 format: +1234567890)")
    args = parser.parse_args()

    api_key = os.getenv("VAPI_API_KEY")
    if not api_key:
        print("Error: VAPI_API_KEY not set in .env")
        sys.exit(1)

    state = load_state()
    assistant_id = state.get("assistant_id")
    if not assistant_id:
        print("Error: No assistant configured. Run setup_assistant.py first.")
        sys.exit(1)

    if args.web or not args.phone:
        start_web_call(api_key, assistant_id)
    else:
        start_phone_call(api_key, assistant_id, args.phone)


if __name__ == "__main__":
    main()

"""Launch the app pre-configured for the live demo.

Configures Ollama on localhost as the LLM provider and starts the server.
Access remotely via Tailscale Funnel (URL configured in scripts/funnel_config.json).

Usage: python scripts/demo_run.py [--port PORT]
"""
import json, sys, os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import init_db, get_connection
from db.repository import SettingsRepository

CONFIG_PATH = Path(__file__).parent / "funnel_config.json"

def load_funnel_url():
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text())
        return config.get("funnel_url", "")
    return ""

def main():
    port = 8501
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])

    funnel_url = load_funnel_url()

    # Pre-configure settings for local Ollama
    init_db()
    conn = get_connection()
    repo = SettingsRepository()
    repo.set(conn, "api_url", "http://localhost:11434")
    repo.set(conn, "default_model", "qwen2.5:7b-instruct-q4_K_M")
    repo.set(conn, "openai_api_key", "")
    conn.close()

    print(f"Demo configured:")
    print(f"  LLM:    Ollama @ http://localhost:11434")
    print(f"  Model:  qwen2.5:7b-instruct-q4_K_M")
    print(f"  Port:   {port}")
    if funnel_url:
        print(f"  Funnel: {funnel_url}")
        print(f"")
        print(f"  Remote access: open {funnel_url} in browser")
    else:
        print(f"")
        print(f"  No Funnel URL configured. Run: python scripts/set_funnel_url.py <URL>")
    print(f"  Starting server...")

    from frontend_web.server import start_server
    start_server(port=port)

if __name__ == "__main__":
    main()

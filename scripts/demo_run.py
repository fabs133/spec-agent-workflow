"""Launch the app pre-configured for the live demo.

Configures Ollama on localhost as the LLM provider and starts the server.
Access remotely via Tailscale Funnel: https://desktop-e9k819f.tail00fec6.ts.net

Usage: python scripts/demo_run.py [--port PORT]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import init_db, get_connection
from db.repository import SettingsRepository

FUNNEL_URL = "https://desktop-e9k819f.tail00fec6.ts.net"

def main():
    port = 8501
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])

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
    print(f"  Funnel: {FUNNEL_URL}")
    print(f"")
    print(f"  Remote access: open {FUNNEL_URL} in browser")
    print(f"  Starting server...")

    from frontend_web.server import start_server
    start_server(port=port)

if __name__ == "__main__":
    main()

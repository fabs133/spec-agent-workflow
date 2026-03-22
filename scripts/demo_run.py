"""Launch the app pre-configured for the live demo.

Usage: python scripts/demo_run.py [--api-url URL] [--model MODEL] [--port PORT]

Defaults to Tailscale Funnel URL if no --api-url is given.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import init_db, get_connection
from db.repository import SettingsRepository

DEFAULT_URL = "https://desktop-e9k819f.tail00fec6.ts.net"

def main():
    api_url = DEFAULT_URL
    model = "qwen2.5:7b-instruct-q4_K_M"
    port = 8501

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--api-url" and i + 1 < len(args):
            api_url = args[i + 1]
        elif arg == "--model" and i + 1 < len(args):
            model = args[i + 1]
        elif arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])

    # Pre-configure settings in DB
    init_db()
    conn = get_connection()
    repo = SettingsRepository()
    repo.set(conn, "api_url", api_url)
    repo.set(conn, "default_model", model)
    repo.set(conn, "openai_api_key", "")  # Not needed for local
    conn.close()

    print(f"Demo configured:")
    print(f"  API URL: {api_url}")
    print(f"  Model:   {model}")
    print(f"  Port:    {port}")
    print(f"  Starting server...")

    # Launch normally
    import webbrowser
    webbrowser.open(f"http://localhost:{port}")
    from frontend_web.server import start_server
    start_server(port=port)

if __name__ == "__main__":
    main()

"""Launch the Spec-Agent Workflow System.

Usage: python run.py [--port PORT]
Opens the browser automatically.
"""

import sys
import webbrowser
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend_web.server import start_server


def main():
    port = 8501
    if "--port" in sys.argv:
        try:
            port = int(sys.argv[sys.argv.index("--port") + 1])
        except (IndexError, ValueError):
            print("Usage: python run.py [--port PORT]")
            sys.exit(1)

    webbrowser.open(f"http://localhost:{port}")
    start_server(port=port)


if __name__ == "__main__":
    main()

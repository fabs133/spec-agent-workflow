"""Set or update the Tailscale Funnel URL used by demo scripts.

Usage: python scripts/set_funnel_url.py <URL>
Example: python scripts/set_funnel_url.py https://my-machine.tail12345.ts.net
"""
import json, sys
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "funnel_config.json"

def main():
    if len(sys.argv) < 2:
        # Show current config
        if CONFIG_PATH.exists():
            config = json.loads(CONFIG_PATH.read_text())
            print(f"Current Funnel URL: {config.get('funnel_url', '(not set)')}")
        else:
            print("No funnel_config.json found.")
        print(f"\nUsage: python {sys.argv[0]} <URL>")
        sys.exit(0)

    url = sys.argv[1].rstrip("/")
    if not url.startswith("https://"):
        print(f"ERROR: URL must start with https:// (got: {url})")
        sys.exit(1)

    config = {"funnel_url": url}
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Funnel URL set: {url}")
    print(f"Saved to: {CONFIG_PATH}")

if __name__ == "__main__":
    main()

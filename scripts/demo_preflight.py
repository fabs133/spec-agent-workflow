"""Pre-flight check for live demo.

Run this before the presentation to verify all systems are operational.
Usage: python scripts/demo_preflight.py [--api-url URL] [--model MODEL]
"""
import sys, json, time, urllib.request, urllib.error, os

DEFAULT_URL = "https://desktop-e9k819f.tail00fec6.ts.net"
DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"

def check(name, fn):
    """Run a check function, print result."""
    try:
        result = fn()
        print(f"  ✓ {name}: {result}")
        return True
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        return False

def main():
    api_url = sys.argv[sys.argv.index("--api-url") + 1] if "--api-url" in sys.argv else DEFAULT_URL
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else DEFAULT_MODEL

    if not api_url:
        print("ERROR: No API URL specified. Use --api-url <url>")
        print("Example: python scripts/demo_preflight.py --api-url https://your-domain.com")
        sys.exit(1)

    base = api_url.rstrip("/")
    print(f"\n{'='*60}")
    print(f"Demo Pre-flight Check")
    print(f"{'='*60}")
    print(f"API URL: {base}")
    print(f"Model:   {model}")
    print(f"{'='*60}\n")

    results = []

    # 1. Python version
    print("[1/6] Python version")
    results.append(check("Python", lambda: f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"))

    # 2. Project imports
    print("[2/6] Project imports")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    def check_imports():
        from core.manifest import Manifest
        from core.orchestrator import Orchestrator
        from db.connection import init_db
        return "All core modules OK"
    results.append(check("Imports", check_imports))

    # 3. Remote API reachable
    print("[3/6] Remote API reachable")
    def check_api():
        # Try Ollama-style endpoint first
        try:
            req = urllib.request.Request(f"{base}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                return f"Reachable, {len(models)} models available"
        except Exception:
            pass
        # Try OpenAI-style endpoint
        req = urllib.request.Request(f"{base}/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return f"Reachable (OpenAI-compatible)"
    results.append(check("API endpoint", check_api))

    # 4. Model available
    print("[4/6] Model available")
    def check_model():
        try:
            req = urllib.request.Request(f"{base}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                if model in models or any(model in m for m in models):
                    return f"'{model}' found"
                return f"WARNING: '{model}' not found in {models}"
        except Exception:
            return "Could not list models (may still work)"
    results.append(check("Model", check_model))

    # 5. Test inference (small request)
    print("[5/6] Test inference")
    def check_inference():
        url = f"{base}/v1/chat/completions"
        payload = json.dumps({
            "model": model,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": "Reply with only the word 'OK'."}],
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        start = time.time()
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
        duration = time.time() - start
        content = body["choices"][0]["message"]["content"].strip()
        tokens = body.get("usage", {}).get("total_tokens", "?")
        return f"'{content}' in {duration:.1f}s ({tokens} tokens)"
    results.append(check("Inference", check_inference))

    # 6. Database writable
    print("[6/6] Database")
    def check_db():
        from db.connection import init_db, get_connection
        init_db()
        conn = get_connection()
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        return f"{len(tables)} tables"
    results.append(check("Database", check_db))

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    if passed == total:
        print(f"ALL CHECKS PASSED ({passed}/{total}) — Ready for demo!")
    else:
        print(f"WARNING: {total - passed} check(s) failed ({passed}/{total})")
        print("Fix the issues above before starting the presentation.")
    print(f"{'='*60}\n")
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()

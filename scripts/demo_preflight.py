"""Pre-flight check for live demo.

Run this ON THE HOME PC before the presentation.
Verifies: Ollama, Web App, Tailscale Funnel, Database.

Usage: python scripts/demo_preflight.py [--port PORT]
"""
import sys, json, time, urllib.request, urllib.error, os

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"
FUNNEL_URL = "https://desktop-e9k819f.tail00fec6.ts.net"
DEFAULT_PORT = 8501

def check(name, fn):
    try:
        result = fn()
        print(f"  ✓ {name}: {result}")
        return True
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        return False

def main():
    port = DEFAULT_PORT
    if "--port" in sys.argv:
        try:
            port = int(sys.argv[sys.argv.index("--port") + 1])
        except (IndexError, ValueError):
            pass

    app_url = f"http://localhost:{port}"

    print(f"\n{'='*60}")
    print(f"Demo Pre-flight Check (Home PC)")
    print(f"{'='*60}")
    print(f"Ollama:  {OLLAMA_URL}")
    print(f"Web App: {app_url}")
    print(f"Funnel:  {FUNNEL_URL}")
    print(f"Model:   {DEFAULT_MODEL}")
    print(f"{'='*60}\n")

    results = []

    # 1. Python version
    print("[1/8] Python version")
    results.append(check("Python", lambda: f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"))

    # 2. Project imports
    print("[2/8] Project imports")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    def check_imports():
        from core.manifest import Manifest
        from core.orchestrator import Orchestrator
        from db.connection import init_db
        return "All core modules OK"
    results.append(check("Imports", check_imports))

    # 3. Ollama reachable
    print("[3/8] Ollama reachable")
    def check_ollama():
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            return f"Running, {len(models)} models"
    results.append(check("Ollama", check_ollama))

    # 4. Model available
    print("[4/8] Model available")
    def check_model():
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            if DEFAULT_MODEL in models or any(DEFAULT_MODEL in m for m in models):
                return f"'{DEFAULT_MODEL}' found"
            return f"WARNING: '{DEFAULT_MODEL}' not in {models}"
    results.append(check("Model", check_model))

    # 5. Test inference
    print("[5/8] Test inference")
    def check_inference():
        payload = json.dumps({
            "model": DEFAULT_MODEL,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": "Reply with only the word 'OK'."}],
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.time()
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
        duration = time.time() - start
        content = body["choices"][0]["message"]["content"].strip()
        return f"'{content}' in {duration:.1f}s"
    results.append(check("Inference", check_inference))

    # 6. Database
    print("[6/8] Database")
    def check_db():
        from db.connection import init_db, get_connection
        init_db()
        conn = get_connection()
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        return f"{len(tables)} tables"
    results.append(check("Database", check_db))

    # 7. Web app running locally
    print("[7/8] Web app (local)")
    def check_webapp():
        req = urllib.request.Request(f"{app_url}/api/stats", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return f"Running, {data.get('total_runs', '?')} runs"
    results.append(check("Web App", check_webapp))

    # 8. Funnel reachable (public URL)
    print("[8/8] Tailscale Funnel (public)")
    def check_funnel():
        req = urllib.request.Request(f"{FUNNEL_URL}/api/stats", method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return f"Reachable, {data.get('total_runs', '?')} runs"
    results.append(check("Funnel", check_funnel))

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    if passed == total:
        print(f"ALL CHECKS PASSED ({passed}/{total}) — Ready for demo!")
        print(f"Open on school laptop: {FUNNEL_URL}")
    else:
        print(f"WARNING: {total - passed} check(s) failed ({passed}/{total})")
    print(f"{'='*60}\n")
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()

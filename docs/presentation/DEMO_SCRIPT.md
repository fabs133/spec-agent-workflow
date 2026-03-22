# Live Demo Script

## Before the Presentation (15 min prior)

1. On YOUR machine (at home):
   - Verify environment variables are set (persistent, should survive reboot):
     ```
     OLLAMA_ORIGINS=*
     OLLAMA_HOST=0.0.0.0:11434
     ```
   - Start Ollama: `ollama serve`
   - Start Tailscale Funnel: `tailscale funnel --bg --https=443 http://localhost:11434`
   - Verify funnel status: `tailscale funnel status` → should show `(Funnel on)`
   - Warm the model into GPU VRAM:
     ```
     curl https://desktop-e9k819f.tail00fec6.ts.net/v1/chat/completions ^
       -H "Content-Type: application/json" ^
       -d "{\"model\":\"qwen2.5:7b-instruct-q4_K_M\",\"messages\":[{\"role\":\"user\",\"content\":\"Hi\"}]}"
     ```

2. On the SCHOOL laptop (via Handy-Hotspot if Schulnetz blocked):
   - Open PowerShell, navigate to project: `cd C:\Users\fbrmp\Projekte\agent-workflow`
   - Run pre-flight check:
     ```
     python scripts/demo_preflight.py
     ```
   - If all 6 checks pass → ready
   - Clean previous data:
     ```
     Remove-Item data\output\* -Recurse -Force -ErrorAction SilentlyContinue
     Remove-Item data\spec_agent.db -ErrorAction SilentlyContinue
     ```
   - Launch demo:
     ```
     python scripts/demo_run.py
     ```
   - Browser opens. Verify Settings page shows the Tailscale URL.

## During the Presentation (~5 min demo block)

### Beat 1: Show the Input (30 sec)
- Open `data/input/` and show the sample text files
- "Das sind unstrukturierte Projektnotizen — Meeting-Protokolle, Architekturentscheidungen."

### Beat 2: Start the Workflow (30 sec)
- Navigate to **Run Workflow**
- Click **Start Workflow**
- "Der Workflow startet jetzt. Drei Steps: Dateien laden, LLM-Extraktion, Ergebnisse schreiben."
- Show the live progress updating

### Beat 3: Results (1 min)
- Navigate to **Dashboard** when complete
- Show the flow diagram with green checkmarks
- Click into **Run Detail** — show spec results (all passed), show agent traces (token count, duration)
- "Jeder Step wurde durch Pre- und Post-Specs validiert. Hier sehen Sie die Trace: X Tokens, Y Millisekunden."

### Beat 4: Extracted Items (30 sec)
- Navigate to **Items Browser**
- "Aus 2 Textdateien wurden N strukturierte Work Items extrahiert."
- Click one item — show title, type, tags, description

### Beat 5: The Infrastructure Point (1 min)
- Navigate to **Settings**
- Point at the API URL field: "Das Modell läuft nicht bei OpenAI, sondern auf meiner eigenen Infrastruktur — ein lokales Sprachmodell, gehostet über Tailscale Funnel auf meiner eigenen GPU."
- "Die Architektur ist vom Provider entkoppelt. OpenAI, lokales Modell, eigene Infrastruktur — der Workflow bleibt identisch."

### Beat 6: Architecture Page (30 sec)
- Show the **Architecture** page in the app itself
- "Die App erklärt ihre eigene Architektur."

## If the Tunnel Goes Down (Backup Plan)

1. DON'T PANIC. Say: "Die Netzwerkverbindung ist instabil — lassen Sie mich auf die Aufnahme wechseln."
2. If Handy-Hotspot available: reconnect, `python scripts/demo_preflight.py` to re-verify
3. If nothing works: Switch to the pre-recorded demo video
   - `docs/presentation/demo_recording.mp4`
   - "Hier ist eine Aufnahme eines erfolgreichen Durchlaufs."

## Home PC Startup Checklist (after reboot)

```powershell
# 1. Start Ollama (env vars are persistent)
ollama serve

# 2. In a second terminal — start Tailscale Funnel
tailscale funnel --bg --https=443 http://localhost:11434

# 3. Verify
tailscale funnel status
# Should show: (Funnel on)

# 4. Test from another device
# https://desktop-e9k819f.tail00fec6.ts.net/ → "Ollama is running"
```

## Timing Budget

| Section | Duration | Slides |
|---------|----------|--------|
| Projektidee + Problem | 2 min | 1–2 |
| Pipeline + Architektur | 3 min | 3–4 |
| Tech Stack | 1 min | 5 |
| Datenbank | 1.5 min | 6 |
| **LIVE DEMO** | **5 min** | 7 |
| Zahlen & Tests | 1 min | 8 |
| Fazit + Fragen | 1.5 min | 9 |
| **Total** | **~15 min** | 9 slides |

## Reminder: Record Backup Video

**Before presentation day**, record the full demo flow once:
- Windows: `Win+G` → Record, or OBS
- Save as `docs/presentation/demo_recording.mp4`
- This is insurance if the tunnel dies during the talk.

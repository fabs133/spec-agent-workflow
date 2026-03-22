# Live Demo Script

## Architecture

```
[School Laptop: Browser] --HTTPS--> [Tailscale Funnel :443] --> [Web App :8501] --> [Ollama :11434]
                                                                 ^--- all on Home PC ---^
```

The school laptop only needs a browser. Everything runs on the Home PC.

## First-Time Setup (once)

Set the Tailscale Funnel URL (run `tailscale funnel status` to find your URL):
```
python scripts/set_funnel_url.py https://YOUR-MACHINE.tailXXXXX.ts.net
```

This saves it to `scripts/funnel_config.json` (gitignored, never committed).

## Before the Presentation (15 min prior)

1. On the HOME PC:
   - Verify Ollama env vars are set (persistent, should survive reboot):
     ```
     OLLAMA_ORIGINS=*
     OLLAMA_HOST=0.0.0.0:11434
     ```

   - **Terminal 1** — Start Ollama:
     ```
     ollama serve
     ```

   - **Terminal 2** — Start Web App:
     ```
     cd C:\Users\fbrmp\Projekte\agent-workflow
     python scripts/demo_run.py
     ```
     Should print the Funnel URL from config.

   - **Terminal 3** — Start Tailscale Funnel (points to web app, NOT Ollama):
     ```
     tailscale funnel --bg --https=443 http://localhost:8501
     tailscale funnel status
     ```
     Should show: `(Funnel on)` proxying to `http://localhost:8501`

   - **Terminal 4** — Run pre-flight check:
     ```
     python scripts/demo_preflight.py
     ```
     Expected: `ALL CHECKS PASSED (8/8) — Ready for demo!`

2. On the SCHOOL laptop:
   - Connect to Handy-Hotspot (fallback if Schulnetz blocks `.ts.net` domains)
   - Open browser with the Funnel URL shown by `demo_run.py`
   - Verify: Web UI loads with sidebar (Dashboard, Run Workflow, etc.)

## If the Funnel URL Changes

```
python scripts/set_funnel_url.py https://NEW-URL.tailXXXXX.ts.net
```

Then restart `demo_run.py` and re-run `demo_preflight.py`.

## During the Presentation (~5 min demo block)

### Beat 1: Show the Input (30 sec)
- Navigate to **Run Workflow** page
- Show the input files listed
- "Das sind unstrukturierte Projektnotizen — Meeting-Protokolle, Architekturentscheidungen."

### Beat 2: Start the Workflow (30 sec)
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
- Point at the API URL field: "Das Modell läuft nicht bei OpenAI, sondern auf meiner eigenen Infrastruktur — ein lokales Sprachmodell auf meiner GPU zuhause, erreichbar über Tailscale Funnel."
- "Die Architektur ist vom Provider entkoppelt. OpenAI, lokales Modell, eigene Infrastruktur — der Workflow bleibt identisch."

### Beat 6: Architecture Page (30 sec)
- Show the **Architecture** page in the app itself
- "Die App erklärt ihre eigene Architektur."

## If the Network Goes Down (Backup Plan)

1. DON'T PANIC. Say: "Die Netzwerkverbindung ist instabil — lassen Sie mich auf die Aufnahme wechseln."
2. If Handy-Hotspot available: reconnect, refresh browser
3. If nothing works: Switch to the pre-recorded demo video
   - `docs/presentation/demo_recording.mp4`
   - "Hier ist eine Aufnahme eines erfolgreichen Durchlaufs."

## Home PC Startup Checklist (after reboot)

```powershell
# 1. Start Ollama (env vars are persistent)
ollama serve

# 2. Start Web App (in a second terminal)
cd C:\Users\fbrmp\Projekte\agent-workflow
python scripts/demo_run.py

# 3. Start Tailscale Funnel (in a third terminal)
tailscale funnel --bg --https=443 http://localhost:8501
tailscale funnel status

# 4. Run pre-flight check
python scripts/demo_preflight.py
# Expected: 8/8 checks pass

# 5. Open Funnel URL on school laptop browser
```

## Timing Budget

| Section | Duration | Slides |
|---------|----------|--------|
| Projektidee + Problem | 2 min | 1-2 |
| Pipeline + Architektur | 3 min | 3-4 |
| Tech Stack | 1 min | 5 |
| Datenbank | 1.5 min | 6 |
| **LIVE DEMO** | **5 min** | 7 |
| Zahlen & Tests | 1 min | 8 |
| Fazit + Fragen | 1.5 min | 9 |
| **Total** | **~15 min** | 9 slides |

## Reminder: Record Backup Video

**Before presentation day**, record the full demo flow once:
- Windows: `Win+G` -> Record, or OBS
- Save as `docs/presentation/demo_recording.mp4`
- This is insurance if the network dies during the talk.

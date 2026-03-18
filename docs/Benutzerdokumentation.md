# Benutzerdokumentation – Spec-Agent Workflow System

## 1. Systemvoraussetzungen

- **Python:** Version 3.10 oder höher
- **Betriebssystem:** Windows, macOS oder Linux
- **Internetzugang:** Erforderlich für OpenAI-API-Aufrufe
- **Keine zusätzlichen Pakete nötig** – das System verwendet ausschließlich die Python-Standardbibliothek

## 2. Installation

1. Repository klonen:
   ```
   git clone https://github.com/fabs133/spec-agent-workflow.git
   cd agent-workflow
   ```
2. Optional: `.env.example` nach `.env` kopieren und OpenAI-API-Key eintragen

Weitere Installationsschritte sind nicht erforderlich.

## 3. Anwendung starten

```
python run.py
```

Der Browser öffnet sich automatisch unter `http://localhost:8501`.

**Alternativer Port:**
```
python run.py --port 8502
```

## 4. Bedienung

### 4.1 API-Key konfigurieren

1. Navigieren Sie zu **Settings** in der Seitenleiste
2. Tragen Sie Ihren OpenAI-API-Key ein
3. Wählen Sie das gewünschte Modell (Standard: gpt-4o)
4. Passen Sie die Temperatur bei Bedarf an (Standard: 0.3)

### 4.2 Dateien vorbereiten

Legen Sie Ihre Textdateien im Ordner `data/input/` ab. Unterstützte Formate: `.txt` und `.md`.

### 4.3 Workflow ausführen

1. Navigieren Sie zu **Run Workflow** in der Seitenleiste
2. Klicken Sie auf **Start Workflow**
3. Der Fortschritt wird live angezeigt

Der Workflow durchläuft automatisch drei Schritte:

| Schritt | Agent | Beschreibung |
|---------|-------|-------------|
| Intake | IntakeAgent | Dateien aus `data/input/` laden und validieren |
| Extract | ExtractAgent | Strukturierte Items per LLM extrahieren |
| Write | WriteAgent | Ergebnisse in `data/output/` speichern |

Jeder Schritt wird vor und nach der Ausführung durch Spec-Funktionen validiert (Pre-Specs, Post-Specs, Invarianten).

### 4.4 Ergebnisse einsehen

- **Dashboard:** Übersicht mit Statistiken und letzten Durchläufen
- **Run History:** Chronologische Liste aller Workflow-Durchläufe mit Status
- **Run Detail:** Detailansicht eines Durchlaufs mit Steps, Traces, Spec-Ergebnissen und Context-Diffs
- **Items Browser:** Alle extrahierten Items filtern und durchsuchen

### 4.5 Ausgabedateien

Nach einem erfolgreichen Durchlauf finden Sie im Ordner `data/output/`:
- `extraction_results.json` – Zusammenfassung aller extrahierten Items
- Einzelne Markdown-Dateien pro extrahiertem Item

### 4.6 Lokales LLM verwenden (Ollama)

Das System unterstützt neben OpenAI auch lokale LLM-Backends, die eine OpenAI-kompatible API bereitstellen (z.B. Ollama). Damit läuft der gesamte Workflow offline — keine Daten verlassen den Rechner, keine API-Kosten.

> **Wichtiger Hinweis:** Lokale Sprachmodelle sind ressourcenintensiv. Ollama muss korrekt konfiguriert werden, bevor es auf einem normalen Laptop eingesetzt wird. Ohne Anpassung kann Ollama mit den Standardeinstellungen den gesamten Arbeitsspeicher belegen und das System zum Einfrieren bringen. Bitte lesen Sie die Abschnitte **Hardwareanforderungen** und **Konfiguration für Laptops** vollständig, bevor Sie Ollama starten.

#### Hardwareanforderungen

| | 7B-Modell (empfohlen) | 12B-Modell | Hinweis |
|---|---|---|---|
| **RAM** | mindestens 8 GB, empfohlen 16 GB | mindestens 16 GB | Das Modell wird komplett in den Arbeitsspeicher geladen |
| **Festplatte** | ~4 GB pro Modell | ~7 GB pro Modell | Einmaliger Download, gespeichert in `~/.ollama/` |
| **CPU** | 4+ Kerne (x86_64 oder ARM) | 6+ Kerne empfohlen | Läuft auf jeder modernen CPU, aber langsam |
| **GPU (optional)** | NVIDIA ab 6 GB VRAM | NVIDIA ab 8 GB VRAM | Beschleunigt um Faktor 5–10× |

**Realistische Zeiten nach Rechnertyp:**

| Rechnertyp | Dauer pro Datei (7B) | Erlebnis |
|---|---|---|
| Büro-Laptop (i5, 8 GB, keine GPU) | 60–180 Sekunden | Funktioniert, aber System wird träge. Lüfter laut. Andere Programme schließen. |
| Moderner Laptop (i7/Ryzen 7, 16 GB, keine GPU) | 30–60 Sekunden | Gut nutzbar |
| Desktop mit GPU (RTX 3060+, 16 GB) | 3–8 Sekunden | Vergleichbar mit OpenAI |
| Apple Silicon (M1/M2/M3, 16 GB) | 10–25 Sekunden | Gut nutzbar dank Metal-Beschleunigung |

#### Installation

1. Ollama von [ollama.com/download](https://ollama.com/download) herunterladen und installieren (Windows, macOS, Linux)
2. Modell herunterladen (einmalig, ~4 GB):
   ```
   ollama pull qwen2.5:7b-instruct-q4_K_M
   ```
3. Prüfen ob das Modell verfügbar ist:
   ```
   ollama list
   ```

Ausführliche Installationsanleitung: [github.com/ollama/ollama](https://github.com/ollama/ollama)

#### ⚠ Konfiguration für Laptops (wichtig vor dem ersten Start)

Ollama startet mit Standardeinstellungen, die für Server mit viel Arbeitsspeicher ausgelegt sind. Auf einem Laptop mit 8–16 GB RAM können diese Standardwerte dazu führen, dass das System einfriert oder extrem langsam wird.

**Das Problem:** Ollama versucht standardmäßig, bis zu 3 Modelle gleichzeitig geladen zu halten und 4 Anfragen parallel zu bearbeiten. Jede parallele Anfrage reserviert zusätzlichen Speicher (KV-Cache). Bei einem 7B-Modell, das ~5 GB RAM belegt, bleibt auf einem 8-GB-Laptop kaum Platz für das Betriebssystem.

**Die Lösung:** Setzen Sie folgende Umgebungsvariablen, bevor Sie Ollama starten:

**Windows (PowerShell — einmalig setzen):**
```powershell
# Nur 1 Modell gleichzeitig laden (Standard: 3)
[Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "1", "User")

# Nur 1 parallele Anfrage (Standard: 4) — spart erheblich RAM
[Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")

# Modell nach 5 Minuten Inaktivität entladen (Standard, aber explizit setzen)
[Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "5m", "User")
```
Danach PowerShell schließen und Ollama neu starten.

**macOS (Terminal):**
```bash
launchctl setenv OLLAMA_MAX_LOADED_MODELS 1
launchctl setenv OLLAMA_NUM_PARALLEL 1
launchctl setenv OLLAMA_KEEP_ALIVE 5m
```
Danach Ollama-App neu starten.

**Linux (systemd):**
```bash
sudo systemctl edit ollama.service
```
Folgendes eintragen:
```ini
[Service]
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_KEEP_ALIVE=5m"
```
Dann: `sudo systemctl daemon-reload && sudo systemctl restart ollama`

**Was die Einstellungen bewirken:**

| Variable | Standard | Empfehlung Laptop | Warum |
|---|---|---|---|
| `OLLAMA_MAX_LOADED_MODELS` | 3 | **1** | Verhindert, dass mehrere Modelle gleichzeitig den RAM belegen |
| `OLLAMA_NUM_PARALLEL` | 4 (bzw. 1) | **1** | Jede parallele Anfrage reserviert zusätzlichen KV-Cache-Speicher. Auf 8 GB RAM reicht der Platz nur für 1 gleichzeitige Anfrage |
| `OLLAMA_KEEP_ALIVE` | 5m | 5m | Modell wird nach 5 Minuten Inaktivität entladen und gibt den RAM frei. Auf sehr knappen Systemen ggf. auf `1m` setzen |

> **Tipp:** Schließen Sie vor dem Workflow-Start speicherintensive Programme (Browser mit vielen Tabs, IDEs, Docker). Ein 7B-Modell + Betriebssystem + Python-Workflow brauchen zusammen 7–8 GB RAM.

#### Einrichtung in der Anwendung

1. Ollama starten: `ollama serve` (läuft auf Port 11434)
2. In der Anwendung **Settings** öffnen
3. Im Feld **API URL** eintragen: `http://localhost:11434`
4. Das **Modell** auf den Ollama-Modellnamen ändern (z.B. `qwen2.5:7b-instruct-q4_K_M`)
5. Das Feld **API Key** kann leer bleiben
6. **Start Workflow** klicken

#### Empfohlene Modelle

| Modell | Download | RAM-Bedarf | Eignung |
|--------|----------|------------|---------|
| `qwen2.5:7b-instruct-q4_K_M` | ~4 GB | ~5 GB | **Empfohlen.** Beste Balance aus Qualität und Ressourcenverbrauch |
| `qwen2.5-coder:7b` | ~4 GB | ~5 GB | Gut für technische Texte und Code-Notizen |
| `mistral-nemo:12b-instruct` | ~7 GB | ~9 GB | Bessere Qualität, aber **nur mit 16+ GB RAM** |

#### Vergleich: OpenAI vs. lokal

| | OpenAI GPT-4o | Lokales 7B-Modell |
|---|---|---|
| **Geschwindigkeit** | 3–5 Sek. pro Datei | 30–180 Sek. pro Datei (CPU) |
| **Qualität** | Sehr hoch | Gut — explizite Aufgaben werden erkannt, implizite können fehlen |
| **Kosten** | ~0,01–0,03 € pro Durchlauf | Kostenlos |
| **Internet** | Erforderlich | Nicht nötig |
| **Datenschutz** | Daten gehen an OpenAI | Alles bleibt lokal |

#### Fehlerbehebung Ollama

| Problem | Ursache | Lösung |
|---------|---------|--------|
| „Network error: Connection refused" | Ollama läuft nicht | `ollama serve` in separatem Terminal starten |
| „model not found" | Modell nicht heruntergeladen | `ollama pull qwen2.5:7b-instruct-q4_K_M` ausführen |
| System friert ein / wird extrem langsam | Zu viel RAM-Verbrauch | Umgebungsvariablen setzen (siehe oben), andere Programme schließen |
| Sehr langsame Antworten (>3 Min.) | CPU-only, wenig RAM | Normales Verhalten. Geduld — der Workflow bricht nicht ab |
| Lüfter dreht auf Volllast | CPU unter Volllast | Erwartetes Verhalten während der Verarbeitung |
| Leere oder unbrauchbare Ergebnisse | Modell zu klein | Temperatur auf 0.1 senken, oder größeres Modell verwenden |
| „Out of memory" / Absturz | Nicht genug RAM | Auf 7B-Modell wechseln, `OLLAMA_NUM_PARALLEL=1` setzen, Programme schließen |

#### Weiterführende Ressourcen

- Ollama Dokumentation: [github.com/ollama/ollama/blob/main/docs](https://github.com/ollama/ollama/blob/main/docs)
- Modellbibliothek: [ollama.com/library](https://ollama.com/library)
- Umgebungsvariablen (vollständige Referenz): [github.com/ollama/ollama/blob/main/docs/faq.md](https://github.com/ollama/ollama/blob/main/docs/faq.md)
- VRAM-Rechner für GPU-Nutzer: [localllm.in/blog/ollama-vram-requirements-for-local-llms](https://localllm.in/blog/ollama-vram-requirements-for-local-llms)

## 5. Seiten im Überblick

| Seite | Beschreibung |
|-------|-------------|
| Dashboard | Startseite mit Statistiken und letzten Durchläufen |
| Run Workflow | Neuen Workflow-Durchlauf starten |
| Run History | Chronologische Liste aller Durchläufe |
| Run Detail | Detaillierte Ansicht eines einzelnen Durchlaufs |
| Items Browser | Extrahierte Items anzeigen und filtern |
| Settings | API-Key, Modell und Ordnerkonfiguration |
| Architecture | Technische Architekturübersicht |
| Manifest | Workflow-Definition (JSON) anzeigen |
| Diagrams | UML-Diagramme anzeigen |
| User Guide | Integrierte Hilfe |

## 6. Wartung

### 6.1 Datenbank zurücksetzen

Löschen Sie die SQLite-Datenbank, um alle gespeicherten Durchläufe zu entfernen:

```
del data\spec_agent.db        (Windows)
rm data/spec_agent.db          (macOS/Linux)
```

Die Datenbank wird beim nächsten Start automatisch neu erstellt.

### 6.2 Ausgabedateien bereinigen

```
del /Q data\output\*           (Windows)
rm -rf data/output/*           (macOS/Linux)
```

### 6.3 Tests ausführen

```
pip install pytest pytest-asyncio
pytest tests/ -v
```

### 6.4 Port ändern

```
python run.py --port 8502
```

## 7. Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| „Authentication failed (401)" | API-Key in Settings prüfen |
| „Rate limit exceeded (429)" | Kurz warten und erneut versuchen |
| „Network error" | Internetverbindung prüfen |
| „Request timed out" | Erneut versuchen; bei wiederholtem Auftreten Internetverbindung prüfen |
| Browser öffnet sich nicht | Manuell `http://localhost:8501` aufrufen |
| Port bereits belegt | Anderen Port wählen: `python run.py --port 8502` |
| Keine Dateien geladen | Prüfen, ob Dateien in `data/input/` liegen und `.txt` oder `.md` Endung haben |
| Workflow schlägt fehl | Run Detail öffnen → Spec Results und Error Messages prüfen |

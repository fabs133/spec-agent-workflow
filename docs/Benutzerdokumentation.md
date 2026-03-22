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

Das System unterstützt neben OpenAI auch lokale LLM-Backends, die eine OpenAI-kompatible API bereitstellen. Ollama ist eine leichtgewichtige Runtime für lokale Sprachmodelle, die auf Windows, macOS und Linux läuft. Damit kann der gesamte Workflow offline betrieben werden — keine Daten verlassen den Rechner, keine API-Kosten.

#### Hardwareanforderungen

| | 7B-Modell (empfohlen) | 12B-Modell | Hinweis |
|---|---|---|---|
| **RAM** | mindestens 8 GB, empfohlen 16 GB | mindestens 16 GB | Das Modell wird komplett in den Arbeitsspeicher geladen |
| **Festplatte** | ~4 GB pro Modell | ~7 GB pro Modell | Einmaliger Download, gespeichert in `~/.ollama/` |
| **CPU** | 4+ Kerne (x86_64 oder ARM) | 6+ Kerne empfohlen | Läuft auf jeder modernen CPU |
| **GPU (optional)** | NVIDIA ab 6 GB VRAM | NVIDIA ab 8 GB VRAM | Beschleunigt um Faktor 5–10× |

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

#### Einrichtung in der Anwendung

1. Ollama starten: `ollama serve` (läuft auf Port 11434)
2. In der Anwendung **Settings** öffnen
3. Im Feld **API URL** eintragen: `http://localhost:11434`
4. Das **Modell** auf den Ollama-Modellnamen ändern (z.B. `qwen2.5:7b-instruct-q4_K_M`)
5. Das Feld **API Key** kann leer bleiben
6. **Start Workflow** klicken

#### Remote / Self-Hosted Betrieb

Ollama kann auch auf einem separaten Rechner laufen (z.B. ein Desktop mit GPU oder ein Server) und über das Netzwerk angesprochen werden. Dafür wird in der Anwendung einfach die API URL auf die Netzwerkadresse des entfernten Rechners gesetzt (z.B. `http://192.168.1.50:11434` oder eine eigene Domain). Der Workflow bleibt identisch — lediglich die API URL ändert sich.

#### Empfohlene Modelle

| Modell | Download | RAM-Bedarf | Eignung |
|--------|----------|------------|---------|
| `qwen2.5:7b-instruct-q4_K_M` | ~4 GB | ~5 GB | **Empfohlen.** Beste Balance aus Qualität und Ressourcenverbrauch |
| `qwen2.5-coder:7b` | ~4 GB | ~5 GB | Gut für technische Texte und Code-Notizen |
| `mistral-nemo:12b-instruct` | ~7 GB | ~9 GB | Bessere Qualität, aber nur mit 16+ GB RAM |

#### Vergleich: OpenAI vs. lokal

| | OpenAI GPT-4o | Lokales 7B-Modell |
|---|---|---|
| **Geschwindigkeit** | 3–5 Sek. pro Datei | 30–180 Sek. (CPU), 3–8 Sek. (GPU) |
| **Qualität** | Sehr hoch | Gut — explizite Aufgaben werden erkannt, implizite können fehlen |
| **Kosten** | ~0,01–0,03 € pro Durchlauf | Kostenlos |
| **Internet** | Erforderlich | Nicht nötig |
| **Datenschutz** | Daten gehen an OpenAI | Alles bleibt lokal |

#### Fehlerbehebung Ollama

| Problem | Ursache | Lösung |
|---------|---------|--------|
| „Network error: Connection refused" | Ollama läuft nicht | `ollama serve` in separatem Terminal starten |
| „model not found" | Modell nicht heruntergeladen | `ollama pull qwen2.5:7b-instruct-q4_K_M` ausführen |
| Leere oder unbrauchbare Ergebnisse | Modell zu klein | Temperatur auf 0.1 senken, oder größeres Modell verwenden |

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

# Privatemode AI 2API & Automatisierter Konten-Manager

<p align="center">
  <b>Sprache / Language / 语言:</b>
  <b>Deutsch</b> |
  <a href="README_EN.md">English</a> |
  <a href="README_ZH.md">中文</a>
</p>

---

Ein leistungsstarkes und zuverlässiges **2API Gateway** sowie ein vollautomatischer Registrierungs- und Konten-Wiederherstellungsdienst für [Privatemode AI](https://portal.privatemode.ai/).

Dieses Projekt wandelt die offizielle SaaS License API Keys von Privatemode in eine standardisierte **OpenAI-kompatible REST API** (`/v1/chat/completions`, `/v1/models`, `/v1/embeddings` etc.) um. Durch die nahtlose Kopplung mit Microsoft Outlook IMAP und dem Turnstile Cloudflare Solver können neue Konten vollautomatisch registriert oder bereits registrierte Konten aus der Sperrliste mit einem Klick wiederhergestellt werden.

---

## 🌟 Hauptfunktionen

- **Standardisiertes OpenAI /v1 Protokoll**: Vollständig kompatibel mit NextChat, Chatbox, Cherry Studio, LobeChat, LangChain und weiteren Client-Tools.
- **Offizielle Modell-Matrix**:
  - `glm-5.3`, `glm-latest` (1M Kontext-Tokens, Chat)
  - `glm-5.3-flash`, `glm-flash-latest` (1M Kontext-Tokens, Multimodal Text + Bild)
  - `gpt-oss-120b` (128k Kontext-Tokens, Chat)
  - `deepseek-ocr-2` (Preview, OCR Bild- & Texterkennung)
  - `qwen3-embedding-4b` (32k Tokens, Embeddings)
  - `voxtral-mini-3b`, `whisper-large-v3` (Spracherkennung / Audio Transcriptions)
- **Automatische Kontenregistrierung**: Integrierter Turnstile-Solver (Port 5072) zur Umgehung von Cloudflare-Challenges und automatische IMAP-Codeabfrage über Outlook-Postfächer.
- **Intelligente Konten-Wiederherstellung (Account Recovery)**: Bereits registrierte Konten (`Email already registered in Privatemode`) werden nicht verworfen, sondern über Clerk Sign-In und IMAP-Verifizierungscodes automatisch wiederhergestellt und mit neuen License Keys ausgestattet.
- **Moderne Web-Verwaltungskonsole**: Übersichtliches Web-Dashboard im Mocha & Cream-Stil für Echtzeit-Metriken, Kontenstatus, manuelle Pflege, interaktiven Test-Playground und Log-Streaming.

---

## 🔗 Turnstile Solver Projekt & Bereitstellung

Für die automatische Lösung des Cloudflare Turnstile Captchas bei Registrierung und Wiederherstellung wird das folgende Open-Source-Projekt verwendet:

- **Repository**: [https://github.com/D3-vin/Turnstile-Solver-NEW](https://github.com/D3-vin/Turnstile-Solver-NEW)

### Bereitstellung des Turnstile Solvers:

#### 1. Install

```bash
git clone https://github.com/D3-vin/Turnstile-Solver-NEW.git
cd Turnstile-Solver-NEW
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

#### 2. Install a browser

```bash
python -m patchright install chromium   # or: install msedge / use system Chrome
python -m camoufox fetch                # if you want Camoufox
```

#### 3. Run

```bash
python api.py
```

Server starts on `http://0.0.0.0:5072`.

---

## 📖 Anleitung & Konfiguration

### 1. Outlook-E-Mail-Kontendatei platzieren

Das System benötigt eine Liste von Outlook-Konten für den E-Mail-Empfang und die Codeextraktion:

- **Speicherort**: Platzieren Sie Ihre Kontendatei direkt im **Projekt-Stammverzeichnis**:
  ```text
  Privatemodeai2api/
  ├── outlook_accounts.txt
  ```
- **Format**: Jede Zeile enthält die Kontodaten im Format:
  ```text
  email----password----client_id----refresh_token
  ```
  *(Alternativ wird auch das Standardformat `email----password` unterstützt, sofern IMAP-Passwörter aktiviert sind).*

### 2. Umgebungsvariablen konfigurieren (`.env`)

Kopieren Sie die Beispielkonfigurationsdatei:
```bash
cp .env.example .env
```

Wichtige Parameter in der `.env`:
```ini
# Host und Port des Gateways
HOST=0.0.0.0
PORT=8000

# Optionaler Sicherheitsschlüssel für den Zugriff auf /v1 Endpunkte (im Dashboard eintragen)
API_KEY=change-me

# Pfad zur Outlook-Kontendatei (im Projekt-Root)
OUTLOOK_ACCOUNT_FILE=outlook_accounts.txt

# Turnstile Solver Adresse
TURNSTILE_SOLVER_URL=http://127.0.0.1:5072
TURNSTILE_SITEKEY=0x4AAAAAAAWXJGBD7bONzLBd
TURNSTILE_SOLVER_PATH=C:/Users/Administrator/PycharmProjects/Turnstile-Solver-NEW


# Konten-Pool Datenspeicherung
ACCOUNT_FILE=data/accounts.json
OUTLOOK_BLACKLIST_FILE=data/outlook_email_blacklist.json
```

---

## 🚀 Starten des Dienstes

### 1. Python-Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### 2. Privatemode 2API Gateway starten
Führen Sie das Startskript im Projektverzeichnis aus:
```bash
python run.py
```

Das Skript prüft automatisch die Erreichbarkeit des Turnstile Solvers und startet anschließend den Uvicorn-Server.

- **Web-Verwaltungskonsole**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **OpenAPI / Swagger Dokumentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **OpenAI-kompatibler Endpunkt**: `http://127.0.0.1:8000/v1`

---

## 🖥️ Verwendung der Web-Verwaltungskonsole

1. **Authentifizierung**: Tragen Sie oben rechts im Feld `🔑 网关密钥` Ihren in `.env` definierten `API_KEY` ein (z. B. `change-me`). Dieser wird sicher im lokalen Speicher Ihres Browsers abgelegt.
2. **Automatisierte Registrierung**: Geben Sie die gewünschte Anzahl ein und klicken Sie auf `🚀 开始批量注册`.
3. **Konten-Wiederherstellung (Recovery)**:
   - *Einzelnes Konto*: Geben Sie eine E-Mail-Adresse ein und klicken Sie auf `找回此号`.
   - *Vollständige Wiederherstellung*: Klicken Sie auf `一键找回全部`, um alle bereits registrierten E-Mails aus der Sperrliste automatisch zu reaktivieren und dem Pool hinzuzufügen.
4. **2API Playground**: Testen Sie beliebige offizielle Modelle direkt im Browser mit sofortiger Antwortanzeige.

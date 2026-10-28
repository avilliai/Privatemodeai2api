# Privatemode AI 2API & Automated Account Manager

<p align="center">
  <b>Language / Sprache / 语言:</b>
  <a href="README.md">Deutsch</a> |
  <b>English</b> |
  <a href="README_ZH.md">中文</a>
</p>

---

A high-performance, production-ready **2API Gateway**, automated registration worker, and account recovery engine for [Privatemode AI](https://portal.privatemode.ai/).

This gateway transparently wraps official Privatemode SaaS License API keys into standard **OpenAI-compatible endpoints** (`/v1/chat/completions`, `/v1/models`, `/v1/embeddings`, etc.). It supports automatic Cloudflare Turnstile bypassing and Outlook IMAP OTP verification for bulk registration and account recovery.

---

## 🌟 Key Features

- **OpenAI Compatible Protocol**: Drop-in replacement for OpenAI API in Chatbox, NextChat, Cherry Studio, LobeChat, Claude Dev, and custom applications.
- **Complete Official Model Support**:
  - `glm-5.3`, `glm-latest` (1M tokens context, Chat)
  - `glm-5.3-flash`, `glm-flash-latest` (1M tokens context, Multimodal Text + Vision)
  - `gpt-oss-120b` (128k tokens context, Chat)
  - `deepseek-ocr-2` (OCR image & text parsing)
  - `qwen3-embedding-4b` (32k tokens, Embeddings)
  - `voxtral-mini-3b`, `whisper-large-v3` (Speech-to-text / Audio Transcriptions)
- **Automated Registration**: Automatic Cloudflare Turnstile token retrieval and Outlook IMAP OTP mailbox extraction.
- **Account Recovery Engine**: Automatically recovers accounts already registered on Privatemode via Clerk sign-in and IMAP verification, generating fresh License Keys and adding them back to the active pool.
- **Web Management Dashboard**: Beautiful Mocha & Cream responsive dashboard featuring real-time pool metrics, token management, batch recovery, and an interactive 2API testing playground.

---

## 🔗 Turnstile Solver Project & Setup

For solving Cloudflare Turnstile verification during registration and recovery:

- **Repository**: [https://github.com/D3-vin/Turnstile-Solver-NEW](https://github.com/D3-vin/Turnstile-Solver-NEW)

### Deployment Steps:

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

## 📖 Configuration & Guide

### 1. Outlook Accounts File

Place your Outlook accounts file in the **project root directory**:

- **File Path**:
  ```text
  Privatemodeai2api/
  └── outlook_accounts.txt
  ```
- **Format**: One account per line:
  ```text
  email----password----client_id----refresh_token
  ```

### 2. Environment Configuration (`.env`)

Copy the configuration template:
```bash
cp .env.example .env
```

Configure parameters in `.env`:
```ini
# Gateway Server
HOST=0.0.0.0
PORT=8000

# Gateway Access Auth Key (optional, enter into Web Dashboard)
API_KEY=change-me

# Outlook file path in project root
OUTLOOK_ACCOUNT_FILE=outlook_accounts.txt

# Turnstile Solver URL
TURNSTILE_SOLVER_URL=http://127.0.0.1:5072
TURNSTILE_SITEKEY=0x4AAAAAAAWXJGBD7bONzLBd
TURNSTILE_SOLVER_PATH=C:/Users/Administrator/PycharmProjects/Turnstile-Solver-NEW


# Storage Paths
ACCOUNT_FILE=data/accounts.json
OUTLOOK_BLACKLIST_FILE=data/outlook_email_blacklist.json
```

---

## 🚀 Running the Gateway

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Service
```bash
python run.py
```

- **Web Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API Base URL**: `http://127.0.0.1:8000/v1`

---

## 🖥️ Web Management Console Guide

1. **Authentication**: Enter your `API_KEY` (e.g. `change-me`) into the `🔑 网关密钥` input on the top navigation bar. It is stored in `localStorage`.
2. **Registration**: Set the account count and click `🚀 开始批量注册`.
3. **Account Recovery**:
   - *Single*: Enter an Outlook email and click `找回此号`.
   - *All*: Click `一键找回全部` to scan the blacklist and recover all registered accounts automatically.
4. **Testing Playground**: Select any official Privatemode model to verify streaming and responses directly.

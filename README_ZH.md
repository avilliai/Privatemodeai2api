# Privatemode AI 2API 网关与全自动账号池管理系统

<p align="center">
  <b>语言切换 / Language:</b>
  <a href="README.md">Deutsch</a> |
  <a href="README_EN.md">English</a> |
  <b>中文</b>
</p>

---

针对 [Privatemode AI](https://portal.privatemode.ai/) 打造的高性能 **2API 网关**，具备全自动账号注册、多账号轮询负载均衡、已注册账号一键找回及全功能 Web 管理控制台。

本系统将 Privatemode 账户生成的 SaaS License API Key 转换为标准的 **OpenAI 格式 REST API**（`/v1/chat/completions`, `/v1/models`, `/v1/embeddings` 等），与对话共享额度，支持批量轮询。

---

## 🌟 核心特性

- **标准 OpenAI /v1 接口**：零修改接入 NextChat、Chatbox、Cherry Studio、LobeChat、LangChain 等客户端。
- **官方完整模型矩阵**：
  - `glm-5.3` / `glm-latest` (1M 上下文，Chat)
  - `glm-5.3-flash` / `glm-flash-latest` (1M 上下文，多模态 图文)
  - `gpt-oss-120b` (128k 上下文，Chat)
  - `deepseek-ocr-2` (OCR 预览版图像文本解析)
  - `qwen3-embedding-4b` (32k Tokens，Embeddings 向量)
  - `voxtral-mini-3b` / `whisper-large-v3` (语音识别转写)
- **全自动注册流程**：联动 Turnstile Solver 求解人机验证，自动监听 Outlook IMAP 获取 6 位验证码，自动创建组织并提取 License API Key。
- **账号找回功能 (Account Recovery)**：针对因历史注册而在黑名单中标记为 `Email already registered in Privatemode` 的账号，提供一键找回与单个找回功能，通过 Clerk 登录协议重新签发 License Key 加入活跃号池，拒绝资源浪费。
- **Apollodorus 风格 Web 管理界面**：提供 Mocha & Cream 配色控制台，实时查看活跃号池指标、密钥鉴权、批量注册与找回、实时日志流、账号增删重置以及 2API 对话测试 Playground。

---

## 🔗 Turnstile Solver 部署说明

注册与账号找回过程需要使用 Cloudflare Turnstile 求解服务：

- **开源项目地址**：[https://github.com/D3-vin/Turnstile-Solver-NEW](https://github.com/D3-vin/Turnstile-Solver-NEW)

### 部署步骤：

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

## 📖 配置与使用教程

### 1. 放置 Outlook 邮箱文件

将你的 Outlook 邮箱文件放置在 **项目根目录** 下：

- **放置路径**：
  ```text
  Privatemodeai2api/
  └── outlook_accounts.txt
  ```
- **文件格式**：每行一个账号，支持格式：
  ```text
  email----password----client_id----refresh_token
  ```
  *(若有 IMAP 应用密码，亦支持 `email----password` 格式)*。

### 2. 填写配置文件 (`.env`)

复制环境配置文件模板：
```bash
cp .env.example .env
```

核心配置项说明：
```ini
# 服务端口
HOST=0.0.0.0
PORT=8000

# 网关鉴权 Key（设置后客户端请求 /v1 需携带 Bearer <API_KEY>）
API_KEY=change-me

# Outlook 邮箱文件路径（在根目录下）
OUTLOOK_ACCOUNT_FILE=outlook_accounts.txt

# Turnstile Solver 求解器地址
TURNSTILE_SOLVER_URL=http://127.0.0.1:5072
TURNSTILE_SITEKEY=0x4AAAAAAAWXJGBD7bONzLBd
TURNSTILE_SOLVER_PATH=C:/Users/Administrator/PycharmProjects/Turnstile-Solver-NEW


# 号池数据持久化
ACCOUNT_FILE=data/accounts.json
OUTLOOK_BLACKLIST_FILE=data/outlook_email_blacklist.json
```

---

## 🚀 启动网关服务

### 1. 安装项目依赖
```bash
pip install -r requirements.txt
```

### 2. 一键启动网关
```bash
python run.py
```

- **Web 控制台地址**：[http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API 文档**：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API 请求基地址**：`http://127.0.0.1:8000/v1`

---

## 🖥️ Web 管理界面操作说明

1. **鉴权密钥配置**：在导航栏右上角 `🔑 网关密钥` 中输入在 `.env` 中配置的 `API_KEY`（如 `change-me`），数据将自动保存在浏览器 `localStorage` 中。
2. **批量注册**：设置注册数量，点击 `🚀 开始批量注册`，下方终端窗口可实时查看注册进度。
3. **账号找回**：
   - *单个找回*：输入已注册邮箱，点击 `找回此号`。
   - *一键找回*：点击 `一键找回全部`，系统自动扫描黑名单中所有已被占用的邮箱，批量执行 Clerk 登录重签 License Key 并激活入池。
4. **2API 在线测试**：选择官方模型，输入 Prompt 即可实时测试网关转发效果。

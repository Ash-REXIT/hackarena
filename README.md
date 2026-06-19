# FoxZilla

**Your documents first. The internet second.**

FoxZilla is a privacy-first local AI assistant built on the **Mozilla AI stack** (llamafile, encoderfile, mcpd, any-agent). It searches your private documents before touching the public web, and shows confidence, privacy score, and sources for every answer.

---

## What it does

| Route | When | Privacy |
|-------|------|---------|
| **Local docs** | Question matches files in `private_docs/` | ~100 |
| **MCP tools** | Live time, timezone, URL fetch | ~85 |
| **Web search** | Local confidence is low or question needs public facts | ~35 |

The UI runs at **http://localhost:8000** — chat, document upload, agent timeline, and settings in one place.

---

## Architecture

```
Browser (:8000)
    └─ FastAPI + React
           └─ PrivateLens pipeline
                  ├─ Retriever  → encoderfile (:8081) + private_docs/
                  ├─ Decision   → local / web / MCP
                  ├─ Web Agent  → Wikipedia + DuckDuckGo (external)
                  └─ Answer Agent → any-agent → llamafile (:8080)
                                       └─ MCP tools → mcpd (:8090)
```

---

## Prerequisites

Install these before cloning:

| Requirement | Purpose |
|-------------|---------|
| **Windows 10/11** | Primary dev environment (PowerShell scripts) |
| **Python 3.11+** | Backend API and agent |
| **Node.js 18+** | Frontend build |
| **WSL2 (Ubuntu)** | encoderfile and mcpd run inside Linux |
| **llamafile + a GGUF model** | Local LLM ([Mozilla llamafile](https://github.com/Mozilla-Ocho/llamafile)) |
| **Git** | Clone this repo |

**Ports used:** `8000` (app), `8080` (llamafile), `8081` (encoderfile), `8090` (mcpd).

---

## 1. Clone the repository

```powershell
git clone <YOUR_GITHUB_REPO_URL>
cd proj
```

Replace `<YOUR_GITHUB_REPO_URL>` with the link you share. The rest of this guide assumes your clone lives at something like `D:\proj` — adjust paths to match your machine.

---

## 2. Backend setup

```powershell
cd backend
pip install -r requirements.txt
copy .env.example .env
```

Edit **`backend\.env`** with your paths:

```env
# Path to your llamafile executable (Windows)
LLAMAFILE_PATH=C:\path\to\your\Qwen3.5-0.8B-Q8_0.exe

# Path to encoderfile binary inside WSL (after setup below)
ENCODERFILE_BINARY=/home/YOUR_USER/mozilla-hackathon/encoderfile/build/sentiment-analyzer.encoderfile

LLM_API_BASE=http://localhost:8080/v1
LLM_MODEL_ID=openai:Qwen3.5-0.8B-Q8_0.gguf
LLM_MAX_TURNS=3
LLM_TEMPERATURE=0.1

ENCODERFILE_BASE_URL=http://localhost:8081
MCPD_BASE_URL=http://localhost:8090

RETRIEVAL_TOP_K=4
RETRIEVAL_CHUNK_SIZE=512
INTERNET_FALLBACK=true
INTERNET_LIMIT=50
```

| Variable | Description |
|----------|-------------|
| `LLAMAFILE_PATH` | Full Windows path to your llamafile `.exe` |
| `ENCODERFILE_BINARY` | WSL path to the built encoderfile binary |
| `LLM_MAX_TURNS` | Agent tool-call limit (raise to `6` for complex MCP chains) |
| `INTERNET_FALLBACK` | Allow web search when local docs are not enough |
| `INTERNET_LIMIT` | Max web searches per session (Settings page) |

---

## 3. Frontend setup

```powershell
cd ..\frontend
npm install
cd ..
```

`start.ps1` runs `npm run build` automatically; you only need `npm install` once.

---

## 4. First-time WSL setup (encoderfile + mcpd)

Open **PowerShell** from the repo root.

### encoderfile

Builds the document encoder in WSL (~5–15 minutes first run):

```powershell
wsl -e bash /mnt/d/proj/scripts/setup-encoderfile.sh
```

> **Path note:** If your repo is not on `D:`, convert your Windows path to WSL form, e.g.  
> `wsl -e bash "$(wslpath -u 'C:\Users\you\proj')\scripts/setup-encoderfile.sh"`

When setup finishes, copy the printed binary path into `ENCODERFILE_BINARY` in `backend\.env`.

### mcpd

MCP daemon provides **time** and **fetch** tools. Install the `mcpd` binary in WSL (see [Mozilla mcpd docs](https://github.com/mozilla-ai/mcpd)), then verify config:

```powershell
wsl -e bash /mnt/d/proj/scripts/setup-mcpd.sh
```

**Update hardcoded paths in `start-mcpd.ps1`** if your WSL username or install location differs:

```powershell
# Defaults in start-mcpd.ps1 — change to match your WSL install
$mcpdBin = "/home/YOUR_USER/mozilla-hackathon/mcpd/mcpd"
$projectMcpdDir = "/mnt/d/proj/mcpd"   # WSL path to this repo's mcpd/ folder
```

Config file: `mcpd/.mcpd.toml` (time + fetch servers).

### Optional one-shot setup script

```powershell
.\setup-hackathon.ps1
```

Runs encoderfile setup and preflight checks.

---

## 5. Get llamafile + model

1. Download **llamafile** and a **GGUF model** (e.g. Qwen3.5-0.8B) from Mozilla / Hugging Face.
2. Set `LLAMAFILE_PATH` in `backend\.env` to the `.exe` path.
3. Ensure `LLM_MODEL_ID` in `.env` matches the model name llamafile exposes.

---

## 6. Start the stack

Run **four separate terminals** from the repo root:

```powershell
# Terminal 1 — local LLM
.\start-llamafile.ps1

# Terminal 2 — document encoder (WSL)
.\start-encoderfile.ps1

# Terminal 3 — MCP daemon (WSL)
.\start-mcpd.ps1

# Terminal 4 — build UI + API
.\start.ps1
```

Or list all commands:

```powershell
.\start-all.ps1
```

### Verify everything is up

```powershell
.\preflight.ps1
```

Expected: llamafile, encoderfile, mcpd, and app all show `[OK]`.

Open **http://localhost:8000** in your browser.

### Stop / restart the app

```powershell
.\stop.ps1      # frees port 8000
.\start.ps1     # rebuild frontend + start backend
```

---

## 7. Using FoxZilla

### Chat

1. Open **Chat** in the sidebar.
2. Type a question and send.
3. Watch the agent timeline (Retriever → Decision → Local/Web → Answer).
4. Each reply shows **Confidence**, **Privacy**, and **source tags**.

**Example queries**

| Question | Expected behavior |
|----------|-------------------|
| Content from your uploaded `.txt` files | Local docs, Privacy ~100 |
| `what is your name` | Reads `private_docs/lk.txt` via LLM |
| `what time is it in Tokyo?` | MCP time tool via mcpd |
| `who is the CEO of Google?` | Web search + LLM synthesis |

Use **New Chat** after backend restarts to avoid stale answers.

### Add your own documents

1. Go to **Documents**.
2. Upload `.txt`, `.pdf`, or `.docx` files.
3. Files are saved to `private_docs/` and indexed automatically.
4. Ask questions about them in Chat.

Sample files ship in `private_docs/` (`company_policy.txt`, `product_faq.txt`, etc.) — replace or extend with your own data.

### Settings

Open **Settings** to adjust:

- **Top K** — how many document chunks to retrieve
- **Chunk size** — indexing granularity
- **Internet fallback** — allow/disable web search
- **Internet budget** — max web queries per session
- **Temperature** — LLM creativity (reloads agent when changed)

---

## 8. Development mode (optional)

For frontend hot reload without rebuilding:

```powershell
# Terminal A — backend only
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal B — Vite dev server
cd frontend
npm run dev
```

UI: **http://localhost:5173** (proxies API to `:8000` if configured in Vite).

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 8000 already in use | Run `.\stop.ps1`, close browser tabs on localhost:8000, retry |
| Llamafile not found | Set `LLAMAFILE_PATH` in `backend\.env` |
| Encoderfile binary missing | Re-run `setup-encoderfile.sh`, update `ENCODERFILE_BINARY` |
| MCPD won't start | Check `start-mcpd.ps1` WSL paths and `mcpd/.mcpd.toml` |
| Health check times out | Ensure all four services are running; use `.\preflight.ps1` |
| Wrong / old answers in UI | Hard refresh (Ctrl+Shift+R) + **New Chat** |
| Web answers inaccurate | Small models (0.8B) struggle with noisy web snippets; consider a larger GGUF model in llamafile |
| `scripts/load-env.ps1` / `.env` not picked up | Confirm `backend\.env` exists (copy from `.env.example`) |

**Logs:** The terminal running `start.ps1` shows uvicorn access logs and Any-Agent `CALL_LLM` traces when the LLM runs.

---

## 10. Project layout

```
proj/
├── backend/           FastAPI, PrivateLens pipeline, any-agent, tools
│   ├── agent/         Agent orchestration and prompts
│   ├── documents/     Local doc indexing and search
│   ├── routes/        REST API
│   └── tools/         Web, MCP wrappers, role extraction
├── frontend/          React + Vite UI
├── private_docs/      Your local knowledge base (gitignored uploads OK)
├── mcpd/              MCPD server config (.mcpd.toml)
├── scripts/           WSL setup + env loader
├── start*.ps1         Service launchers
├── stop.ps1           Stop backend on port 8000
└── preflight.ps1      Stack health check
```

---

## 11. API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send `{ "query": "...", "request_id": "..." }` |
| `GET` | `/api/chat/status` | Poll job progress while chat runs |
| `GET` | `/api/health` | Full stack health (llamafile, encoderfile, mcpd) |
| `GET` | `/api/documents` | List indexed documents |
| `POST` | `/api/documents/upload` | Upload a document |
| `GET/PATCH` | `/api/settings` | Read/update runtime settings |
| `GET` | `/api/tools` | Active and available tools |

Interactive docs: **http://localhost:8000/docs** (when backend is running).

---

## 12. Privacy model

- **Local path:** Documents, embeddings, and LLM inference stay on your machine → Privacy **100**.
- **MCP path:** Live tools (time, fetch) via local mcpd → Privacy **~85**.
- **Web path:** Wikipedia + DuckDuckGo HTTP calls → **external internet**, Privacy **~35**, **Web Used** badge shown.

FoxZilla always tries local documents first when confidence is high enough.

---

## 13. Credits

Built on the **Mozilla AI hackathon stack**:

- [llamafile](https://github.com/Mozilla-Ocho/llamafile) — local LLM server
- [encoderfile](https://github.com/mozilla-ai/encoderfile) — document encoder
- [mcpd](https://github.com/mozilla-ai/mcpd) — MCP daemon
- [any-agent](https://github.com/mozilla-ai/any-agent) — agent framework

---

## Quick reference (copy-paste)

```powershell
# First time
git clone <YOUR_GITHUB_REPO_URL>
cd proj
cd backend && pip install -r requirements.txt && copy .env.example .env && cd ..
cd frontend && npm install && cd ..
# Edit backend\.env (LLAMAFILE_PATH, ENCODERFILE_BINARY)
wsl -e bash /mnt/d/proj/scripts/setup-encoderfile.sh

# Every session (4 terminals)
.\start-llamafile.ps1
.\start-encoderfile.ps1
.\start-mcpd.ps1
.\start.ps1

# Verify + open
.\preflight.ps1
# → http://localhost:8000
```

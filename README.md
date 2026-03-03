# FakeNews Tribunal

> An autonomous fact-checking system powered by a multi-agent AI debate pipeline.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![LiteLLM](https://img.shields.io/badge/LiteLLM-multi--provider-6C63FF)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

A user submits a claim or news headline. A jury of three specialized AI agents debates it across iterative rounds and returns a structured verdict — with a confidence score, source citations, and full reasoning transparency.

**Current release:** v0.3.x — Admin user management, SSE stability, dev seed, auth hardening.

---

## How It Works

```
Claim submitted
      │
      ▼
  Researcher ──► searches the web, collects evidence (pro & contra)
      │
      ▼
Devil's Advocate ──► challenges sources, hunts for logical flaws
      │
      ▼
    Judge ──► enough evidence? YES → emit verdict / NO → another round
      │
      ▼
  Verdict: label · confidence · reasoning · sources
```

Each round the Judge evaluates whether the evidence is sufficient. If not, the Researcher receives targeted guidance and the cycle repeats (max rounds configurable). The verdict carries one of five labels:

`TRUE` · `FALSE` · `MISLEADING` · `PARTIALLY_TRUE` · `UNVERIFIABLE`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| REST API | FastAPI + Uvicorn |
| Agent orchestration | Custom (no framework) |
| LLM abstraction | LiteLLM — Anthropic, OpenAI, Gemini, Ollama |
| Web search | Tavily |
| Source credibility | Domain-tier scoring (80+ domains, high/medium/low) |
| Database | PostgreSQL 16 + SQLAlchemy async + Alembic |
| Auth | JWT access tokens (8 h dev TTL) + bcrypt + refresh token rotation + proactive silent refresh |
| PDF export | fpdf2 (pure Python, no native dependencies) |
| Rate limiting | slowapi (10 analyses/hour per user) |
| CLI | Typer |
| Web UI | Next.js 16 + React 19 + Tailwind CSS 4 |
| Logging | structlog (JSON in prod, colored in dev) |
| Containerization | Docker Compose |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+ (for the web UI)
- Docker (for PostgreSQL)
- At least one LLM provider key — or a local [Ollama](https://ollama.com) instance

### 1. Clone and set up the Python environment

```bash
git clone https://github.com/your-username/fakenews-tribunal.git
cd fakenews-tribunal

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

Key variables:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude models |
| `OPENAI_API_KEY` | OpenAI GPT models |
| `GEMINI_API_KEY` | Google Gemini models |
| `OLLAMA_BASE_URL` | Local Ollama (default: `http://localhost:11434`) |
| `TAVILY_API_KEY` | Web search — required for all providers |
| `JWT_SECRET_KEY` | Auth secret — change in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL (default: `480` — 8 h; set to `30` in production) |
| `CORS_ORIGINS` | Allowed origins for the web UI (default: `["http://localhost:3000"]`) |

> You only need the key for the provider you intend to use. `TAVILY_API_KEY` is always required.

### 3. Start the database and run migrations

```bash
docker compose up db -d
PYTHONPATH=. alembic upgrade head
```

### 4. Start the API server

```bash
PYTHONPATH=. uvicorn api.main:app
```

API docs available at `http://localhost:8000/docs`.

> **Dev seed:** when `ENV=development` (default), the server automatically creates four test accounts on startup if they don't already exist:
> - `admin@tribunal.test` / `Admin1234!` — admin
> - `user1@tribunal.test` / `User1234!`
> - `user2@tribunal.test` / `User1234!`
> - `user3@tribunal.test` / `User1234!`

### 5. Start the Web UI

```bash
cd web
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL if needed
npm install
npm run dev
```

Web UI available at `http://localhost:3000`.

---

## Web UI

The web interface is a Next.js 16 app located in the `web/` subfolder. It provides:

- **Authentication** — register, login, logout with JWT token management and silent proactive refresh (no mid-session expiry)
- **Dashboard** — submit claims, configure provider/model/language/rounds, browse history
- **Ollama model browser** — when Ollama is selected as provider, available models are fetched live from the local instance
- **Live analysis view** — real-time SSE stream showing each agent's progress as it runs
- **Verdict display** — label, confidence, summary, full reasoning, supporting and contradicting sources with credibility tiers
- **Debate transcript** — collapsible round-by-round view of Researcher, Devil's Advocate, and Judge output
- **PDF export** — one-click download of the full verdict report
- **Resilient streaming** — client disconnect does not kill the background analysis; the SSE queue persists until the task completes
- **Admin panel** — list users, enable/disable accounts, delete users, view global usage stats

---

## CLI

### Local mode (no server required)

```bash
# Fact-check a claim directly
tribunal check "La Grande Muraglia cinese è visibile dalla Luna"

# Choose provider and model
tribunal check "Vaccines cause autism" --provider openai --model gpt-4o

# Use a local Ollama model
tribunal check "The Earth is flat" --provider ollama --model ollama/mistral --rounds 3

# Output as JSON
tribunal check "..." --output json
```

### Server mode (calls REST API)

```bash
# Register and log in
tribunal login --server http://localhost:8000 --register

# Submit via server (URL stored in ~/.tribunal/config.json after login)
tribunal check "La Terra è piatta" --provider anthropic

# Log out (invalidates refresh token server-side)
tribunal logout
```

---

## LLM Providers

| Provider | Default model | Env var |
|---|---|---|
| `anthropic` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-4o` | `OPENAI_API_KEY` |
| `gemini` | `gemini/gemini-2.0-flash` | `GEMINI_API_KEY` |
| `ollama` | `ollama/llama3.2` | `OLLAMA_BASE_URL` |

Override the model per-request with `--model <model-name>` (CLI), `"llm_model"` field (API), or via the model selector in the web UI. For Ollama, the web UI fetches the list of locally available models automatically.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Get tokens |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token |
| `POST` | `/api/v1/auth/logout` | Invalidate refresh token |
| `POST` | `/api/v1/analysis` | Submit claim → 202 Accepted (10/hour per user) |
| `GET` | `/api/v1/analysis/{id}` | Poll result |
| `GET` | `/api/v1/analysis/{id}/stream` | Stream debate progress via SSE |
| `GET` | `/api/v1/analysis/{id}/export` | Download verdict as PDF |
| `GET` | `/api/v1/analysis` | History (paginated) |
| `DELETE` | `/api/v1/analysis/{id}` | Delete analysis |
| `GET` | `/api/v1/providers/ollama/models` | List available Ollama models |
| `GET` | `/api/v1/auth/me` | Current user info |
| `POST` | `/api/v1/analysis/{id}/resume` | Resume an interrupted analysis |
| `GET` | `/api/v1/admin/users` | List all users (admin only) |
| `GET` | `/api/v1/admin/users/{id}` | User detail (admin only) |
| `PATCH` | `/api/v1/admin/users/{id}` | Update email/password/is_admin/is_disabled (admin only) |
| `DELETE` | `/api/v1/admin/users/{id}` | Delete user (admin only) |
| `GET` | `/api/v1/admin/stats` | Global usage stats (admin only) |
| `GET` | `/api/v1/health` | Health check |

### Quick curl walkthrough

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'

# Submit a claim (returns analysis_id immediately)
curl -X POST http://localhost:8000/api/v1/analysis \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"claim": "La Terra è piatta", "llm_provider": "anthropic", "max_rounds": 3}'

# Poll for the result
curl http://localhost:8000/api/v1/analysis/<analysis_id> \
  -H "Authorization: Bearer <access_token>"

# Export PDF
curl http://localhost:8000/api/v1/analysis/<analysis_id>/export \
  -H "Authorization: Bearer <access_token>" \
  --output verdict.pdf
```

---

## Running Tests

```bash
# Unit tests (no API keys needed)
PYTHONPATH=. pytest tests/unit/ -v

# Integration tests (real APIs required)
RUN_INTEGRATION=1 PYTHONPATH=. pytest tests/integration/ -v
```

---

## Roadmap

### v0.1 — Core ✓
- [x] Multi-agent debate loop (Researcher, Devil's Advocate, Judge)
- [x] LiteLLM multi-provider support (Anthropic, OpenAI, Gemini, Ollama)
- [x] Tavily web search integration
- [x] FastAPI REST API with JWT auth
- [x] PostgreSQL persistence + Alembic migrations
- [x] CLI local mode
- [x] Docker Compose setup

### v0.2 — Streaming & Operations ✓
- [x] SSE streaming endpoint (`GET /api/v1/analysis/{id}/stream`)
- [x] CLI server mode (`tribunal login` + `tribunal check --server URL`)
- [x] Per-user rate limiting (10 analyses/hour, slowapi)
- [x] Admin endpoints (user management, usage stats)

### v0.3 — Credibility, Export & Web UI ✓
- [x] Source credibility scoring (domain-tier system, propagated to Judge prompt)
- [x] PDF verdict export (fpdf2, pure Python)
- [x] Web UI (Next.js 16 + React 19 + Tailwind 4, dark theme)
- [x] Ollama model browser in web UI (live fetch from local instance)
- [x] CORS configuration via `CORS_ORIGINS` env var
- [x] Resilient SSE — client disconnect no longer kills the background analysis

### v0.3.x — Admin, Auth Hardening & Dev Experience ✓
- [x] User management: `is_disabled` field, PATCH admin endpoint, disable/enable from web UI
- [x] Resume endpoint — restart an interrupted or failed analysis (`POST /analysis/{id}/resume`)
- [x] Dev seed — test accounts created automatically on startup (`ENV=development`)
- [x] Access token TTL increased to 8 h for local LLM sessions (Ollama can take 20–30 min)
- [x] Proactive silent token refresh in the web UI (60 s before expiry, no mid-session logout)
- [x] SSE queue lifecycle fix — `push_done()` is the sole owner; client reconnects are safe
- [x] Credibility scoring fixes — `removeprefix("www.")` instead of `lstrip`; registrable domains in `_HIGH`
- [x] `processing_time_ms` now correctly populated from DB column

### Future
- [ ] Webhook support on verdict completion
- [ ] Batch analysis endpoint
- [ ] Plugin system for custom agents

---

## License

MIT — see [LICENSE](LICENSE).

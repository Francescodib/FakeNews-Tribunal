# FakeNews Tribunal

> An autonomous fact-checking system powered by a multi-agent AI debate pipeline.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white)
![LiteLLM](https://img.shields.io/badge/LiteLLM-multi--provider-6C63FF)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

A user submits a claim or news headline. A jury of three specialized AI agents debates it across iterative rounds and returns a structured verdict — with a confidence score, source citations, and full reasoning transparency.

**Current release:** v0.2 — SSE streaming, rate limiting, CLI server mode. Web UI in active development.

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
| Database | PostgreSQL 16 + SQLAlchemy async + Alembic |
| Auth | JWT access tokens + bcrypt refresh tokens |
| CLI | Typer |
| Logging | structlog (JSON in prod, colored in dev) |
| Containerization | Docker Compose |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker (for PostgreSQL)
- At least one LLM provider key — or a local [Ollama](https://ollama.com) instance

### 1. Clone and set up the environment

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

Minimum required keys:

| Key | Required for |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude models |
| `OPENAI_API_KEY` | OpenAI GPT models |
| `GEMINI_API_KEY` | Google Gemini models |
| `OLLAMA_BASE_URL` | Local Ollama (default: `http://localhost:11434`) |
| `TAVILY_API_KEY` | Web search (all providers) |
| `JWT_SECRET_KEY` | API auth — change in production |

> You only need the key for the provider you intend to use. Tavily is always required.

### 3. Start the database and run migrations

```bash
docker compose up db -d
PYTHONPATH=. alembic upgrade head
```

### 4a. CLI mode (no server needed)

```bash
# Fact-check a claim directly (local, no server required)
tribunal check "La Grande Muraglia cinese è visibile dalla Luna"

# Choose provider and model
tribunal check "Vaccines cause autism" --provider openai --model gpt-4o

# Use a local Ollama model
tribunal check "The Earth is flat" --provider ollama --model mistral-small --rounds 3

# Output as JSON
tribunal check "..." --output json
```

### 4b. CLI server mode (calls REST API)

```bash
# Register and log in
tribunal login --server http://localhost:8000 --register

# Re-use stored credentials for subsequent calls
tribunal check "La Terra è piatta" --server http://localhost:8000 --provider anthropic

# --server can be omitted after login (URL is stored in ~/.tribunal/config.json)
tribunal check "Vaccines cause autism"

# Log out (invalidates refresh token server-side)
tribunal logout
```

### 4b. API server mode

```bash
PYTHONPATH=. uvicorn api.main:app --reload
```

API docs available at `http://localhost:8000/docs`.

#### Quick API walkthrough

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
```

---

## LLM Providers

| Provider | Default model | Env var |
|---|---|---|
| `anthropic` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-4o` | `OPENAI_API_KEY` |
| `gemini` | `gemini/gemini-2.0-flash` | `GEMINI_API_KEY` |
| `ollama` | `ollama/llama3.2` | `OLLAMA_BASE_URL` |

Override the model per-request with `--model <model-name>` (CLI) or `"llm_model"` (API).

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Get tokens |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token |
| `POST` | `/api/v1/auth/logout` | Invalidate refresh token |
| `POST` | `/api/v1/analysis` | Submit claim → 202 Accepted (10/hour rate limit) |
| `GET` | `/api/v1/analysis/{id}` | Poll result |
| `GET` | `/api/v1/analysis/{id}/stream` | Stream debate progress via SSE |
| `GET` | `/api/v1/analysis` | History (paginated) |
| `DELETE` | `/api/v1/analysis/{id}` | Delete analysis |
| `GET` | `/api/v1/health` | Health check |

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

### v0.1 — Core *(current)*
- [x] Multi-agent debate loop (Researcher, Devil's Advocate, Judge)
- [x] LiteLLM multi-provider support
- [x] Tavily web search integration
- [x] FastAPI REST API with JWT auth
- [x] PostgreSQL persistence + Alembic migrations
- [x] CLI local mode
- [x] Docker Compose setup

### v0.2 — Streaming & Polish *(current)*
- [x] SSE streaming endpoint (`GET /api/v1/analysis/{id}/stream`)
- [x] CLI server mode (`tribunal login` + `tribunal check --server URL`)
- [x] Per-user rate limiting (10 analyses/hour, slowapi)
- [ ] Admin endpoints (user management, usage stats)

### v0.3 — Web UI & Export
- [ ] Web UI (React / SvelteKit — separate repo)
- [ ] PDF verdict export
- [ ] Source credibility scoring

### Future
- [ ] Webhook support on verdict completion
- [ ] Batch analysis endpoint
- [ ] Plugin system for custom agents

---

## License

MIT — see [LICENSE](LICENSE).

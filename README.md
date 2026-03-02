# FakeNews Tribunal

Autonomous fact-checking system powered by a multi-agent AI pipeline. A claim is submitted and debated by three specialized agents (Researcher, Devil's Advocate, Judge) across iterative rounds, producing a structured verdict with confidence score and source citations.

## Stack

- **API:** FastAPI + Uvicorn
- **Agents:** Custom orchestrator (no framework)
- **LLM:** LiteLLM (Anthropic, OpenAI, Gemini, Ollama)
- **Search:** Tavily
- **DB:** PostgreSQL 16 + SQLAlchemy async + Alembic
- **Auth:** JWT (python-jose) + bcrypt (passlib)
- **CLI:** Typer

## Quick Start

```bash
# 1. Copy and fill environment variables
cp .env.example .env

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Start the database
docker compose up db -d

# 4. Run migrations
alembic upgrade head

# 5. Start the API server
uvicorn api.main:app --reload

# 6. Or use the CLI directly (no server needed)
tribunal check "The Earth is flat"
tribunal check "La Terra è piatta" --provider ollama --model llama3.2
```

## Supported LLM Providers

| Provider   | Default model            | Env var needed         |
|------------|--------------------------|------------------------|
| anthropic  | claude-sonnet-4-6        | ANTHROPIC_API_KEY      |
| openai     | gpt-4o                   | OPENAI_API_KEY         |
| gemini     | gemini/gemini-2.0-flash  | GEMINI_API_KEY         |
| ollama     | ollama/llama3.2          | OLLAMA_BASE_URL        |

## Verdict Labels

`TRUE` · `FALSE` · `MISLEADING` · `PARTIALLY_TRUE` · `UNVERIFIABLE`

## License

MIT

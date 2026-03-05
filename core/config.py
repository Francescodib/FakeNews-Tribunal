from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known insecure placeholder values that must never be used.
# Comparison is case-insensitive for the lower-cased variants.
_INSECURE_JWT_DEFAULTS = {
    "change-me-in-production",
    "changeme",
    "secret",
    "",
    "unset",
}
# Prefixes that indicate an unset placeholder (checked case-insensitively).
_INSECURE_JWT_PREFIXES = ("replace-this", "changeme", "your-secret")
_MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    # LLM
    DEFAULT_PROVIDER: str = "anthropic"
    PROVIDER_MODEL_MAP: dict = {
        "anthropic": "claude-sonnet-4-6",
        "openai": "gpt-4o",
        "gemini": "gemini/gemini-2.0-flash",
        "ollama": "ollama/llama3.2",
    }

    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Search
    TAVILY_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://tribunal:tribunal@localhost:5432/tribunal"

    # Auth
    # No safe in-code default: the validator below will reject any short or
    # known-insecure value.  Set JWT_SECRET_KEY in your .env file.
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    JWT_SECRET_KEY: str = "UNSET"
    JWT_ALGORITHM: str = "HS256"
    # 480 min (8 h) default — suits long local-LLM analyses (Ollama can take 20-30 min).
    # Set to 30 in production via .env.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Debate
    MAX_DEBATE_ROUNDS: int = 5

    # Webhooks
    WEBHOOK_TIMEOUT_S: int = 10
    WEBHOOK_MAX_RETRIES: int = 3

    # Batch
    MAX_BATCH_SIZE: int = 10

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENV: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ------------------------------------------------------------------
    # Field-level validators (run before model_validator)
    # ------------------------------------------------------------------

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_be_set(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "DATABASE_URL must be set to a non-empty connection string."
            )
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def jwt_secret_must_be_strong(cls, v: str) -> str:
        v_lower = v.lower()
        # Check against known insecure placeholder values and common prefixes.
        is_known_bad = (
            v_lower in _INSECURE_JWT_DEFAULTS
            or any(v_lower.startswith(p) for p in _INSECURE_JWT_PREFIXES)
        )
        if is_known_bad:
            raise ValueError(
                f"JWT_SECRET_KEY is set to an insecure placeholder value ({v!r}). "
                "Generate a real secret with: "
                "python -c \"import secrets; print(secrets.token_hex(32))\" "
                "and set it in your .env file."
            )
        if len(v) < _MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY is too short ({len(v)} chars). "
                f"It must be at least {_MIN_JWT_SECRET_LENGTH} characters long. "
                "Generate one with: "
                "python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    # ------------------------------------------------------------------
    # Cross-field / environment-aware validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def production_checks(self) -> "Settings":
        """Enforce stricter rules when ENV=production."""
        if self.ENV != "production":
            return self

        # Tavily API key is required in production (search is a core feature).
        if not self.TAVILY_API_KEY or not self.TAVILY_API_KEY.strip():
            raise ValueError(
                "TAVILY_API_KEY must be set in production. "
                "The search/credibility pipeline will not function without it."
            )

        # CORS origins must not contain wildcard or localhost in production.
        unsafe_origins = {"*", "http://localhost:3000", "http://localhost"}
        bad = [o for o in self.CORS_ORIGINS if o in unsafe_origins or o == "*"]
        if bad:
            raise ValueError(
                f"CORS_ORIGINS contains insecure values in production: {bad}. "
                "Remove wildcards and localhost entries and set your real domain(s)."
            )

        return self


settings = Settings()

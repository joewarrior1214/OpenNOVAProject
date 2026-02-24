"""Nova Syntheia — Application configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class NovaSettings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # ── LLM Providers ──────────────────────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    judicial_model: str = "anthropic/claude-sonnet-4-20250514"
    executive_model: str = "openai/gpt-4o"
    federal_reserve_model: str = "anthropic/claude-sonnet-4-20250514"
    citation_model: str = "openai/gpt-4o-mini"
    custodian_model: str = "openai/gpt-4o-mini"

    # ── PostgreSQL (National Ledger) ───────────────────────────
    postgres_user: str = "nova_syntheia"
    postgres_password: str = "change-me-in-production"
    postgres_db: str = "national_ledger"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url_async(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── ChromaDB ───────────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8100

    # ── Alpaca ─────────────────────────────────────────────────
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # ── Dashboard ──────────────────────────────────────────────
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000
    jwt_secret_key: str = "change-me-generate-a-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    # ── Nova Syntheia ──────────────────────────────────────────
    founding_era: bool = True
    human_founder_id: str = "founder-001"
    emergency_deliberation_hours: int = 24
    normal_deliberation_days: int = 7

    # ── Logging ────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "json"


settings = NovaSettings()

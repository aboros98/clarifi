from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./clarifi.db"

    # Supabase (for Storage + Auth)
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""  # From Supabase Settings → API → JWT Secret

    # LLM
    google_api_key: str = ""
    llm_model: str = "gemini-3.1-flash-lite-preview"
    llm_extraction_model: str = "gemini-2.5-flash-lite"

    # File discovery
    watch_dir: str = "./inbox"
    processed_dir: str = "./storage"  # permanent file storage (copies of originals)

    # Google Drive
    google_drive_client_id: str = ""
    google_drive_client_secret: str = ""
    google_drive_redirect_uri: str = "http://localhost:3000/auth/callback"

    # Telegram
    telegram_bot_token: str = ""

    # memU (long-term semantic memory — self-hosted via Supabase PostgreSQL)
    # Uses Gemini directly via Google's OpenAI-compatible endpoint
    memu_enabled: bool = False
    memu_llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    memu_llm_api_key: str = ""  # Falls back to google_api_key if empty
    memu_llm_model: str = "gemini-2.5-flash-lite"

    # Extraction confidence
    auto_approve_threshold: float = 0.85

    # Data freshness (days)
    freshness_unverified_days: int = 7
    freshness_bank_stale_days: int = 3
    freshness_overdue_uncollectible_days: int = 60

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # Alert windows (days)
    alert_cashflow_days: int = 60
    alert_invoice_due_soon_days: int = 7
    alert_contract_expiry_days: int = 30


settings = Settings()  # type: ignore[call-arg]

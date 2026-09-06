from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root .env (repo/) and optional backend/.env
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"
_BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Central configuration — thresholds and secrets live here, not as magic numbers in analytics."""

    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), str(_BACKEND_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Smart Market Watchlist"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Database — host port 55432 avoids clash with local Postgres installs
    database_url: str = (
        "postgresql+asyncpg://watchlist:watchlist@127.0.0.1:55432/watchlist"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "dev-only-change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS — never use * with credentials
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001"
    )

    # Market data: replay (judge demo) | yahoo (delayed NSE via yfinance) | live (live-sim) | mock
    market_data_mode: str = "replay"

    # Feature flags
    enable_cusum: bool = True
    enable_llm: bool = False
    enable_news: bool = False
    enable_web_retrieval: bool = True
    enable_rolling_ols: bool = False
    enable_isolation_forest: bool = False
    enable_finbert: bool = False

    # LLM — free tier: Groq (recommended) or Gemini
    llm_provider: str = "groq"  # groq | gemini
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-20b"

    # Web Push (VAPID) — alerts when the tab is closed but the browser can still wake SW
    enable_web_push: bool = True
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:demo@example.com"

    # Scoring thresholds (documented defaults — not universal financial truths)
    top_k: int = 5
    history_sessions: int = 20
    min_history_points: int = 30
    freshness_limit_seconds: int = 30
    source_conflict_tolerance: float = 0.01
    max_watchlist_size: int = 100
    rvol_threshold: float = 2.0
    context_threshold: float = 0.015
    notable_price_z: float = 2.0
    cusum_k: float = 0.001
    cusum_h: float = 0.02
    anomaly_percentile_1: float = 0.90
    anomaly_percentile_2: float = 0.95
    anomaly_percentile_3: float = 0.99

    # Severity weights for attention (band midpoints / legacy fallback)
    severity_weight_low: float = 0.1
    severity_weight_notable: float = 0.4
    severity_weight_worth_watching: float = 0.7
    severity_weight_high: float = 1.0

    # Cap absurd |z| for evidence chips (still continuous within band via excess)
    max_price_anomaly_z: float = 8.0

    # Demo talk-track: force DATA_CONFLICT on one symbol (empty = off)
    # Prefer a WORTH_WATCHING demo name (TCS) so the card is visible at MEDIUM sensitivity
    demo_conflict_symbol: str = "TCS"
    # Skip HDFC/TCS/RELIANCE calibration overlays (uncalibrated live moment)
    demo_skip_calibration: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

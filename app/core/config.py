from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings come from the .env file (or real environment variables)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    reservation_minutes: int = 10
    max_tickets_per_order: int = 10
    require_event_approval: bool = False

    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str = "tickets@ticketflow.local"


settings = Settings()

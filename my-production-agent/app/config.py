from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    app_name: str = "Production AI Agent"
    app_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    redis_url: str = "redis://localhost:6379/0"
    agent_api_key: str = ""
    openai_api_key: str = ""
    llm_model: str = "gpt-5.4-mini"

    rate_limit_per_minute: int = 10
    monthly_budget_usd: float = 10.0
    history_max_items: int = 20


settings = Settings()

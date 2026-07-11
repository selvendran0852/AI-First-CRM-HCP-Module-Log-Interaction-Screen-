from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app configuration, loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://hcp_user:hcp_pass@localhost:5432/hcp_crm"

    groq_api_key: str = ""
    groq_primary_model: str = "gemma2-9b-it"
    groq_fallback_model: str = "llama-3.3-70b-versatile"

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    promptforge_env: str = Field(default="development", alias="PROMPTFORGE_ENV")
    port: int = Field(default=8000, alias="PORT")
    host: str = Field(default="0.0.0.0", alias="HOST")
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", alias="CORS_ORIGINS")

    # LLM Keys
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")
    ollama_enabled: bool = Field(default=True, alias="OLLAMA_ENABLED")

    # Tool integrations
    stripe_test_secret_key: str = Field(default="", alias="STRIPE_TEST_SECRET_KEY")

    # DB & Tenancy
    database_url: str = Field(default="sqlite+aiosqlite:///./promptforge.db", alias="DATABASE_URL")
    tenant_default_id: str = Field(default="tenant-demo", alias="TENANT_DEFAULT_ID")
    jwt_secret: str = Field(default="dev-insecure-secret-promptforge-key", alias="JWT_SECRET")
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_production_security(self) -> None:
        """Enforces security gates in production mode."""
        if self.promptforge_env == "production":
            if not self.jwt_secret or self.jwt_secret == "dev-insecure-secret-promptforge-key":
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: "
                    "Cannot run in production with default or empty JWT_SECRET. "
                    "Please configure a strong, unique secret via JWT_SECRET environment variable."
                )

settings = Settings()
settings.validate_production_security()

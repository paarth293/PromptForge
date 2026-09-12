from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    promptforge_env: str = Field(default="development", alias="PROMPTFORGE_ENV")
    port: int = Field(default=8000, alias="PORT")
    host: str = Field(default="0.0.0.0", alias="HOST")
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", alias="CORS_ORIGINS")

    # LLM Keys
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    # Legacy single Groq key (still honoured; tried after the numbered keys)
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")

    # Multi-key Groq fallback chain
    groq_api_key_1: str = Field(default="", alias="GROQ_API_KEY_1")
    groq_api_key_2: str = Field(default="", alias="GROQ_API_KEY_2")
    groq_api_key_3: str = Field(default="", alias="GROQ_API_KEY_3")
    groq_api_key_4: str = Field(default="", alias="GROQ_API_KEY_4")
    groq_api_key_5: str = Field(default="", alias="GROQ_API_KEY_5")
    # Extra Groq models to try (each model has its own rate-limit bucket) once the
    # primary model is rate-limited on every key. Comma-separated; blank disables.
    # Only real Groq production model IDs belong here. A non-existent ID still gets a
    # 429 from Groq's rate-limit layer (with a sub-second reset), so a typo'd model is
    # never reported as "unknown" — it just burns the rotation on every single call.
    groq_fallback_models: str = Field(
        default="openai/gpt-oss-20b,llama-3.3-70b-versatile,llama-3.1-8b-instant",
        alias="GROQ_FALLBACK_MODELS",
    )
    # If every Groq key/model is rate-limited but the shortest wait is at most this
    # many seconds (per-minute limits), wait once and retry instead of leaving Groq.
    groq_max_wait_seconds: float = Field(default=20.0, alias="GROQ_MAX_WAIT_SECONDS")
    groq_timeout_seconds: float = Field(default=45.0, alias="GROQ_TIMEOUT_SECONDS")

    # Ollama fallback (local LLM, no rate limits)
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")
    ollama_enabled: bool = Field(default=True, alias="OLLAMA_ENABLED")
    ollama_timeout_seconds: float = Field(default=300.0, alias="OLLAMA_TIMEOUT_SECONDS")
    ollama_num_ctx: int = Field(default=8192, alias="OLLAMA_NUM_CTX")

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

    @property
    def groq_api_keys_list(self) -> List[str]:
        """All configured Groq keys in fallback order (numbered keys first, then the
        legacy GROQ_API_KEY), with blanks and duplicates removed."""
        ordered = [
            self.groq_api_key_1,
            self.groq_api_key_2,
            self.groq_api_key_3,
            self.groq_api_key_4,
            self.groq_api_key_5,
            self.groq_api_key,
        ]
        keys: List[str] = []
        for k in ordered:
            k = (k or "").strip()
            if k and k not in keys:
                keys.append(k)
        return keys

    @property
    def groq_fallback_models_list(self) -> List[str]:
        return [m.strip() for m in self.groq_fallback_models.split(",") if m.strip()]

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

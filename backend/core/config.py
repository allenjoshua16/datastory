from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    # Provider: "gemini" or "groq"
    ai_provider: str = "groq"

    cors_origins: str = "http://localhost:5173"
    max_file_size_mb: int = 200          # ← bumped to 200 MB
    upload_dir: str = "./uploads"
    log_level: str = "info"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()

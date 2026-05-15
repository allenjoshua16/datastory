from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    # Gemini (free tier)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"  # ← free tier model
    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    # Provider: "groq" | "gemini" | "ollama"
    ai_provider: str = "groq"

    cors_origins: str = "http://localhost:5173"
    max_file_size_mb: int = 200
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

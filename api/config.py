"""FastAPI configuration for QF_Wiz Web API."""

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8787
    debug: bool = False

    # Security
    api_key: str = ""

    # CORS — comma-separated list of allowed origins, or the default dev origins
    # Override via SDC_ALLOWED_ORIGINS="https://myapp.fly.dev,https://other.com"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:80,http://localhost"

    # LLM provider (anthropic | openai)
    llm_provider: str = "anthropic"

    # Paths (relative to project root)
    root_dir: Path = Path(__file__).resolve().parents[1]

    @property
    def cors_origins(self) -> List[str]:
        """Parse allowed_origins string into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def runtime_dir(self) -> Path:
        return self.root_dir / "runtime"

    @property
    def tickets_ready_dir(self) -> Path:
        return self.root_dir / "tickets" / "ready"

    @property
    def tickets_results_dir(self) -> Path:
        return self.root_dir / "tickets" / "results"

    class Config:
        env_prefix = "SDC_"
        env_file = ".env"
        extra = "ignore"


settings = Settings()

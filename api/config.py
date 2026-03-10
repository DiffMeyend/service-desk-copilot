"""FastAPI configuration for QF_Wiz Web API."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8787
    debug: bool = False

    # Security
    api_key: str = ""

    # Paths (relative to project root)
    root_dir: Path = Path(__file__).resolve().parents[1]

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


settings = Settings()

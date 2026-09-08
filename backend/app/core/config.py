"""Environment-only configuration. No credentials in source (spec section 16)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Repo root = two levels up from this file: backend/app/core/config.py -> repo/
REPO_ROOT = Path(__file__).resolve().parents[3]

# Load repo-root .env explicitly (find_dotenv() is unreliable when the app is
# imported by uvicorn from an arbitrary CWD).
load_dotenv(REPO_ROOT / ".env")


class Settings:
    def __init__(self) -> None:
        self.database_url: str = _normalise_db_url(os.getenv("DATABASE_URL", "").strip())

        # Deterministic pseudonymisation secret. A pseudonym is not irreversible
        # anonymisation; keep the secret out of the frontend and out of logs.
        self.privacy_secret: str = os.getenv("PRIVACY_SECRET", "dev-privacy-secret-change-me")

        # auto  -> try the real ML pipeline, fall back to the heuristic engine
        # ml    -> require the ML pipeline (503 if unavailable)
        # heuristic -> always use the DB-config-backed heuristic engine
        self.advisor_engine: str = os.getenv("ADVISOR_ENGINE", "auto").strip().lower()

        # CORS origins for the Vite dev server (requests are usually proxied, so
        # this only matters for direct browser calls).
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.getenv(
                "BACKEND_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if o.strip()
        ]

        self.app_version: str = "0.1.0"

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url)


def _normalise_db_url(url: str) -> str:
    """Force the psycopg2 driver so SQLAlchemy picks the installed binary."""
    if not url:
        return url
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings()

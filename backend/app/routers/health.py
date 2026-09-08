from fastapi import APIRouter

from app.core.config import get_settings
from app.db.session import ping

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    db_ok = ping() if settings.database_configured else False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": settings.app_version,
        "database": "up" if db_ok else "down",
        "advisor_engine": settings.advisor_engine,
    }

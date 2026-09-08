from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from app.core.security import CurrentUser, get_current_user, require
from app.db.session import get_db
from app.services import advisor_service
from app.services.snapshot_service import require_snapshot

router = APIRouter(prefix="/api/models", tags=["models"])

Viewer = require("PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")


@router.get("/overview")
def overview(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "models.overview")


@router.get("/metrics")
def metrics(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "models.metrics")


@router.get("/versions")
def versions(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "models.versions")


@router.get("/explanations/{encounter_id}/{treatment_id}")
def explanation(
    encounter_id: str,
    treatment_id: str,
    conn: Connection = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    # A treating DOCTOR (own encounter) or a TECH_REVIEWER may view an attribution.
    return advisor_service.explanation(conn, user, encounter_id, treatment_id)

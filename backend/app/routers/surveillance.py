from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from app.core.security import CurrentUser, require
from app.db.session import get_db
from app.services.snapshot_service import require_snapshot

router = APIRouter(prefix="/api/surveillance", tags=["surveillance"])

Viewer = require("HOSPITAL_ADMIN", "PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")


@router.get("/overview")
def overview(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "surveillance.overview")


@router.get("/alerts")
def alerts(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "surveillance.alerts")


@router.get("/emerging-symptoms")
def emerging_symptoms(
    conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)
) -> dict:
    return require_snapshot(conn, "surveillance.emerging_symptoms")


@router.get("/trends")
def trends(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "surveillance.trends")

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from app.core.security import CurrentUser, require
from app.db.session import get_db
from app.services.snapshot_service import require_snapshot

router = APIRouter(prefix="/api/privacy", tags=["privacy"])

Viewer = require("HOSPITAL_ADMIN", "PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")


@router.get("/policy")
def policy(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "privacy.policy")


@router.get("/data-flow")
def data_flow(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "privacy.data_flow")


@router.get("/audit")
def audit(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "privacy.audit")

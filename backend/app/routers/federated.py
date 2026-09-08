from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from app.core.security import CurrentUser, require
from app.db.session import get_db
from app.services.snapshot_service import require_snapshot

router = APIRouter(prefix="/api/federated", tags=["federated"])

Viewer = require("HOSPITAL_ADMIN", "PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")


@router.get("/network")
def network(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "federated.network")


@router.get("/rounds")
def rounds(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "federated.rounds")


@router.get("/model")
def model(conn: Connection = Depends(get_db), user: CurrentUser = Depends(Viewer)) -> dict:
    return require_snapshot(conn, "federated.model")

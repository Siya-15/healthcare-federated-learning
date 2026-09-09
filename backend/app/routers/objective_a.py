from fastapi import APIRouter, Depends, Query
from app.core.security import CurrentUser, require
from app.services.objective_a_service import build_objective_a_response

router = APIRouter(prefix="/api/objectives/a", tags=["objectives"])

Viewer = require("HOSPITAL_ADMIN", "PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")


@router.get("")
def objective_a(
    refresh: bool = Query(False),
    include_records: bool = Query(True),
    record_limit: int = Query(50, ge=1, le=500),
    user: CurrentUser = Depends(Viewer),
) -> dict:
    return build_objective_a_response(
        refresh=refresh,
        include_records=include_records,
        record_limit=record_limit,
    )


@router.get("/latest")
def objective_a_latest(
    include_records: bool = Query(True),
    record_limit: int = Query(50, ge=1, le=500),
    user: CurrentUser = Depends(Viewer),
) -> dict:
    return build_objective_a_response(
        refresh=False,
        include_records=include_records,
        record_limit=record_limit,
    )

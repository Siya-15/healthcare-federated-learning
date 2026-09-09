from fastapi import APIRouter, HTTPException, Query

from app.services.objective_b_service import build_objective_b_response


router = APIRouter(
    prefix="/api/objectives/b",
    tags=["Objective B - Epidemic/Pandemic Detection"],
)


@router.get("")
def get_objective_b(
    refresh: bool = Query(
        True,
        description="Run B13's real continuous-update check before reading outputs.",
    ),
    include_records: bool = Query(
        False,
        description="Include detailed B1-B12 records in the response.",
    ),
    record_limit: int = Query(
        100,
        ge=1,
        le=1000,
    ),
):
    try:
        return build_objective_b_response(
            refresh=refresh,
            include_records=include_records,
            record_limit=record_limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Objective B integration failed: {exc}",
        ) from exc


@router.get("/latest")
def get_objective_b_latest(
    record_limit: int = Query(100, ge=1, le=1000),
):
    """
    Read the already-generated B outputs without rerunning B13.
    Useful for dashboard polling.
    """
    try:
        return build_objective_b_response(
            refresh=False,
            include_records=False,
            record_limit=record_limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Objective B latest-output read failed: {exc}",
        ) from exc

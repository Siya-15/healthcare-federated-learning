
from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, require
from app.services.objective_c4_service import build_c4_evidence


router = APIRouter(
    prefix="/api/privacy",
    tags=["privacy"],
)

Viewer = require(
    "HOSPITAL_ADMIN",
    "PUBLIC_HEALTH_ADMIN",
    "TECH_REVIEWER",
)


@router.get("/implementation")
def implementation(
    user: CurrentUser = Depends(Viewer),
) -> dict:
    return build_c4_evidence()

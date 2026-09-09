from fastapi import APIRouter, Depends
from app.core.security import CurrentUser, require
from app.services.live_objectives import privacy_status

router = APIRouter(prefix="/api/privacy", tags=["privacy"])
Viewer = require("HOSPITAL_ADMIN", "PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")

@router.get("/policy")
def policy(user: CurrentUser = Depends(Viewer)):
    return privacy_status()

@router.get("/data-flow")
def data_flow(user: CurrentUser = Depends(Viewer)):
    return privacy_status()

@router.get("/audit")
def audit(user: CurrentUser = Depends(Viewer)):
    return privacy_status()

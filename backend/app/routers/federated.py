from fastapi import APIRouter, Depends
from app.core.security import CurrentUser, require
from app.services.live_objectives import objective_c

router = APIRouter(prefix="/api/federated", tags=["federated"])
Viewer = require("HOSPITAL_ADMIN", "PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")

@router.get("/network")
def network(user: CurrentUser = Depends(Viewer)):
    return objective_c()

@router.get("/rounds")
def rounds(user: CurrentUser = Depends(Viewer)):
    data = objective_c()
    return {"configured_rounds": data["configured_rounds"], "aggregation": data["aggregation"], "status": data["status"]}

@router.get("/model")
def model(user: CurrentUser = Depends(Viewer)):
    data = objective_c()
    return {"framework": data["framework"], "aggregation": data["aggregation"], "configured_hospitals": data["configured_hospitals"], "privacy_controls": data["privacy_controls"]}

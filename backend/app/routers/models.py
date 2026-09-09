from fastapi import APIRouter, Depends
from app.core.security import CurrentUser, get_current_user, require
from app.services.live_objectives import model_metrics
from app.services import advisor_service
from app.db.session import get_db

router = APIRouter(prefix="/api/models", tags=["models"])
Viewer = require("PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")

@router.get("/overview")
def overview(user: CurrentUser = Depends(Viewer)):
    return model_metrics()

@router.get("/metrics")
def metrics(user: CurrentUser = Depends(Viewer)):
    return model_metrics()

@router.get("/versions")
def versions(user: CurrentUser = Depends(Viewer)):
    data = model_metrics()
    return {"models": {k: {"artifact_present": v.get("artifact_present"), "path": v.get("path")} for k, v in data["models"].items()}}

@router.get("/explanations/{encounter_id}/{treatment_id}")
def explanation(encounter_id: str, treatment_id: str, conn=Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return advisor_service.explanation(conn, user, encounter_id, treatment_id)

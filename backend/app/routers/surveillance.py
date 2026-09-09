from fastapi import APIRouter, Depends, Query
from app.core.security import CurrentUser, require
from app.db.session import get_db
from app.services.live_objectives import objective_a, objective_b

router = APIRouter(prefix="/api/surveillance", tags=["surveillance"])
Viewer = require("DOCTOR","HOSPITAL_ADMIN", "PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")

@router.get("/overview")
def overview(user: CurrentUser = Depends(Viewer), conn=Depends(get_db)):
    return objective_b(conn)

@router.get("/alerts")
def alerts(user: CurrentUser = Depends(Viewer), conn=Depends(get_db)):
    data = objective_b(conn)
    return {"assessment": data["assessment"], "source": data["source"]}

@router.get("/emerging-symptoms")
def emerging_symptoms(hospital_id: str | None = Query(default=None), user: CurrentUser = Depends(Viewer)):
    return objective_a(hospital_id)

@router.get("/trends")
def trends(user: CurrentUser = Depends(Viewer), conn=Depends(get_db)):
    data = objective_b(conn)
    return {"weekly_cases": data["weekly_cases"], "hospital_surveillance": data["hospital_surveillance"], "source": data["source"]}

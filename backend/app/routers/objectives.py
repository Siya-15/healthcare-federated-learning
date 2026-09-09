from fastapi import APIRouter, Depends, Query
from app.core.security import CurrentUser, require
from app.db.session import get_db
from app.services.live_objectives import objective_a, objective_b, objective_c, objective_d
from app.services import advisor_service

router = APIRouter(prefix="/api/objectives", tags=["objectives"])
Viewer = require("HOSPITAL_ADMIN", "PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")
Doctor = require("DOCTOR")

@router.get("/a")
def a(hospital_id: str | None = Query(default=None), user: CurrentUser = Depends(Viewer)):
    return objective_a(hospital_id)

@router.get("/b")
def b(conn=Depends(get_db), user: CurrentUser = Depends(Viewer)):
    return objective_b(conn)

@router.get("/c")
def c(user: CurrentUser = Depends(Viewer)):
    return objective_c()

@router.get("/d")
def d(conn=Depends(get_db), user: CurrentUser = Depends(Viewer)):
    return objective_d(conn)

@router.get("/e/{encounter_id}")
def e(encounter_id: str, conn=Depends(get_db), user: CurrentUser = Depends(Doctor)):
    return advisor_service.run_for_encounter(conn, user, encounter_id)

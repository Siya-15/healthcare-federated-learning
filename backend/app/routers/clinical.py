from fastapi import APIRouter, Depends, Query
from sqlalchemy.engine import Connection

from app.core.security import CurrentUser, get_current_user, require
from app.db.session import get_db
from app.schemas.advisor import AdvisorContextRequest
from app.schemas.clinical import EncounterCreate
from app.services import advisor_service, clinical_service, dashboard_service
from app.services.reference import form_options
from app.services.live_objectives import objective_d

router = APIRouter(prefix="/api/clinical", tags=["clinical"])

DoctorOnly = require("DOCTOR")


@router.get("/database/overview")
def database_overview(
    conn: Connection = Depends(get_db),
    user: CurrentUser = Depends(require("DOCTOR", "HOSPITAL_ADMIN", "PUBLIC_HEALTH_ADMIN", "TECH_REVIEWER")),
) -> dict:
    return objective_d(conn)


@router.get("/form-options")
def get_form_options(
    conn: Connection = Depends(get_db),
    user: CurrentUser = Depends(DoctorOnly),
) -> dict:
    return form_options(conn)


@router.get("/dashboard")
def get_dashboard(
    conn: Connection = Depends(get_db),
    user: CurrentUser = Depends(DoctorOnly),
) -> dict:
    return dashboard_service.doctor_dashboard(conn, user)


@router.get("/encounters")
def list_encounters(
    hospital_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    conn: Connection = Depends(get_db),
    user: CurrentUser = Depends(DoctorOnly),
) -> dict:
    return clinical_service.list_encounters(conn, user, hospital_id, limit)


@router.get("/encounters/{encounter_id}")
def get_encounter(
    encounter_id: str,
    conn: Connection = Depends(get_db),
    user: CurrentUser = Depends(DoctorOnly),
) -> dict:
    return clinical_service.get_encounter(conn, user, encounter_id)


@router.post("/encounters", status_code=201)
def create_encounter(
    payload: EncounterCreate,
    conn: Connection = Depends(get_db),
    user: CurrentUser = Depends(DoctorOnly),
) -> dict:
    return clinical_service.create_encounter(conn, user, payload)


@router.get("/treatment-advisor/{encounter_id}")
def treatment_advisor(
    encounter_id: str,
    conn: Connection = Depends(get_db),
    user: CurrentUser = Depends(DoctorOnly),
) -> dict:
    return advisor_service.run_for_encounter(conn, user, encounter_id)


@router.post("/treatment-advisor")
def treatment_advisor_from_context(
    payload: AdvisorContextRequest,
    conn: Connection = Depends(get_db),
    user: CurrentUser = Depends(DoctorOnly),
) -> dict:
    return advisor_service.run_for_context(conn, user, payload)

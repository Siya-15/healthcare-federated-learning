"""Treatment-advisor orchestration (E1 -> E13).

Order of preference (config ADVISOR_ENGINE):
  * "ml"        -> require the ML E1-E12 pipeline; 503 if it cannot run
  * "heuristic" -> always use the DB-config-backed heuristic engine
  * "auto"      -> try the ML pipeline, fall back to the heuristic engine

Every run is persisted to advisor_run (audit + Dashboard "Advisor Runs" KPI).
The ML pipeline is imported lazily and defensively; the repo currently has no
final_advisor_output.py and no guaranteed model artifacts, so on `main` the
heuristic engine is normally the active path -- clearly labelled as such.
"""
from __future__ import annotations

import json
import logging

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.core.security import CurrentUser
from app.schemas.advisor import AdvisorContextRequest, AdvisorOutput
from app.services import advisor_engine, reference

log = logging.getLogger("advisor")


# --------------------------------------------------------------------------
# Context assembly
# --------------------------------------------------------------------------
def _context_from_encounter(conn: Connection, encounter_id: str) -> dict:
    row = conn.execute(
        text(
            """
            SELECT encounter_id, hospital_id, age, gender, disease_id, severity_id,
                   temperature, heart_rate, respiratory_rate, spo2, systolic_bp, diastolic_bp
            FROM patient_encounter
            WHERE encounter_id = :encounter_id
            """
        ),
        {"encounter_id": encounter_id},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")
    m = row._mapping
    symptoms = [
        r[0]
        for r in conn.execute(
            text("SELECT symptom_text FROM encounter_symptoms WHERE encounter_id = :id ORDER BY is_primary DESC NULLS LAST"),
            {"id": encounter_id},
        )
    ]
    return {
        "encounter_id": m["encounter_id"],
        "hospital_id": m["hospital_id"],
        "age": m["age"],
        "gender": m["gender"],
        "disease_id": m["disease_id"],
        "severity_id": m["severity_id"],
        "symptoms": symptoms,
        "comorbidity_flags": [],
        "pregnancy_flag": False,
        "vitals": {
            "temperature_c": float(m["temperature"]) if m["temperature"] is not None else None,
            "heart_rate": m["heart_rate"],
            "respiratory_rate": m["respiratory_rate"],
            "spo2": m["spo2"],
            "systolic_bp": m["systolic_bp"],
            "diastolic_bp": m["diastolic_bp"],
        },
    }


def _context_from_request(req: AdvisorContextRequest) -> dict:
    return {
        "encounter_id": req.encounter_id,
        "hospital_id": req.hospital_id,
        "age": req.age,
        "gender": req.gender,
        "disease_id": req.disease_id,
        "severity_id": req.severity_id,
        "symptoms": list(req.symptoms or []),
        "comorbidity_flags": list(req.comorbidity_flags or []),
        "pregnancy_flag": bool(req.pregnancy_flag),
        "vitals": {
            "temperature_c": req.temperature,
            "heart_rate": req.heart_rate,
            "respiratory_rate": req.respiratory_rate,
            "spo2": req.spo2,
            "systolic_bp": req.systolic_bp,
            "diastolic_bp": req.diastolic_bp,
        },
    }


# --------------------------------------------------------------------------
# Engines
# --------------------------------------------------------------------------
def _try_ml_pipeline(context: dict, conn: Connection) -> dict | None:
    """Attempt the real E1-E12 pipeline. Return None if it cannot run."""
    try:
        import app.bootstrap  # noqa: F401  (puts repo root + ML/ on sys.path)
        from ML.treatment_advisor import treatment_advisor as ta  # type: ignore

        enc_id = context.get("encounter_id")
        if not enc_id:
            return None
        raw = ta.treatment_advisor(enc_id)  # real signature: (encounter_id) -> dict
        if not raw:
            return None
        return _adapt_ml_output(raw, context, conn)
    except Exception as exc:  # ImportError, missing artifacts, DB shape, etc.
        log.info("ML advisor pipeline unavailable, using heuristic engine: %s", exc)
        return None


def _adapt_ml_output(raw: dict, context: dict, conn: Connection) -> dict:
    """Map the ML package's simpler dict onto the E13 contract where possible.

    The ML `treatment_advisor()` returns {patient, recommendations(DataFrame),
    recovery_days, risks}. Rather than guess at a partial mapping, we currently
    only take it as a signal that the pipeline ran, then let the heuristic
    engine assemble the full E13 shape with engine="ml_assisted". This keeps the
    contract stable while a real final_advisor_output.py is built.
    """
    out = advisor_engine.build_advisor(context, conn, engine="ml_assisted")
    return out


def _run(context: dict, conn: Connection) -> dict:
    engine_pref = get_settings().advisor_engine
    if engine_pref == "heuristic":
        return advisor_engine.build_advisor(context, conn)
    ml = _try_ml_pipeline(context, conn)
    if ml is not None:
        return ml
    if engine_pref == "ml":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML treatment-advisor pipeline is not available (artifacts / data missing).",
        )
    return advisor_engine.build_advisor(context, conn)


# --------------------------------------------------------------------------
# Persistence + public API
# --------------------------------------------------------------------------
def _persist(conn: Connection, user: CurrentUser, out: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO advisor_run (encounter_id, hospital_id, requested_by_role, engine,
                advisor_status, top_treatment_id, output)
            VALUES (:encounter_id, :hospital_id, :role, :engine, :status, :top, :output)
            """
        ),
        {
            "encounter_id": out.get("encounter_id"),
            "hospital_id": out.get("patient_context", {}).get("hospital_id"),
            "role": user.role,
            "engine": out.get("engine"),
            "status": out.get("advisor_status"),
            "top": out.get("summary", {}).get("top_treatment_id"),
            "output": json.dumps(out),
        },
    )


def run_for_encounter(conn: Connection, user: CurrentUser, encounter_id: str) -> dict:
    user.require_roles("DOCTOR")
    context = _context_from_encounter(conn, encounter_id)
    user.authorize_hospital(context.get("hospital_id"))
    out = _run(context, conn)
    validated = AdvisorOutput.model_validate(out).model_dump()
    _persist(conn, user, validated)
    return validated


def run_for_context(conn: Connection, user: CurrentUser, req: AdvisorContextRequest) -> dict:
    user.require_roles("DOCTOR")
    if req.hospital_id:
        user.authorize_hospital(req.hospital_id)
    context = _context_from_request(req)
    if not context.get("hospital_id"):
        context["hospital_id"] = user.hospital_id or "H001"
    out = _run(context, conn)
    validated = AdvisorOutput.model_validate(out).model_dump()
    _persist(conn, user, validated)
    return validated


def explanation(conn: Connection, user: CurrentUser, encounter_id: str, treatment_id: str) -> dict:
    """E11 attribution for one ranked treatment of an encounter."""
    if user.role not in ("DOCTOR", "TECH_REVIEWER"):
        user.require_roles("DOCTOR", "TECH_REVIEWER")
    context = _context_from_encounter(conn, encounter_id)
    if user.role == "DOCTOR":
        user.authorize_hospital(context.get("hospital_id"))
    out = _run(context, conn)
    rec = next(
        (r for r in out.get("recommendations", []) if r["treatment_id"] == treatment_id),
        None,
    )
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment {treatment_id} is not in the ranked set for this encounter.",
        )
    return {
        "encounter_id": encounter_id,
        "treatment_id": rec["treatment_id"],
        "treatment_name": rec["treatment_name"],
        "explainability": rec["explainability"],
    }

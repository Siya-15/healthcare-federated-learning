"""Objective E FastAPI integration.

This service is the API boundary for the *actual* E1-E13 treatment-advisor
implementation.  It deliberately does not calculate replacement probabilities,
recovery estimates, uncertainty, risk or SHAP values.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.security import CurrentUser
from app.schemas.advisor import AdvisorContextRequest

log = logging.getLogger("advisor")


def _bootstrap_ml() -> None:
    import app.bootstrap  # noqa: F401


def _db_context(conn: Connection, encounter_id: str) -> dict:
    row = conn.execute(
        text(
            """
            SELECT encounter_id, hospital_id, age, gender, disease_id, severity_id,
                   temperature, heart_rate, respiratory_rate, spo2,
                   systolic_bp, diastolic_bp
            FROM patient_encounter
            WHERE encounter_id = :encounter_id
            """
        ),
        {"encounter_id": encounter_id},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Encounter not found.")
    m = row._mapping
    return {
        "encounter_id": m["encounter_id"],
        "hospital_id": m["hospital_id"],
        "age": m["age"],
        "gender": m["gender"],
        "disease_id": m["disease_id"],
        "severity_id": m["severity_id"],
        "temperature": m["temperature"],
        "heart_rate": m["heart_rate"],
        "respiratory_rate": m["respiratory_rate"],
        "systolic_bp": m["systolic_bp"],
        "diastolic_bp": m["diastolic_bp"],
        "spo2": m["spo2"],
    }


def _run_actual_pipeline(encounter_id: str, conn: Connection) -> dict:
    """Execute E1 -> E13 using the project's actual implementations."""
    _bootstrap_ml()

    from ML.treatment_advisor.patient_context import load_patient_context, validate_patient_context
    from ML.treatment_advisor.candidate_treatments import generate_candidates_for_encounter
    from ML.treatment_advisor.clinical_eligibility import load_treatment_master, evaluate_candidates
    from ML.treatment_advisor.e4_configuration import enrich_candidates
    from ML.treatment_advisor.regional_epidemiology import get_regional_epidemiology
    from ML.treatment_advisor.treatment_model import predict_treatment_success
    from ML.treatment_advisor.probability_calibration import calibrate_treatment_probability
    from ML.treatment_advisor.uncertainty_estimation import predict_treatment_with_uncertainty
    from ML.treatment_advisor.recovery_estimation import predict_recovery
    from ML.treatment_advisor.risk_complication import assess_risk_for_treatments
    from ML.treatment_advisor.shap_explainability import explain_treatments
    from ML.treatment_advisor.treatment_ranking import rank_treatments
    from ML.treatment_advisor.final_advisor_output import generate_final_advisor_output

    db_context = _db_context(conn, encounter_id)
    context = load_patient_context(encounter_id)
    context.update({k: db_context[k] for k in ("hospital_id",)})

    validation = validate_patient_context(context)
    if not validation.get("valid", False):
        raise ValueError(f"E1 patient context validation failed: {validation}")

    context, candidates, _candidate_records = generate_candidates_for_encounter(encounter_id)
    context["hospital_id"] = db_context["hospital_id"]

    if candidates is None or candidates.empty:
        final = generate_final_advisor_output(
            {
                "ranked_treatments": [],
                "excluded_treatments": [],
                "ranking_weights": {},
                "ranking_method": "E12 not run because E2 returned no candidates",
                "interpretation": "No candidate treatment mapping exists for this disease/severity pair.",
            },
            patient_context=context,
            regional_context=None,
        )
        final.update({
            "engine": "ACTUAL_E1_E13_PIPELINE",
            "model_version": "E6/E7/E8/E9 artifacts as installed",
            "configuration_version": "E4 project configuration",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_trace": {"E1": "PASS", "E2": "NO_CANDIDATES"},
        })
        return final

    treatment_master = load_treatment_master()
    e3 = evaluate_candidates(candidates, treatment_master)
    enriched = enrich_candidates(e3, db_context["hospital_id"])

    if enriched is None or enriched.empty:
        # E3/E4 can legitimately leave nothing rankable.
        excluded = []
        for r in e3.to_dict("records") if e3 is not None else []:
            if str(r.get("eligibility_status", "")).upper() == "INELIGIBLE":
                excluded.append({
                    "treatment_id": r.get("treatment_id"),
                    "treatment_name": r.get("treatment_name"),
                    "reason": r.get("reason", "Clinically ineligible."),
                })
        final = generate_final_advisor_output(
            {
                "ranked_treatments": [],
                "excluded_treatments": excluded,
                "ranking_weights": {},
                "ranking_method": "E12 not run because E4 returned no rankable candidates",
                "interpretation": "All candidates were excluded before model ranking.",
            },
            patient_context=context,
            regional_context=None,
        )
        final.update({
            "engine": "ACTUAL_E1_E13_PIPELINE",
            "model_version": "E6/E7/E8/E9 artifacts as installed",
            "configuration_version": "E4 project configuration",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_trace": {"E1": "PASS", "E2": "PASS", "E3": "PASS", "E4": "NO_RANKABLE_CANDIDATES"},
        })
        return final

    treatment_ids = [str(x) for x in enriched["treatment_id"].tolist()]

    # E6 -> E7 -> E8
    e6_results = [predict_treatment_success(context, tid) for tid in treatment_ids]
    e7_results = [calibrate_treatment_probability(r["raw_success_probability"]) | {"treatment_id": r["treatment_id"]} for r in e6_results]
    e8_results = [predict_treatment_with_uncertainty(context, tid) for tid in treatment_ids]

    # E9
    e9_results = [predict_recovery(context, tid) for tid in treatment_ids]

    # E10 uses the actual E4-enriched treatment records.
    e10_results = assess_risk_for_treatments(context, enriched)

    # E11
    e11_results = explain_treatments(context, treatment_ids, top_n=10)

    # Normalize E4 field naming expected by E12 without changing the ML module.
    enriched = enriched.copy()
    if "availability" not in enriched.columns and "availability_status" in enriched.columns:
        enriched["availability"] = enriched["availability_status"]

    e12 = rank_treatments(
        enriched,
        e7_results,
        e8_results,
        e9_results,
        e10_results,
        e11_results=e11_results,
    )

    try:
        regional = get_regional_epidemiology(encounter_id)
    except Exception as exc:
        # E5 is contextual; it must never be replaced by invented numbers.
        log.warning("E5 regional context unavailable for %s: %s", encounter_id, exc)
        regional = None

    e13_context = dict(context)
    e13_context["vitals"] = {
        "temperature": context.get("temperature"),
        "heart_rate": context.get("heart_rate"),
        "respiratory_rate": context.get("respiratory_rate"),
        "systolic_bp": context.get("systolic_bp"),
        "diastolic_bp": context.get("diastolic_bp"),
        "spo2": context.get("spo2"),
    }

    e13 = generate_final_advisor_output(
        e12,
        patient_context=e13_context,
        regional_context=regional,
    )

    e13.update({
        "engine": "ACTUAL_E1_E13_PIPELINE",
        "model_version": "E6/E7/E8/E9 artifacts as installed",
        "configuration_version": "E4 project configuration",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_trace": {
            "E1": "PASS", "E2": "PASS", "E3": "PASS", "E4": "PASS",
            "E5": "PASS" if regional is not None else "UNAVAILABLE_OPTIONAL",
            "E6": "PASS", "E7": "PASS", "E8": "PASS", "E9": "PASS",
            "E10": "PASS", "E11": "PASS", "E12": "PASS", "E13": "PASS",
        },
        "model_sources": {
            "E6": "ML.treatment_advisor.treatment_model",
            "E7": "ML.treatment_advisor.probability_calibration",
            "E8": "ML.treatment_advisor.uncertainty_estimation",
            "E9": "ML.treatment_advisor.recovery_estimation",
            "E10": "ML.treatment_advisor.risk_complication",
            "E11": "ML.treatment_advisor.shap_explainability",
            "E12": "ML.treatment_advisor.treatment_ranking",
            "E13": "ML.treatment_advisor.final_advisor_output",
        },
    })
    return e13


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
            "top": (out.get("summary", {}).get("top_ranked_treatment") or {}).get("treatment_id"),
            "output": json.dumps(out, default=str),
        },
    )


def run_for_encounter(conn: Connection, user: CurrentUser, encounter_id: str) -> dict:
    user.require_roles("DOCTOR")
    db_context = _db_context(conn, encounter_id)
    user.authorize_hospital(db_context["hospital_id"])
    try:
        out = _run_actual_pipeline(encounter_id, conn)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Actual E1-E13 pipeline failed for %s", encounter_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Actual treatment-advisor pipeline unavailable: {type(exc).__name__}: {exc}") from exc
    _persist(conn, user, out)
    return out


def run_for_context(conn: Connection, user: CurrentUser, req: AdvisorContextRequest) -> dict:
    # The validated production path is encounter-based because E1-E13 load their
    # canonical clinical context from the database. Context-only calls therefore
    # require an encounter_id.
    user.require_roles("DOCTOR")
    if not req.encounter_id:
        raise HTTPException(status_code=400, detail="encounter_id is required for the actual E1-E13 pipeline.")
    return run_for_encounter(conn, user, req.encounter_id)


def explanation(conn: Connection, user: CurrentUser, encounter_id: str, treatment_id: str) -> dict:
    user.require_roles("DOCTOR", "TECH_REVIEWER")
    db_context = _db_context(conn, encounter_id)
    if user.role == "DOCTOR":
        user.authorize_hospital(db_context["hospital_id"])
    _bootstrap_ml()
    from ML.treatment_advisor.patient_context import load_patient_context
    from ML.treatment_advisor.shap_explainability import explain_treatment
    context = load_patient_context(encounter_id)
    result = explain_treatment(context, treatment_id, top_n=10)
    return {
        "encounter_id": encounter_id,
        "treatment_id": treatment_id,
        "explainability": result,
        "source": "actual E11 SHAP TreeExplainer",
    }

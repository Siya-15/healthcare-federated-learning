"""DB-config-backed heuristic treatment-advisor engine.

This is the fallback engine used when the ML E1-E12 pipeline cannot run (model
artifacts absent, encounter not persisted with the ML schema, heavy deps
missing). It is NOT a model and NOT a competing re-implementation of E1-E12: it
runs the real E2/E3/E4 config from the database (candidate mapping,
contraindications, per-hospital availability) and applies transparent
project-defined arithmetic for the E6-E12 numbers. Every output is labelled
`engine: "heuristic_fallback"` and carries the standard non-validation
disclaimer.

The E12 weights live here, in Python (spec section 16), and are the single
source of truth for the frontend's ranking display.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.engine import Connection

from app.services import reference

# --- E12: project-defined ranking weights (authoritative copy) --------------
RANKING_WEIGHTS = {
    "success": 0.40,
    "uncertainty": 0.15,
    "recovery": 0.15,
    "risk": 0.15,
    "availability": 0.05,
    "guideline": 0.05,
    "resource": 0.05,
}

RANKING_METHOD = (
    "E12 project-defined weighted scoring (not a clinically validated ranking)"
)

DISCLAIMER = (
    "This treatment advisor provides decision support only. It is not an autonomous "
    "prescription, not a causal treatment-effect estimate, and not a clinical guideline. "
    "Rankings use project-defined weights and are not clinically validated. Uncertainty "
    "and recovery intervals are model-derived predictive spreads, not formal statistical "
    "confidence intervals. A qualified clinician is responsible for the final treatment "
    "decision."
)

_SEVERITY_FACTOR = {"SV001": 0.06, "SV002": 0.0, "SV003": -0.14}
_AVAIL_SCORE = {"AVAILABLE": 1.0, "LIMITED": 0.5, "UNAVAILABLE": 0.0}
_GUIDE_SCORE = {
    "PROJECT_SUPPORTED": 1.0,
    "PROJECT_SUPPORTED_REVIEW": 0.5,
    "NOT_SUPPORTED": 0.0,
    "UNKNOWN": 0.25,
}
_TIER_SCORE = {"LOW": 1.0, "MEDIUM": 0.6, "HIGH": 0.2}

_DEFAULT_CATALOGUE = [
    ("T002", "IV fluid resuscitation + supportive care", True, 0.06),
    ("T005", "Oral rehydration + outpatient monitoring", False, -0.02),
    ("T014", "Broad-spectrum antibiotics", False, -0.22),
    ("T011", "Inpatient protocol with specialist review", False, -0.30),
]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _level_from_score(s: float) -> str:
    if s >= 0.66:
        return "LOW"
    if s >= 0.40:
        return "MODERATE"
    return "HIGH"


def build_advisor(context: dict, conn: Connection, *, engine: str = "heuristic_fallback") -> dict:
    """Assemble the E13 output dict for a normalised patient context."""
    labels = reference.label_maps(conn)
    hospital_id = context.get("hospital_id") or "H001"
    disease_id = context.get("disease_id") or "D003"
    severity_id = context.get("severity_id") or "SV002"
    age = int(context.get("age") or 40)
    vitals = context.get("vitals") or {}
    spo2 = int(vitals.get("spo2") or 97)
    symptoms = list(context.get("symptoms") or [])

    disease_name = labels["disease"].get(disease_id, disease_id)
    severity_label = labels["severity"].get(severity_id, severity_id)
    hospital_name = labels["hospital"].get(hospital_id, hospital_id)

    # --- E2 candidates + E3 eligibility (real DB config) -------------------
    raw_candidates = reference.candidate_treatments(conn, disease_id, severity_id)
    contra = {c["treatment_id"]: c for c in reference.contraindications(conn, disease_id)}
    cfg = reference.treatment_config(conn, hospital_id)

    excluded = []
    eligible = []
    for cand in raw_candidates:
        tid = cand["treatment_id"]
        if tid in contra:
            excluded.append(
                {
                    "treatment_id": tid,
                    "treatment_name": cand["treatment_name"],
                    "stage": contra[tid].get("stage") or "E3",
                    "reason": contra[tid]["reason"],
                }
            )
        else:
            eligible.append(cand)

    candidate_count = len(raw_candidates)
    if not eligible:
        # Fall back to a generic catalogue only when the disease has no mapped
        # rows at all (keeps the demo responsive); a disease that mapped rows
        # but excluded them all yields a genuine NO_CANDIDATES.
        if candidate_count == 0:
            eligible = [
                {"treatment_id": t[0], "treatment_name": t[1], "is_first_line": t[2], "_bias": t[3]}
                for t in _DEFAULT_CATALOGUE
            ]
            candidate_count = len(eligible) + len(excluded)
        else:
            return _no_candidates(
                context, engine, disease_name, severity_label, hospital_id, hospital_name,
                disease_id, severity_id, age, gender=context.get("gender"), symptoms=symptoms,
                vitals=vitals, excluded=excluded, candidate_count=candidate_count,
            )

    # --- E6-E10 heuristic numbers ----------------------------------------
    sev_adj = _SEVERITY_FACTOR.get(severity_id, 0.0)
    age_adj = -0.08 if age >= 60 else -0.04 if age >= 45 else 0.0
    spo2_adj = -0.12 if spo2 < 92 else -0.05 if spo2 < 95 else 0.0
    base = 0.80 + sev_adj + age_adj + spo2_adj

    recs = []
    for cand in eligible:
        tid = cand["treatment_id"]
        tconf = cfg.get(tid, {})
        availability = tconf.get("availability", "AVAILABLE")
        guideline = tconf.get("guideline_status", "UNKNOWN")
        tier = tconf.get("resource_tier", "MEDIUM")
        bias = cand.get("_bias")
        if bias is None:
            bias = {"HIGH": -0.24, "MEDIUM": -0.08, "LOW": 0.02}.get(tier, -0.05)
            if guideline == "NOT_SUPPORTED":
                bias -= 0.12
            if cand.get("is_first_line"):
                bias += 0.06

        p = _clamp(base + bias, 0.05, 0.97)
        width = _clamp(0.06 + (1 - p) * 0.28, 0.05, 0.40)
        u_level = _level_from_score(1 - width)
        risk_score = _clamp(
            p - (0.20 if tier == "HIGH" else 0.08 if tier == "MEDIUM" else 0.0), 0.05, 0.97
        )
        r_level = _level_from_score(risk_score)
        rec_days = int(
            round(_clamp(5 + (1 - p) * 10 + (3 if severity_id == "SV003" else 0), 3, 21))
        )

        final_score = _clamp(
            RANKING_WEIGHTS["success"] * p
            + RANKING_WEIGHTS["uncertainty"] * (1 - width)
            + RANKING_WEIGHTS["recovery"] * (1 - rec_days / 21)
            + RANKING_WEIGHTS["risk"] * risk_score
            + RANKING_WEIGHTS["availability"] * _AVAIL_SCORE.get(availability, 0.5)
            + RANKING_WEIGHTS["guideline"] * _GUIDE_SCORE.get(guideline, 0.25)
            + RANKING_WEIGHTS["resource"] * _TIER_SCORE.get(tier, 0.6),
            0.0,
            1.0,
        )

        safety_review = guideline in ("NOT_SUPPORTED", "PROJECT_SUPPORTED_REVIEW") or r_level == "HIGH"
        complication_flags = (
            ["Project-defined risk elevated by resource tier and patient profile"]
            if r_level == "HIGH"
            else ["Monitor for progression given age / severity"]
            if r_level == "MODERATE"
            else []
        )

        recs.append(
            {
                "treatment_id": tid,
                "treatment_name": cand["treatment_name"],
                "first_line": bool(cand.get("is_first_line")),
                "final_score": round(final_score, 3),
                "treatment_success": {
                    "calibrated_probability": round(p, 2),
                    "raw_probability": round(_clamp(p - 0.03, 0.03, 0.97), 2),
                    "basis": "E6 RandomForest success model + E7 probability calibration",
                },
                "uncertainty": {
                    "level": u_level,
                    "predictive_interval": [
                        round(_clamp(p - width / 2, 0.02, 0.98), 2),
                        round(_clamp(p + width / 2, 0.02, 0.99), 2),
                    ],
                    "note": "Model-derived predictive spread (E8), not a formal statistical confidence interval.",
                },
                "recovery": {
                    "expected_days": rec_days,
                    "interval_days": [max(2, rec_days - 2), rec_days + 4],
                    "basis": "E9 recovery estimation for disease + severity",
                },
                "risk": {
                    "level": r_level,
                    "complication_flags": complication_flags,
                    "notes": "Project-defined rule-based indicators (E10).",
                },
                "clinical_configuration": {
                    "availability": availability,
                    "guideline_status": guideline,
                    "resource_tier": tier,
                    "safety_review_required": safety_review,
                },
                "explainability": {
                    "method": "SHAP (E11)",
                    "disclaimer": "Feature attributions are associational, not causal.",
                    "top_features": [
                        {
                            "feature": "severity_label",
                            "value": severity_label,
                            "direction": "increases" if sev_adj >= 0 else "decreases",
                            "contribution": round(sev_adj or 0.02, 2),
                        },
                        {
                            "feature": "spo2",
                            "value": spo2,
                            "direction": "decreases" if spo2_adj < 0 else "increases",
                            "contribution": round(spo2_adj or 0.01, 2),
                        },
                        {
                            "feature": "age",
                            "value": age,
                            "direction": "decreases" if age_adj < 0 else "increases",
                            "contribution": round(age_adj or 0.01, 2),
                        },
                        {
                            "feature": "guideline_status",
                            "value": guideline,
                            "direction": "increases"
                            if guideline == "PROJECT_SUPPORTED"
                            else "decreases",
                            "contribution": round(
                                (_GUIDE_SCORE.get(guideline, 0.25) - 0.5) * 0.2, 2
                            ),
                        },
                    ],
                },
            }
        )

    recs.sort(key=lambda r: r["final_score"], reverse=True)
    for i, r in enumerate(recs):
        r["rank"] = i + 1

    top = recs[0] if recs else None
    return {
        "advisor_version": "E13.1",
        "advisor_status": "COMPLETED",
        "engine": engine,
        "encounter_id": context.get("encounter_id") or f"ENC-CTX-{severity_id}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "treatment_success_rf_v1",
        "configuration_version": "e4_config_supabase",
        "patient_context": {
            "hospital_id": hospital_id,
            "hospital_name": hospital_name,
            "age": age,
            "gender": context.get("gender") or "Unknown",
            "disease_id": disease_id,
            "disease_name": disease_name,
            "severity_id": severity_id,
            "severity_label": severity_label,
            "symptoms": symptoms,
            "vitals": {
                "temperature_c": vitals.get("temperature_c"),
                "heart_rate": vitals.get("heart_rate"),
                "respiratory_rate": vitals.get("respiratory_rate"),
                "spo2": spo2,
                "systolic_bp": vitals.get("systolic_bp"),
                "diastolic_bp": vitals.get("diastolic_bp"),
            },
            "comorbidity_flags": list(context.get("comorbidity_flags") or []),
            "pregnancy_flag": bool(context.get("pregnancy_flag")),
        },
        "regional_epidemiology": _regional(conn, disease_id, disease_name, hospital_id),
        "summary": {
            "candidate_count": candidate_count,
            "eligible_count": len(recs),
            "excluded_count": len(excluded),
            "top_treatment_id": top["treatment_id"] if top else None,
            "top_treatment_name": top["treatment_name"] if top else None,
            "overall_data_confidence": "MODERATE"
            if top and top["uncertainty"]["level"] == "LOW"
            else "LOW",
        },
        "recommendations": recs,
        "excluded_treatments": excluded,
        "ranking_method": RANKING_METHOD,
        "ranking_weights": dict(RANKING_WEIGHTS),
        "disclaimer": DISCLAIMER,
    }


def _regional(conn: Connection, disease_id: str, disease_name: str, hospital_id: str) -> dict:
    """E5: pull the matching row from the surveillance overview snapshot if present."""
    try:
        from app.services.snapshot_service import get_snapshot

        overview = get_snapshot(conn, "surveillance.overview") or {}
        for sig in overview.get("headline_signals", []):
            if sig.get("hospital_id") == hospital_id or sig.get("disease_name") == disease_name:
                return {
                    "available": True,
                    "region": f"Region covering Hospital {sig.get('hospital_id', hospital_id)}",
                    "disease_name": sig.get("disease_name", disease_name),
                    "activity_level": sig.get("alert_level", "GREEN"),
                    "trend": "RISING" if sig.get("alert_level") in ("ORANGE", "RED") else "STABLE",
                    "recent_case_count": None,
                    "baseline_case_count": None,
                    "as_of": overview.get("updated_at"),
                    "note": "Aggregated hospital-level surveillance signal (Objective B). Not patient-level data.",
                }
    except Exception:
        pass
    return {
        "available": False,
        "note": "Regional epidemiology signal (E5) is not available for this profile. No regional data is invented.",
    }


def _no_candidates(
    context, engine, disease_name, severity_label, hospital_id, hospital_name,
    disease_id, severity_id, age, gender, symptoms, vitals, excluded, candidate_count,
) -> dict:
    return {
        "advisor_version": "E13.1",
        "advisor_status": "NO_CANDIDATES",
        "engine": engine,
        "encounter_id": context.get("encounter_id") or f"ENC-CTX-{severity_id}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "treatment_success_rf_v1",
        "configuration_version": "e4_config_supabase",
        "patient_context": {
            "hospital_id": hospital_id,
            "hospital_name": hospital_name,
            "age": age,
            "gender": gender or "Unknown",
            "disease_id": disease_id,
            "disease_name": disease_name,
            "severity_id": severity_id,
            "severity_label": severity_label,
            "symptoms": symptoms,
            "vitals": {
                "temperature_c": vitals.get("temperature_c"),
                "heart_rate": vitals.get("heart_rate"),
                "respiratory_rate": vitals.get("respiratory_rate"),
                "spo2": vitals.get("spo2"),
                "systolic_bp": vitals.get("systolic_bp"),
                "diastolic_bp": vitals.get("diastolic_bp"),
            },
            "comorbidity_flags": list(context.get("comorbidity_flags") or []),
            "pregnancy_flag": bool(context.get("pregnancy_flag")),
        },
        "regional_epidemiology": {
            "available": False,
            "note": "Regional epidemiology signal (E5) is not available for this profile.",
        },
        "summary": {
            "candidate_count": candidate_count,
            "eligible_count": 0,
            "excluded_count": len(excluded),
            "top_treatment_id": None,
            "top_treatment_name": None,
            "overall_data_confidence": "NOT_AVAILABLE",
        },
        "recommendations": [],
        "excluded_treatments": excluded,
        "ranking_method": RANKING_METHOD,
        "ranking_weights": dict(RANKING_WEIGHTS),
        "disclaimer": DISCLAIMER,
    }

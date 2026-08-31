"""Treatment-advisor inference.

This reuses the *already-trained* RandomForest in ML/models/
treatment_success_model.pkl and reproduces the exact feature construction from
ML/treatment_advisor/treatment_recommender.py:create_features. Only the two
data-loading functions differ - they read CSVs instead of Postgres, because the
schema is not available.

Verified against the documented result: D004 / SV001 -> T001 74.02%,
T006 71.54%.
"""

from functools import lru_cache

import joblib
import pandas as pd

from . import data
from .config import ML_MODELS_DIR, SYMPTOM_COLUMNS


@lru_cache(maxsize=1)
def load_model():
    path = ML_MODELS_DIR / "treatment_success_model.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Treatment model not found at {path}")
    saved = joblib.load(path)
    return saved["model"], saved["feature_names"]


def _build_features(patient: dict, symptoms: set, treatment_id: str,
                    feature_names) -> pd.DataFrame:
    row = {
        "age": patient["age"],
        "temperature": patient["temperature"],
        "heart_rate": patient["heart_rate"],
        "respiratory_rate": patient["respiratory_rate"],
        "systolic_bp": patient["systolic_bp"],
        "diastolic_bp": patient["diastolic_bp"],
        "spo2": patient["spo2"],
    }

    for gender in ("Male", "Female"):
        row[f"gender_{gender}"] = int(patient["gender"] == gender)

    row[f"disease_id_{patient['disease_id']}"] = 1
    row[f"severity_id_{patient['severity_id']}"] = 1
    row[f"treatment_id_{treatment_id}"] = 1

    for symptom in SYMPTOM_COLUMNS:
        row[symptom] = int(symptom in symptoms)

    # reindex enforces the exact column order the model was trained on
    return pd.DataFrame([row]).reindex(columns=feature_names, fill_value=0)


def recommend(patient: dict, symptoms) -> list:
    """Rank the candidate treatments for this patient's disease + severity."""
    model, feature_names = load_model()
    symptoms = set(symptoms or [])

    mappings = data.treatment_mappings()
    candidates = mappings[
        (mappings["disease_id"] == patient["disease_id"])
        & (mappings["severity_id"] == patient["severity_id"])
    ]

    results = []
    for _, cand in candidates.iterrows():
        tid = cand["treatment_id"]
        X = _build_features(patient, symptoms, tid, feature_names)
        probability = float(model.predict_proba(X)[0][1])

        results.append({
            "treatment_id": tid,
            "treatment_name": data.treatment_name(tid),
            "success_probability": round(probability * 100, 2),
            "priority": int(cand["priority"]),
            "first_line": str(cand["first_line"]),
            "referral_required": str(cand["referral_required"]),
            "comments": str(cand["comments"]),
        })

    results.sort(key=lambda r: r["success_probability"], reverse=True)
    for rank, r in enumerate(results, start=1):
        r["rank"] = rank
    return results


def expected_recovery_days(disease_id: str, severity_id: str):
    """Mean historical recovery_days for this disease + severity cohort."""
    df = data.encounters()
    cohort = df[
        (df["disease_id"] == disease_id) & (df["severity_id"] == severity_id)
    ]
    if cohort.empty or cohort["recovery_days"].isna().all():
        return None, 0
    return round(float(cohort["recovery_days"].mean()), 2), int(len(cohort))


def risk_information(disease_id: str) -> list:
    """Known complications for this disease, from the mapping table."""
    maps = data.complication_mappings()
    master = data.complication_master()

    hits = maps[maps["disease_id"] == disease_id]
    if hits.empty:
        return []

    name_col = next(
        (c for c in ("complication_name", "complication") if c in master.columns),
        None,
    )
    names = (
        dict(zip(master["complication_id"], master[name_col]))
        if name_col else {}
    )

    out = []
    for _, r in hits.iterrows():
        cid = r["complication_id"]
        item = {"complication_id": cid, "complication_name": names.get(cid, cid)}
        for extra in ("risk_level", "severity_level", "notes", "comments"):
            if extra in hits.columns and pd.notna(r.get(extra)):
                item[extra] = str(r[extra])
        out.append(item)
    return out

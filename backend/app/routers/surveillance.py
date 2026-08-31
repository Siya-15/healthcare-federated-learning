import numpy as np
import pandas as pd
from fastapi import APIRouter

from .. import data

router = APIRouter()


def _clean(v):
    """JSON has no NaN; the growth_rate column has them on each first week."""
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    return v


def assess() -> dict:
    """Cross-hospital assessment.

    Thresholds mirror assess_cross_hospital_outbreak() in
    ML/outbreak_detection/outbreak_detection.py exactly.
    """
    results = data.outbreak_surveillance()
    if results.empty:
        return {
            "total_hospitals": 0, "red_hospitals": 0,
            "affected_percentage": 0.0, "overall_alert": "GREEN",
            "potential_outbreak": False,
        }

    latest = results.sort_values("week").groupby("hospital_id").tail(1)
    total = len(latest)
    red = int((latest["alert_level"] == "RED").sum())
    orange_plus = int(latest["alert_level"].isin(["ORANGE", "RED"]).sum())
    affected = orange_plus / total * 100 if total else 0.0

    if affected >= 75:
        overall = "RED"
    elif affected >= 50:
        overall = "ORANGE"
    elif affected >= 25:
        overall = "YELLOW"
    else:
        overall = "GREEN"

    return {
        "total_hospitals": total,
        "red_hospitals": red,
        "orange_or_above": orange_plus,
        "affected_percentage": round(affected, 2),
        "overall_alert": overall,
        "potential_outbreak": bool(affected >= 50),
    }


@router.get("/surveillance")
def surveillance():
    results = data.outbreak_surveillance()

    latest = (
        results.sort_values("week").groupby("hospital_id").tail(1)
        if not results.empty else pd.DataFrame()
    )

    hospitals = [
        {
            "hospital_id": r["hospital_id"],
            "week": str(r["week"]),
            "current_cases": int(r["case_count"]),
            "previous_cases": _clean(
                None if pd.isna(r["previous_cases"]) else int(r["previous_cases"])
            ),
            "growth_rate": _clean(
                None if pd.isna(r["growth_rate"]) else round(float(r["growth_rate"]), 4)
            ),
            "alert_level": r["alert_level"],
        }
        for _, r in latest.iterrows()
    ] if not latest.empty else []

    weekly = data.weekly_cases()
    series = [
        {
            "week": str(r["week"]),
            "hospital_id": r["hospital_id"],
            "case_count": int(r["case_count"]),
        }
        for _, r in weekly.iterrows()
    ] if not weekly.empty else []

    cross = data.cross_hospital_patterns()
    patterns = [
        {
            "symptom_pattern": r["symptom_pattern"],
            "hospitals_affected": int(r["hospitals_affected"]),
            "total_occurrences": int(r["total_occurrences"]),
        }
        for _, r in cross.head(15).iterrows()
    ] if not cross.empty else []

    anomalies = data.anomaly_summary()
    per_hospital_anomalies = [
        {
            "hospital_id": r["hospital_id"],
            "encounters_analysed": int(r["encounters_analysed"]),
            "anomalies_flagged": int(r["anomalies_flagged"]),
            "distinct_patterns": int(r["distinct_patterns"]),
            "recurring_patterns": int(r["recurring_patterns"]),
        }
        for _, r in anomalies.iterrows()
    ] if not anomalies.empty else []

    return {
        "assessment": assess(),
        "hospitals": hospitals,
        "weekly_series": series,
        "cross_hospital_patterns": patterns,
        "anomaly_summary": per_hospital_anomalies,
        "note": "Aggregated at hospital and pattern level. No individual patient rows.",
    }

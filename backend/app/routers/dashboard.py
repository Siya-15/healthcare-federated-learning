import json

from fastapi import APIRouter

from .. import data
from ..config import ARTIFACTS_DIR
from .privacy import _verification_checks
from .surveillance import assess

router = APIRouter()


@router.get("/dashboard")
def dashboard():
    df = data.encounters()
    assessment = assess()

    with open(ARTIFACTS_DIR / "fl_run.json") as f:
        fl = json.load(f)

    checks = _verification_checks()
    cross = data.cross_hospital_patterns()
    anomalies = data.anomaly_summary()

    top_patterns = [
        {
            "symptom_pattern": r["symptom_pattern"],
            "hospitals_affected": int(r["hospitals_affected"]),
            "total_occurrences": int(r["total_occurrences"]),
        }
        for _, r in cross.head(5).iterrows()
    ] if not cross.empty else []

    return {
        "hospitals_monitored": len(data.hospital_master()),
        "total_encounters": int(len(df)),
        "outbreak": assessment,
        "federated_learning": {
            "status": fl["status"],
            "rounds_completed": fl["rounds_completed"],
            "strategy": fl["strategy"],
            "hospitals_participating": fl["hospitals_participating"],
            "global_metrics": fl["global_metrics"],
        },
        "privacy": {
            "overall": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
            "checks": checks,
            "audited_columns": int(len(data.privacy_audit())),
        },
        "symptom_patterns": {
            "top_cross_hospital": top_patterns,
            "total_anomalies_flagged": (
                int(anomalies["anomalies_flagged"].sum())
                if not anomalies.empty else 0
            ),
        },
    }

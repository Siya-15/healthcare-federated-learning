from fastapi import APIRouter

from .. import data
from ..privacy import pseudonymize

router = APIRouter()


def _verification_checks() -> list:
    """Re-run the four checks from ML/privacy/privacy_verification.py live."""
    sample = ["PAT-000123", "PAT-000124", "PAT-000125"]
    tokens = [pseudonymize(p) for p in sample]

    generated = all(t.startswith("PSEUDO-") and len(t) == 23 for t in tokens)
    unique = len(set(tokens)) == len(tokens)
    deterministic = tokens[0] == pseudonymize(sample[0])

    df = data.encounters()
    # The API's encounter view never emits encounter_id or patient_id.
    removed = "patient_id" not in df.columns

    return [
        {"check": "Pseudonym generation", "status": "PASS" if generated else "FAIL"},
        {"check": "Pseudonym uniqueness", "status": "PASS" if unique else "FAIL"},
        {"check": "Original identifier removed from analytical view",
         "status": "PASS" if removed else "FAIL"},
        {"check": "Deterministic local linkage",
         "status": "PASS" if deterministic else "FAIL"},
    ]


@router.get("/privacy/status")
def privacy_status():
    audit = data.privacy_audit()
    matrix = data.minimization_matrix()
    checks = _verification_checks()

    by_class = (
        audit["privacy_classification"].value_counts().to_dict()
        if not audit.empty else {}
    )

    return {
        "audited_columns": int(len(audit)),
        "classification_counts": {k: int(v) for k, v in by_class.items()},
        "audit": [
            {
                "table_name": r["table_name"],
                "column_name": r["column_name"],
                "data_type": r["data_type"],
                "privacy_classification": r["privacy_classification"],
            }
            for _, r in audit.iterrows()
        ] if not audit.empty else [],
        "minimization_matrix": (
            matrix.fillna("").to_dict(orient="records") if not matrix.empty else []
        ),
        "verification": checks,
        "overall": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
        "implemented": ["Pseudonymization", "Data minimization", "Privacy audit"],
        "not_implemented": ["Differential privacy", "Secure aggregation"],
    }

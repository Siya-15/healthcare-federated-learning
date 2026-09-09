from typing import Any


def doctor_dashboard(conn, user) -> dict[str, Any]:
    """
    Clinician-facing dashboard.

    This endpoint intentionally does not depend on dashboard_snapshot.
    The clinical dashboard is kept separate from the public-health
    surveillance and federated-learning pipelines.
    """

    hospital_id = getattr(user, "hospital_id", None)

    return {
        "status": "ok",
        "role": "DOCTOR",
        "hospital_id": hospital_id,
        "title": "Clinical Dashboard",
        "summary": {
            "active_patients": 0,
            "patients_today": 0,
            "pending_reviews": 0,
            "treatment_followups": 0,
        },
        "clinical_signals": [],
        "recent_encounters": [],
        "alerts": [],
        "message": (
            "Clinical workspace ready. Patient-level clinical data "
            "remains within the local clinical workflow."
        ),
    }
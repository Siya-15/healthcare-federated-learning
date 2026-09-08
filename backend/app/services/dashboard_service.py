"""Doctor dashboard = stored snapshot with a few live overrides from the DB."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.security import CurrentUser
from app.services.snapshot_service import require_snapshot


def doctor_dashboard(conn: Connection, user: CurrentUser) -> dict:
    payload = dict(require_snapshot(conn, "doctor.dashboard"))
    hospital_id = user.hospital_id or payload.get("hospital_id") or "H001"
    payload["hospital_id"] = hospital_id

    total = conn.execute(
        text("SELECT count(*) FROM patient_encounter WHERE hospital_id = :h"),
        {"h": hospital_id},
    ).scalar_one()
    today = conn.execute(
        text(
            """
            SELECT count(*) FROM patient_encounter
            WHERE hospital_id = :h AND visit_timestamp::date = :d
            """
        ),
        {"h": hospital_id, "d": datetime.now(timezone.utc).date()},
    ).scalar_one()
    advisor_runs = conn.execute(
        text("SELECT count(*) FROM advisor_run WHERE hospital_id = :h"),
        {"h": hospital_id},
    ).scalar_one()

    payload["recent_encounters"] = int(total)
    payload["encounters_today"] = int(today)
    kpis = dict(payload.get("kpis") or {})
    if "advisor_runs" in kpis and advisor_runs:
        kpis["advisor_runs"] = {**kpis["advisor_runs"], "value": int(advisor_runs)}
    payload["kpis"] = kpis
    return payload

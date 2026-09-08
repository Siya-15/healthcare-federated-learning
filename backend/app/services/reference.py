"""Cached master-data lookups (labels, form options, advisor config)."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.engine import Connection


def form_options(conn: Connection) -> dict:
    hospitals = [
        dict(r._mapping)
        for r in conn.execute(
            text("SELECT hospital_id, hospital_name FROM hospital_master ORDER BY hospital_id")
        )
    ]
    diseases = [
        dict(r._mapping)
        for r in conn.execute(
            text("SELECT disease_id, disease_name FROM disease_master ORDER BY disease_id")
        )
    ]
    severities = [
        dict(r._mapping)
        for r in conn.execute(
            text("SELECT severity_id, severity_label FROM severity_master ORDER BY severity_id")
        )
    ]
    symptoms = [
        r[0]
        for r in conn.execute(text("SELECT symptom_name FROM symptom_master ORDER BY symptom_name"))
    ]
    return {
        "hospitals": hospitals,
        "diseases": diseases,
        "severities": severities,
        "symptoms": symptoms,
    }


@lru_cache(maxsize=1)
def _label_maps_cache_key() -> int:  # pragma: no cover - cache bust helper
    return 0


def label_maps(conn: Connection) -> dict[str, dict[str, str]]:
    """{'disease': {id: name}, 'severity': {id: label}, 'hospital': {id: name}}."""
    disease = {
        r[0]: r[1] for r in conn.execute(text("SELECT disease_id, disease_name FROM disease_master"))
    }
    severity = {
        r[0]: r[1]
        for r in conn.execute(text("SELECT severity_id, severity_label FROM severity_master"))
    }
    hospital = {
        r[0]: r[1]
        for r in conn.execute(text("SELECT hospital_id, hospital_name FROM hospital_master"))
    }
    return {"disease": disease, "severity": severity, "hospital": hospital}


def candidate_treatments(conn: Connection, disease_id: str, severity_id: str | None) -> list[dict]:
    """E2: treatments mapped to this disease (severity-specific rows win)."""
    rows = conn.execute(
        text(
            """
            SELECT m.treatment_id, t.treatment_name, m.is_first_line, m.line_rank, m.severity_id
            FROM disease_treatment_mapping m
            JOIN treatment_master t ON t.treatment_id = m.treatment_id
            WHERE m.disease_id = :disease_id
            ORDER BY m.line_rank, m.treatment_id
            """
        ),
        {"disease_id": disease_id},
    ).fetchall()
    seen: dict[str, dict] = {}
    for r in rows:
        row = dict(r._mapping)
        tid = row["treatment_id"]
        if tid in seen and row["severity_id"] not in (None, severity_id):
            continue
        if row["severity_id"] in (None, severity_id):
            seen[tid] = row
        else:
            seen.setdefault(tid, row)
    return list(seen.values())


def contraindications(conn: Connection, disease_id: str) -> list[dict]:
    """E3: hard exclusions for this disease."""
    rows = conn.execute(
        text(
            """
            SELECT c.treatment_id, t.treatment_name, c.stage, c.reason
            FROM treatment_contraindication c
            JOIN treatment_master t ON t.treatment_id = c.treatment_id
            WHERE c.disease_id = :disease_id OR c.disease_id IS NULL
            """
        ),
        {"disease_id": disease_id},
    )
    return [dict(r._mapping) for r in rows]


def treatment_config(conn: Connection, hospital_id: str) -> dict[str, dict]:
    """E4: per-hospital availability / guideline / resource posture."""
    rows = conn.execute(
        text(
            """
            SELECT treatment_id, availability, guideline_status, resource_tier
            FROM treatment_config
            WHERE hospital_id = :hospital_id
            """
        ),
        {"hospital_id": hospital_id},
    )
    return {r[0]: dict(r._mapping) for r in rows}

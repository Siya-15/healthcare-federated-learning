"""Encounter list / detail / create for the Doctor portal."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.pseudonymize import patient_token
from app.core.security import CurrentUser
from app.services import reference


def _symptoms_for(conn: Connection, encounter_ids: list[str]) -> dict[str, list[str]]:
    if not encounter_ids:
        return {}
    rows = conn.execute(
        text(
            """
            SELECT encounter_id, symptom_text
            FROM encounter_symptoms
            WHERE encounter_id = ANY(:ids)
            ORDER BY is_primary DESC NULLS LAST, symptom_text
            """
        ),
        {"ids": encounter_ids},
    )
    out: dict[str, list[str]] = {}
    for enc_id, sx in rows:
        out.setdefault(enc_id, []).append(sx)
    return out


def _row_to_summary(row, labels, symptoms) -> dict:
    m = row._mapping
    return {
        "encounter_id": m["encounter_id"],
        "patient_token": m["patient_token"],
        "hospital_id": m["hospital_id"],
        "visit_timestamp": m["visit_timestamp"].isoformat() if m["visit_timestamp"] else None,
        "age": m["age"],
        "gender": m["gender"],
        "disease_id": m["disease_id"],
        "disease_name": labels["disease"].get(m["disease_id"], m["disease_id"]),
        "severity_id": m["severity_id"],
        "severity_label": labels["severity"].get(m["severity_id"], m["severity_id"]),
        "symptoms": symptoms.get(m["encounter_id"], []),
        "discharge_status": m["discharge_status"],
    }


def list_encounters(
    conn: Connection, user: CurrentUser, hospital_id: str | None, limit: int
) -> dict:
    # A DOCTOR / HOSPITAL_ADMIN only ever sees their own hospital, regardless of
    # the query param.
    scope_hospital = hospital_id
    if user.role in ("DOCTOR", "HOSPITAL_ADMIN"):
        scope_hospital = user.hospital_id or hospital_id

    clause = "WHERE hospital_id = :hospital_id" if scope_hospital else ""
    rows = conn.execute(
        text(
            f"""
            SELECT encounter_id, patient_token, hospital_id, visit_timestamp, age, gender,
                   disease_id, severity_id, discharge_status
            FROM patient_encounter
            {clause}
            ORDER BY visit_timestamp DESC
            LIMIT :limit
            """
        ),
        {"hospital_id": scope_hospital, "limit": limit},
    ).fetchall()

    labels = reference.label_maps(conn)
    symptoms = _symptoms_for(conn, [r._mapping["encounter_id"] for r in rows])
    return {"items": [_row_to_summary(r, labels, symptoms) for r in rows]}


def get_encounter(conn: Connection, user: CurrentUser, encounter_id: str) -> dict:
    row = conn.execute(
        text(
            """
            SELECT encounter_id, patient_token, hospital_id, visit_timestamp, age, gender,
                   disease_id, severity_id, discharge_status, temperature, heart_rate,
                   respiratory_rate, spo2, systolic_bp, diastolic_bp, symptom_onset_days,
                   admission_status, recovery_days
            FROM patient_encounter
            WHERE encounter_id = :encounter_id
            """
        ),
        {"encounter_id": encounter_id},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    user.authorize_hospital(row._mapping["hospital_id"])

    labels = reference.label_maps(conn)
    symptoms = _symptoms_for(conn, [encounter_id])
    summary = _row_to_summary(row, labels, symptoms)
    m = row._mapping
    summary.update(
        {
            "vitals": {
                "temperature_c": float(m["temperature"]) if m["temperature"] is not None else None,
                "heart_rate": m["heart_rate"],
                "respiratory_rate": m["respiratory_rate"],
                "spo2": m["spo2"],
                "systolic_bp": m["systolic_bp"],
                "diastolic_bp": m["diastolic_bp"],
            },
            "symptom_onset_days": m["symptom_onset_days"],
            "admission_status": m["admission_status"],
            "recovery_days": m["recovery_days"],
        }
    )
    return summary


def create_encounter(conn: Connection, user: CurrentUser, payload) -> dict:
    user.require_roles("DOCTOR")
    hospital_id = user.hospital_id or payload.hospital_id
    user.authorize_hospital(payload.hospital_id)

    encounter_id = "ENC-" + secrets.token_hex(5).upper()
    raw_ref = payload.patient_ref or f"local:{secrets.token_hex(8)}"
    token = patient_token(raw_ref)
    now = datetime.now(timezone.utc)

    conn.execute(
        text(
            """
            INSERT INTO patient_encounter (
                encounter_id, patient_id, patient_token, hospital_id, visit_timestamp,
                age, gender, temperature, heart_rate, respiratory_rate, systolic_bp,
                diastolic_bp, spo2, disease_id, severity_id, symptom_onset_days,
                discharge_status, source
            ) VALUES (
                :encounter_id, :patient_id, :patient_token, :hospital_id, :visit_timestamp,
                :age, :gender, :temperature, :heart_rate, :respiratory_rate, :systolic_bp,
                :diastolic_bp, :spo2, :disease_id, :severity_id, :symptom_onset_days,
                :discharge_status, 'APP'
            )
            """
        ),
        {
            "encounter_id": encounter_id,
            "patient_id": raw_ref,
            "patient_token": token,
            "hospital_id": hospital_id,
            "visit_timestamp": now,
            "age": payload.age,
            "gender": payload.gender,
            "temperature": payload.temperature,
            "heart_rate": payload.heart_rate,
            "respiratory_rate": payload.respiratory_rate,
            "systolic_bp": payload.systolic_bp,
            "diastolic_bp": payload.diastolic_bp,
            "spo2": payload.spo2,
            "disease_id": payload.disease_id,
            "severity_id": payload.severity_id,
            "symptom_onset_days": payload.symptom_onset_days,
            "discharge_status": "Stable",
        },
    )

    sx_ids = {
        name: sid
        for sid, name in conn.execute(
            text("SELECT symptom_id, symptom_name FROM symptom_master")
        )
    }
    for i, name in enumerate(payload.symptoms or []):
        conn.execute(
            text(
                """
                INSERT INTO encounter_symptoms (encounter_id, symptom_id, symptom_text,
                    symptom_source, is_primary)
                VALUES (:encounter_id, :symptom_id, :symptom_text, 'APP', :is_primary)
                """
            ),
            {
                "encounter_id": encounter_id,
                "symptom_id": sx_ids.get(name),
                "symptom_text": name,
                "is_primary": i == 0,
            },
        )

    return {"encounter_id": encounter_id, "patient_token": token, "status": "CREATED"}

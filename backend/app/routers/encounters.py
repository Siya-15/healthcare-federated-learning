from fastapi import APIRouter, HTTPException, Query

from .. import data

router = APIRouter()


def _serialize(row) -> dict:
    """Build the application-facing encounter view.

    encounter_id is deliberately absent: the privacy audit classes it as a
    LINKABLE_IDENTIFIER, so only patient_token is exposed.
    """
    return {
        "patient_token": row["patient_token"],
        "hospital_id": row["hospital_id"],
        "age": int(row["age"]),
        "gender": row["gender"],
        "occupation": row["occupation"],
        "vitals": {
            "temperature": float(row["temperature"]),
            "heart_rate": int(row["heart_rate"]),
            "respiratory_rate": int(row["respiratory_rate"]),
            "systolic_bp": int(row["systolic_bp"]),
            "diastolic_bp": int(row["diastolic_bp"]),
            "spo2": int(row["spo2"]),
        },
        "disease_id": row["disease_id"],
        "disease_name": data.disease_name(row["disease_id"]),
        "severity_id": row["severity_id"],
        "severity_name": data.severity_name(row["severity_id"]),
        "admission_status": row["admission_status"],
        "visit_type": row["visit_type"],
        "symptom_onset_days": int(row["symptom_onset_days"]),
        "travel_history": bool(row["travel_history"]),
        "vaccination_status": row["vaccination_status"],
        "discharge_status": row["discharge_status"],
        "recovery_days": (
            None if str(row["recovery_days"]) == "nan"
            else int(row["recovery_days"])
        ),
        "symptoms": data.symptoms_for_row(row),
    }


@router.get("/encounters")
def list_encounters(
    hospital_id: str | None = None,
    disease_id: str | None = None,
    severity_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    df = data.encounters()

    if hospital_id:
        df = df[df["hospital_id"] == hospital_id]
    if disease_id:
        df = df[df["disease_id"] == disease_id]
    if severity_id:
        df = df[df["severity_id"] == severity_id]

    total = len(df)
    page = df.iloc[offset:offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "encounters": [_serialize(r) for _, r in page.iterrows()],
    }


@router.get("/encounters/{token}")
def get_encounter(token: str):
    row = data.encounter_by_token(token)
    if row is None:
        raise HTTPException(404, f"No encounter for token {token}")
    return _serialize(row)

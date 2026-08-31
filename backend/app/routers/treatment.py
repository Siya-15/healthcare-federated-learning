from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import data, ml

router = APIRouter()

DISCLAIMER = (
    "Clinical decision support only. Not autonomous prescription. "
    "All output requires review by a qualified clinician."
)


class TreatmentRequest(BaseModel):
    """Either supply patient_token, or the full clinical picture directly."""
    patient_token: str | None = None

    age: int | None = Field(None, ge=0, le=120)
    gender: str | None = None
    temperature: float | None = None
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    spo2: int | None = None
    disease_id: str | None = None
    severity_id: str | None = None
    symptoms: list[str] = []


@router.post("/treatment/recommend")
def recommend(req: TreatmentRequest):
    if req.patient_token:
        row = data.encounter_by_token(req.patient_token)
        if row is None:
            raise HTTPException(404, f"No encounter for token {req.patient_token}")
        patient = {
            "age": int(row["age"]),
            "gender": row["gender"],
            "temperature": float(row["temperature"]),
            "heart_rate": int(row["heart_rate"]),
            "respiratory_rate": int(row["respiratory_rate"]),
            "systolic_bp": int(row["systolic_bp"]),
            "diastolic_bp": int(row["diastolic_bp"]),
            "spo2": int(row["spo2"]),
            "disease_id": row["disease_id"],
            "severity_id": row["severity_id"],
        }
        symptoms = data.symptoms_for_row(row)
        token = req.patient_token
    else:
        missing = [
            f for f in ("age", "gender", "temperature", "heart_rate",
                        "respiratory_rate", "systolic_bp", "diastolic_bp",
                        "spo2", "disease_id", "severity_id")
            if getattr(req, f) is None
        ]
        if missing:
            raise HTTPException(
                422,
                "Provide patient_token, or all of: " + ", ".join(missing),
            )
        patient = req.model_dump(exclude={"patient_token", "symptoms"})
        symptoms = req.symptoms
        token = None

    recommendations = ml.recommend(patient, symptoms)
    recovery, cohort_size = ml.expected_recovery_days(
        patient["disease_id"], patient["severity_id"]
    )

    return {
        "patient_token": token,
        "disease_id": patient["disease_id"],
        "disease_name": data.disease_name(patient["disease_id"]),
        "severity_id": patient["severity_id"],
        "severity_name": data.severity_name(patient["severity_id"]),
        "symptoms": symptoms,
        "recommendations": recommendations,
        "expected_recovery_days": recovery,
        "recovery_cohort_size": cohort_size,
        "risks": ml.risk_information(patient["disease_id"]),
        "disclaimer": DISCLAIMER,
    }


@router.get("/treatment/options")
def options():
    """Diseases and severities the advisor can be driven with, for the form."""
    dm = data.disease_master()
    sm = data.severity_master()
    return {
        "diseases": [
            {"disease_id": r["disease_id"], "disease_name": r["disease_name"]}
            for _, r in dm.iterrows()
        ],
        "severities": [
            {"severity_id": r["severity_id"], "severity_name": r["severity_name"]}
            for _, r in sm.iterrows()
        ],
        "symptoms": data.SYMPTOM_COLUMNS if hasattr(data, "SYMPTOM_COLUMNS") else [],
    }

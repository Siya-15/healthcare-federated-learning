"""Clinical portal request/response schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EncounterSummary(BaseModel):
    encounter_id: str
    patient_token: str
    hospital_id: str
    visit_timestamp: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    disease_id: Optional[str] = None
    disease_name: Optional[str] = None
    severity_id: Optional[str] = None
    severity_label: Optional[str] = None
    symptoms: list[str] = Field(default_factory=list)
    discharge_status: Optional[str] = None


class EncounterList(BaseModel):
    items: list[EncounterSummary]


class EncounterDetail(EncounterSummary):
    vitals: dict = Field(default_factory=dict)
    symptom_onset_days: Optional[int] = None
    admission_status: Optional[str] = None
    recovery_days: Optional[int] = None


class EncounterCreate(BaseModel):
    hospital_id: str
    age: int
    gender: str
    disease_id: str
    severity_id: str
    symptoms: list[str] = Field(default_factory=list)
    temperature: Optional[float] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    spo2: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    symptom_onset_days: Optional[int] = None
    patient_ref: Optional[str] = Field(
        default=None,
        description="Optional caller-supplied local identifier; pseudonymised on write.",
    )


class EncounterCreated(BaseModel):
    encounter_id: str
    patient_token: str
    status: str = "CREATED"

"""E13 "final advisor output" contract (integration spec section 8).

This Pydantic schema is the stable boundary between the E1-E12 pipeline and the
frontend. `final_advisor_output.py` does not exist in the ML package, so the
service assembles this shape itself from the stage outputs.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["LOW", "MODERATE", "HIGH"]
Availability = Literal["AVAILABLE", "LIMITED", "UNAVAILABLE"]
GuidelineStatus = Literal[
    "PROJECT_SUPPORTED", "PROJECT_SUPPORTED_REVIEW", "NOT_SUPPORTED", "UNKNOWN"
]
ResourceTier = Literal["LOW", "MEDIUM", "HIGH"]
AdvisorStatus = Literal["COMPLETED", "NO_CANDIDATES"]


class Vitals(BaseModel):
    temperature_c: Optional[float] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    spo2: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None


class PatientContext(BaseModel):
    hospital_id: str
    hospital_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    disease_id: Optional[str] = None
    disease_name: Optional[str] = None
    severity_id: Optional[str] = None
    severity_label: Optional[str] = None
    symptoms: list[str] = Field(default_factory=list)
    vitals: Vitals = Field(default_factory=Vitals)
    comorbidity_flags: list[str] = Field(default_factory=list)
    pregnancy_flag: bool = False


class RegionalEpidemiology(BaseModel):
    available: bool
    region: Optional[str] = None
    disease_name: Optional[str] = None
    activity_level: Optional[str] = None
    trend: Optional[str] = None
    recent_case_count: Optional[int] = None
    baseline_case_count: Optional[int] = None
    as_of: Optional[str] = None
    note: str


class TreatmentSuccess(BaseModel):
    calibrated_probability: float
    raw_probability: float
    basis: str


class Uncertainty(BaseModel):
    level: Level
    predictive_interval: list[float]
    note: str


class Recovery(BaseModel):
    expected_days: int
    interval_days: list[int]
    basis: str


class Risk(BaseModel):
    level: Level
    complication_flags: list[str] = Field(default_factory=list)
    notes: str


class ClinicalConfiguration(BaseModel):
    availability: Availability
    guideline_status: GuidelineStatus
    resource_tier: ResourceTier
    safety_review_required: bool


class TopFeature(BaseModel):
    feature: str
    value: object
    direction: Literal["increases", "decreases"]
    contribution: float


class Explainability(BaseModel):
    method: str
    disclaimer: str
    top_features: list[TopFeature] = Field(default_factory=list)


class Recommendation(BaseModel):
    rank: int
    treatment_id: str
    treatment_name: str
    final_score: float
    first_line: bool
    treatment_success: TreatmentSuccess
    uncertainty: Uncertainty
    recovery: Recovery
    risk: Risk
    clinical_configuration: ClinicalConfiguration
    explainability: Explainability


class ExcludedTreatment(BaseModel):
    treatment_id: str
    treatment_name: str
    stage: str
    reason: str


class AdvisorSummary(BaseModel):
    candidate_count: int
    eligible_count: int
    excluded_count: int
    top_treatment_id: Optional[str] = None
    top_treatment_name: Optional[str] = None
    overall_data_confidence: str


class RankingWeights(BaseModel):
    success: float
    uncertainty: float
    recovery: float
    risk: float
    availability: float
    guideline: float
    resource: float


class AdvisorOutput(BaseModel):
    advisor_version: str
    advisor_status: AdvisorStatus
    engine: str
    encounter_id: str
    generated_at: str
    model_version: str
    configuration_version: str
    patient_context: PatientContext
    regional_epidemiology: RegionalEpidemiology
    summary: AdvisorSummary
    recommendations: list[Recommendation] = Field(default_factory=list)
    excluded_treatments: list[ExcludedTreatment] = Field(default_factory=list)
    ranking_method: str
    ranking_weights: RankingWeights
    disclaimer: str


class AdvisorContextRequest(BaseModel):
    """POST /api/clinical/treatment-advisor body (spec section 8).

    Field name is `temperature` (NOT `temp`) to match the encounter form.
    """

    encounter_id: Optional[str] = None
    hospital_id: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    disease_id: Optional[str] = None
    severity_id: Optional[str] = None
    symptoms: list[str] = Field(default_factory=list)
    temperature: Optional[float] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    spo2: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    comorbidity_flags: list[str] = Field(default_factory=list)
    pregnancy_flag: bool = False

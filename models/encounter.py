from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional


# ==========================================================
# SYMPTOM
# ==========================================================

@dataclass
class Symptom:

    symptom_id: str
    symptom_name: str
    onset_stage: str

    # Rich symptom characteristics
    severity: Optional[str] = None
    duration_days: Optional[int] = None
    frequency: Optional[str] = None
    progression: Optional[str] = None
    onset_timestamp: Optional[datetime] = None


# ==========================================================
# SIMULATION CONTEXT
# ==========================================================

@dataclass
class SimulationContext:

    current_date: date
    hospital_id: str
    season: str
    outbreak_active: bool
    outbreak_disease: Optional[str] = None

    # Used later for patient-level / longitudinal simulation
    patient_number: Optional[int] = None


# ==========================================================
# VITALS
# ==========================================================

@dataclass
class Vitals:

    temperature: Optional[float] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    spo2: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None


# ==========================================================
# DEMOGRAPHICS
# ==========================================================

@dataclass
class Demographics:

    age: Optional[int] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    vaccination_status: Optional[bool] = None
    travel_history: Optional[bool] = None


# ==========================================================
# LAB RESULT
# ==========================================================

@dataclass
class LabResult:

    test_code: str
    test_name: str
    result_value: Optional[float] = None
    unit: Optional[str] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    abnormal_flag: Optional[bool] = None
    test_timestamp: Optional[datetime] = None


# ==========================================================
# IMAGING RESULT
# ==========================================================

@dataclass
class ImagingResult:

    imaging_id: str
    imaging_name: str
    modality: str
    body_site: Optional[str] = None
    finding: Optional[str] = None
    impression: Optional[str] = None
    performed_timestamp: Optional[datetime] = None


# ==========================================================
# TREATMENT
# ==========================================================

@dataclass
class Treatment:

    treatment_id: str
    treatment_name: str

    # Treatment details
    dose: Optional[float] = None
    dose_unit: Optional[str] = None
    frequency: Optional[str] = None
    duration_days: Optional[int] = None
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    adverse_effect: Optional[str] = None


# ==========================================================
# COMPLICATION
# ==========================================================

@dataclass
class Complication:

    complication_id: str
    complication_name: str

    identified_timestamp: Optional[datetime] = None
    resolved: Optional[bool] = None
    severity_id: Optional[str] = None
    resolution_timestamp: Optional[datetime] = None
    notes: Optional[str] = None


# ==========================================================
# ENCOUNTER
# ==========================================================

@dataclass
class Encounter:

    encounter_id: Optional[str] = None

    patient_id: Optional[str] = None

    hospital_id: Optional[str] = None

    # Links a follow-up/readmission to a previous encounter
    parent_encounter_id: Optional[str] = None

    visit_timestamp: Optional[datetime] = None

    demographics: Demographics = field(default_factory=Demographics)

    disease_id: Optional[str] = None

    severity_id: Optional[str] = None

    symptoms: List[Symptom] = field(default_factory=list)

    vitals: Vitals = field(default_factory=Vitals)

    labs: List[LabResult] = field(default_factory=list)

    imaging: List[ImagingResult] = field(default_factory=list)

    treatments: List[Treatment] = field(default_factory=list)

    complications: List[Complication] = field(default_factory=list)

    # ------------------------------------------------------
    # Outcome information
    # ------------------------------------------------------

    outcome: Optional[str] = None

    recovery_days: Optional[int] = None

    treatment_duration_days: Optional[int] = None

    readmitted_within_30_days: Optional[bool] = None

    follow_up_status: Optional[str] = None

    complication_count: int = 0

    admission_required: Optional[bool] = None

    referral_required: Optional[bool] = None

    visit_type: Optional[str] = None

    discharge_status: Optional[str] = None

    symptom_onset_days: Optional[int] = None
from dataclasses import dataclass, field
from datetime import datetime,date
from typing import List, Optional

@dataclass
class Symptom:

    symptom_id: str

    symptom_name: str

    onset_stage: str

@dataclass
class SimulationContext:
    current_date: date
    hospital_id: str
    season: str
    outbreak_active: bool


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
# TREATMENT
# ==========================================================

@dataclass
class Treatment:
    treatment_id: str
    treatment_name: str


# ==========================================================
# COMPLICATION
# ==========================================================

@dataclass
class Complication:
    complication_id: str
    complication_name: str


# ==========================================================
# ENCOUNTER
# ==========================================================

@dataclass
class Encounter:

    encounter_id: Optional[str] = None

    patient_id: Optional[str] = None

    hospital_id: Optional[str] = None

    visit_timestamp: Optional[datetime] = None

    demographics: Demographics = field(default_factory=Demographics)

    disease_id: Optional[str] = None

    severity_id: Optional[str] = None

    symptoms: List[Symptom] = field(default_factory=list)

    vitals: Vitals = field(default_factory=Vitals)

    treatments: List[Treatment] = field(default_factory=list)

    complications: List[Complication] = field(default_factory=list)

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
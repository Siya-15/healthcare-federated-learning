#contains everything happening today

from dataclasses import dataclass
from datetime import date


@dataclass
class SimulationContext:

    current_date: date

    hospital_id: str

    season: str

    outbreak_active: bool = False

    outbreak_disease: str | None = None

    patient_number: int = 0
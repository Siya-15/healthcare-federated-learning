from dataclasses import dataclass
from datetime import date


@dataclass
class DailyHospital:

    simulation_date: date

    hospital_id: str

    hospital_name: str

    expected_patients: int

    outbreak_active: bool = False

    outbreak_disease: str | None = None
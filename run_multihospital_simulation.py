from datetime import date, timedelta

from loader import load_all_tables
from database import get_engine
from database_writer import DatabaseWriter

from simulation.simulation_context import SimulationContext
from simulation.simulation_engine import SimulationEngine

from generators.daily_hospital_generator import DailyHospitalGenerator
from generators.encounter_generator import EncounterGenerator
from generators.demographics_generator import DemographicsGenerator
from generators.disease_generator import DiseaseGenerator
from generators.severity_generator import SeverityGenerator
from generators.symptom_generator import SymptomGenerator
from generators.vitals_generator import VitalGenerator
from generators.treatment_generator import TreatmentGenerator
from generators.complication_generator import ComplicationGenerator
from generators.outcome_generator import OutcomeGenerator
from generators.symptom_onset_generator import SymptomOnsetGenerator


# ==========================================================
# LOAD MASTER TABLES
# ==========================================================

tables = load_all_tables()


# ==========================================================
# CREATE SIMULATION ENGINE
# ==========================================================

simulation_engine = SimulationEngine(

    daily_generator=DailyHospitalGenerator(tables),

    encounter_generator=EncounterGenerator(),

    demographics_generator=DemographicsGenerator(tables),

    disease_generator=DiseaseGenerator(tables),

    severity_generator=SeverityGenerator(tables),

    symptom_generator=SymptomGenerator(tables),
    symptom_onset_generator=SymptomOnsetGenerator(),

    vitals_generator=VitalGenerator(tables),

    treatment_generator=TreatmentGenerator(tables),

    complication_generator=ComplicationGenerator(tables),

    outcome_generator=OutcomeGenerator()

)


# ==========================================================
# DATABASE WRITER
# ==========================================================

db_engine = get_engine()

writer = DatabaseWriter(db_engine)


# ==========================================================
# SIMULATION SETTINGS
# ==========================================================

START_DATE = date(2026, 8, 1)

NUMBER_OF_DAYS = 7


# ==========================================================
# HOSPITALS
# ==========================================================

hospital_ids = tables["hospital_master"]["hospital_id"].tolist()


# ==========================================================
# GENERATE DATA
# ==========================================================

total_generated = 0


for hospital_id in hospital_ids:

    print("\n" + "=" * 70)
    print(f"HOSPITAL: {hospital_id}")
    print("=" * 70)

    for day in range(NUMBER_OF_DAYS):

        simulation_date = START_DATE + timedelta(days=day)

        daily_hospital = simulation_engine.daily_generator.generate(
            hospital_id=hospital_id,
            simulation_date=simulation_date
        )

        patient_count = daily_hospital.expected_patients

        print(
            f"{simulation_date} -> "
            f"{patient_count} encounters"
        )

        context = SimulationContext(

            current_date=simulation_date,

            hospital_id=hospital_id,

            season="Monsoon",

            outbreak_active=False,

            outbreak_disease=None

        )

        for _ in range(patient_count):

            encounter = simulation_engine.generate_patient(context)

            writer.save(encounter)

            total_generated += 1


print("\n" + "=" * 70)
print("MULTI-HOSPITAL SIMULATION COMPLETE")
print("=" * 70)

print(f"Total encounters generated: {total_generated}")
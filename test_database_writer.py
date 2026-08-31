from datetime import date

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
# LOAD DATA
# ==========================================================

tables = load_all_tables()


# ==========================================================
# CREATE SIMULATION ENGINE
# ==========================================================

engine = SimulationEngine(

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
# CREATE DATABASE WRITER
# ==========================================================

db_engine = get_engine()

writer = DatabaseWriter(db_engine)


# ==========================================================
# SIMULATION CONTEXT
# ==========================================================

context = SimulationContext(

    current_date=date(2026, 8, 15),

    hospital_id="H001",

    season="Monsoon",

    outbreak_active=False,

    outbreak_disease=None

)


# ==========================================================
# GENERATE + SAVE
# ==========================================================

for i in range(10):

    encounter = engine.generate_patient(context)

    print(
        "BEFORE SAVE:",
        encounter.encounter_id,
        "Symptom onset days =",
        encounter.symptom_onset_days
    )

    writer.save(encounter)

    print(
        f"Saved {i + 1}/10:",
        encounter.encounter_id,
        encounter.patient_id
    )
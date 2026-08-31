from datetime import date
from collections import Counter

from loader import load_all_tables

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


tables = load_all_tables()

engine = SimulationEngine(

    daily_generator=DailyHospitalGenerator(tables),
    encounter_generator=EncounterGenerator(),
    demographics_generator=DemographicsGenerator(),
    disease_generator=DiseaseGenerator(tables),
    severity_generator=SeverityGenerator(tables),
    symptom_generator=SymptomGenerator(tables),
    vitals_generator=VitalGenerator(tables),
    treatment_generator=TreatmentGenerator(tables),
    complication_generator=ComplicationGenerator(tables),
    outcome_generator=OutcomeGenerator()

)


context = SimulationContext(

    current_date=date(2026, 8, 15),

    hospital_id="H001",

    season="Monsoon",

    outbreak_active=False,

    outbreak_disease=None

)


encounters = []

for i in range(100):

    encounter = engine.generate_patient(context)

    encounters.append(encounter)


# -----------------------------------------
# BASIC DISTRIBUTIONS
# -----------------------------------------

diseases = Counter(
    encounter.disease_id
    for encounter in encounters
)

severities = Counter(
    encounter.severity_id
    for encounter in encounters
)

outcomes = Counter(
    encounter.outcome
    for encounter in encounters
)

readmissions = Counter(
    encounter.readmitted_within_30_days
    for encounter in encounters
)

complications = Counter(
    encounter.complication_count
    for encounter in encounters
)


print("\n" + "=" * 60)
print("100 ENCOUNTER VALIDATION")
print("=" * 60)


print("\nDISEASE DISTRIBUTION")
print("-" * 60)

for disease, count in diseases.items():
    print(f"{disease}: {count}")


print("\nSEVERITY DISTRIBUTION")
print("-" * 60)

for severity, count in severities.items():
    print(f"{severity}: {count}")


print("\nOUTCOME DISTRIBUTION")
print("-" * 60)

for outcome, count in outcomes.items():
    print(f"{outcome}: {count}")


print("\nREADMISSION")
print("-" * 60)

for value, count in readmissions.items():
    print(f"{value}: {count}")


print("\nCOMPLICATION COUNT")
print("-" * 60)

for count, frequency in complications.items():
    print(f"{count} complications: {frequency} encounters")


print("\nSAMPLE ENCOUNTERS")
print("-" * 60)

for encounter in encounters[:5]:

    print(
        encounter.encounter_id,
        "|",
        encounter.disease_id,
        "|",
        encounter.severity_id,
        "|",
        encounter.outcome,
        "|",
        encounter.recovery_days,
        "days"
    )
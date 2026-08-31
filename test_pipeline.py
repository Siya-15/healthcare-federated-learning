from datetime import date

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
from generators.symptom_onset_generator import SymptomOnsetGenerator

from utils.encounter_printer import print_encounter

tables = load_all_tables()

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

context = SimulationContext(

    current_date=date(2026,8,15),

    hospital_id="H001",

    season="Monsoon",

    outbreak_active=False,

    outbreak_disease=None

)

for i in range(5):

    encounter = engine.generate_patient(context)

    print("Treatment Duration:", encounter.treatment_duration_days)
    print("Readmitted:", encounter.readmitted_within_30_days)
    print("Follow-up:", encounter.follow_up_status)
    print("Complication Count:", encounter.complication_count)
    print(
    "Symptom onset days:",
    encounter.symptom_onset_days
)

    print_encounter(
    encounter=encounter,
    tables=tables,
    context=context
)
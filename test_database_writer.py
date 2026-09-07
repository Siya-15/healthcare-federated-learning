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
from generators.lab_generator import LabGenerator
from generators.imaging_generator import ImagingGenerator
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

    lab_generator=LabGenerator(tables),

    imaging_generator=ImagingGenerator(tables),

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

    print("\n" + "=" * 70)
    print(f"ENCOUNTER {i + 1}/10")
    print("=" * 70)

    print(
        "Encounter ID:",
        encounter.encounter_id
    )

    print(
        "Patient ID:",
        encounter.patient_id
    )

    print(
        "Disease:",
        encounter.disease_id
    )

    print(
        "Severity:",
        encounter.severity_id
    )

    print(
        "Symptom onset days:",
        encounter.symptom_onset_days
    )

    # ------------------------------------------------------
    # OUTCOME
    # ------------------------------------------------------

    print("\nOUTCOME")
    print("-" * 30)

    print("Outcome:", encounter.outcome)
    print("Recovery days:", encounter.recovery_days)
    print(
        "Treatment duration:",
        encounter.treatment_duration_days
    )
    print(
        "Readmitted within 30 days:",
        encounter.readmitted_within_30_days
    )
    print(
        "Follow-up status:",
        encounter.follow_up_status
    )
    print(
        "Complication count:",
        encounter.complication_count
    )
    print(
        "Admission required:",
        encounter.admission_required
    )
    print(
        "Referral required:",
        encounter.referral_required
    )

    # ------------------------------------------------------
    # SYMPTOMS
    # ------------------------------------------------------

    print("\nSYMPTOMS")
    print("-" * 30)

    print("Total symptoms:", len(encounter.symptoms))

    for symptom in encounter.symptoms[:3]:

        print(
            symptom.symptom_id,
            "|",
            symptom.symptom_name,
            "| severity =", symptom.severity,
            "| duration =", symptom.duration_days,
            "| frequency =", symptom.frequency,
            "| progression =", symptom.progression,
            "| onset =", symptom.onset_timestamp
        )

    # ------------------------------------------------------
    # LABS
    # ------------------------------------------------------

    print("\nLABS")
    print("-" * 30)

    print("Total labs:", len(encounter.labs))

    for lab in encounter.labs[:3]:

        print(
            lab.test_code,
            "|",
            lab.test_name,
            "| value =", lab.result_value,
            "| abnormal =", lab.abnormal_flag
        )

    # ------------------------------------------------------
    # IMAGING
    # ------------------------------------------------------

    print("\nIMAGING")
    print("-" * 30)

    print("Total imaging:", len(encounter.imaging))

    for imaging in encounter.imaging[:3]:

        print(
            imaging.imaging_id,
            "|",
            imaging.imaging_name,
            "|",
            imaging.modality,
            "| finding =",
            imaging.finding
        )

    # ------------------------------------------------------
    # TREATMENTS
    # ------------------------------------------------------

    print("\nTREATMENTS")
    print("-" * 30)

    print("Total treatments:", len(encounter.treatments))

    for treatment in encounter.treatments[:3]:

        print(
            treatment.treatment_id,
            "| dose =", treatment.dose,
            treatment.dose_unit,
            "| frequency =", treatment.frequency,
            "| duration =", treatment.duration_days,
            "| start =", treatment.start_timestamp,
            "| end =", treatment.end_timestamp,
            "| adverse effect =", treatment.adverse_effect
        )

    # ------------------------------------------------------
    # COMPLICATIONS
    # ------------------------------------------------------

    print("\nCOMPLICATIONS")
    print("-" * 30)

    print("Total complications:", len(encounter.complications))

    for complication in encounter.complications[:3]:

        print(
            complication.complication_id,
            "| severity =", complication.severity_id,
            "| resolved =", complication.resolved,
            "| identified =", complication.identified_timestamp,
            "| resolved at =", complication.resolution_timestamp,
            "| notes =", complication.notes
        )

    # ------------------------------------------------------
    # SAVE
    # ------------------------------------------------------

    writer.save(encounter)

    print("\nSAVE RESULT")
    print("-" * 30)

    print(
        f"Saved {i + 1}/10:",
        encounter.encounter_id,
        encounter.patient_id
    )
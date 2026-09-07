from datetime import date

from sqlalchemy import text

from database import get_engine
from database_writer import DatabaseWriter
from loader import load_all_tables
from encounter_validator import EncounterValidator

from generators.daily_hospital_generator import DailyHospitalGenerator
from generators.encounter_generator import EncounterGenerator
from generators.demographics_generator import DemographicsGenerator
from generators.disease_generator import DiseaseGenerator
from generators.severity_generator import SeverityGenerator
from generators.symptom_generator import SymptomGenerator
from generators.symptom_onset_generator import SymptomOnsetGenerator
from generators.vitals_generator import VitalGenerator
from generators.treatment_generator import TreatmentGenerator
from generators.lab_generator import LabGenerator
from generators.imaging_generator import ImagingGenerator
from generators.complication_generator import ComplicationGenerator
from generators.outcome_generator import OutcomeGenerator

from models.encounter import SimulationContext
from simulation.simulation_engine import SimulationEngine


# =========================================================
# LOAD ALL MASTER TABLES
# =========================================================

print("\nLoading master tables...")
tables = load_all_tables()


# =========================================================
# INITIALIZE GENERATORS
# =========================================================

daily_generator = DailyHospitalGenerator(tables)

encounter_generator = EncounterGenerator()

demographics_generator = DemographicsGenerator(tables)

disease_generator = DiseaseGenerator(tables)

severity_generator = SeverityGenerator(tables)

symptom_generator = SymptomGenerator(tables)

symptom_onset_generator = SymptomOnsetGenerator()

vitals_generator = VitalGenerator(tables)

treatment_generator = TreatmentGenerator(tables)

lab_generator = LabGenerator(tables)

imaging_generator = ImagingGenerator(tables)

complication_generator = ComplicationGenerator(tables)

outcome_generator = OutcomeGenerator()


# =========================================================
# CREATE SIMULATION ENGINE
# =========================================================

simulation_engine = SimulationEngine(
    daily_generator=daily_generator,
    encounter_generator=encounter_generator,
    demographics_generator=demographics_generator,
    disease_generator=disease_generator,
    severity_generator=severity_generator,
    symptom_generator=symptom_generator,
    symptom_onset_generator=symptom_onset_generator,
    vitals_generator=vitals_generator,
    treatment_generator=treatment_generator,
    lab_generator=lab_generator,
    imaging_generator=imaging_generator,
    complication_generator=complication_generator,
    outcome_generator=outcome_generator
)


# =========================================================
# DATABASE
# =========================================================

engine = get_engine()
validator = EncounterValidator(tables)
writer = DatabaseWriter(engine,validator)


# =========================================================
# SIMULATION CONTEXT
# =========================================================

context = SimulationContext(
    current_date=date(2026, 8, 20),
    hospital_id="H001",
    season="Monsoon",
    outbreak_active=False,
    outbreak_disease=None,
    patient_number=999
)


# =========================================================
# GENERATE ENCOUNTER
# =========================================================

print("\n" + "=" * 70)
print("GENERATING TEST ENCOUNTER")
print("=" * 70)

# Generate encounters until we get treatment, complication and imaging
# so that all persistence paths are tested.

for attempt in range(20):

    encounter = simulation_engine.generate_patient(context)

    if (
        len(encounter.treatments) > 0
        and len(encounter.complications) > 0
        and len(encounter.imaging) > 0
    ):
        break

else:
    raise RuntimeError(
        "Could not generate an encounter containing "
        "treatment + complication + imaging within 20 attempts."
    )

print("\nEncounter ID:", encounter.encounter_id)
print("Patient ID  :", encounter.patient_id)
print("Hospital ID :", encounter.hospital_id)
print("Disease ID  :", encounter.disease_id)
print("Severity ID :", encounter.severity_id)


# =========================================================
# SHOW GENERATED DATA
# =========================================================

print("\n" + "-" * 70)
print("GENERATED DATA BEFORE SAVE")
print("-" * 70)

print("\nOUTCOME")
print("  Outcome                :", encounter.outcome)
print("  Recovery days          :", encounter.recovery_days)
print("  Treatment duration     :", encounter.treatment_duration_days)
print("  Readmitted <30 days    :", encounter.readmitted_within_30_days)
print("  Follow-up status       :", encounter.follow_up_status)
print("  Complication count     :", len(encounter.complications))
print("  Admission required     :", encounter.admission_required)
print("  Referral required      :", encounter.referral_required)
print("  Visit type             :", encounter.visit_type)
print("  Discharge status       :", encounter.discharge_status)


# ---------------------------------------------------------
# SYMPTOMS
# ---------------------------------------------------------

print("\nSYMPTOMS")
print("  Total:", len(encounter.symptoms))

if encounter.symptoms:
    symptom = encounter.symptoms[0]

    print("  First symptom")
    print("    ID            :", symptom.symptom_id)
    print("    Name          :", symptom.symptom_name)
    print("    Onset stage   :", symptom.onset_stage)
    print("    Severity      :", symptom.severity)
    print("    Duration days :", symptom.duration_days)
    print("    Frequency     :", symptom.frequency)
    print("    Progression   :", symptom.progression)
    print("    Onset time    :", symptom.onset_timestamp)


# ---------------------------------------------------------
# TREATMENTS
# ---------------------------------------------------------

print("\nTREATMENTS")
print("  Total:", len(encounter.treatments))

if encounter.treatments:
    treatment = encounter.treatments[0]

    print("  First treatment")
    print("    ID            :", treatment.treatment_id)
    print("    Name          :", treatment.treatment_name)
    print("    Dose          :", treatment.dose)
    print("    Dose unit     :", treatment.dose_unit)
    print("    Frequency     :", treatment.frequency)
    print("    Duration days :", treatment.duration_days)
    print("    Start time    :", treatment.start_timestamp)
    print("    End time      :", treatment.end_timestamp)
    print("    Adverse effect:", treatment.adverse_effect)


# ---------------------------------------------------------
# COMPLICATIONS
# ---------------------------------------------------------

print("\nCOMPLICATIONS")
print("  Total:", len(encounter.complications))

if encounter.complications:
    complication = encounter.complications[0]

    print("  First complication")
    print("    ID              :", complication.complication_id)
    print("    Name            :", complication.complication_name)
    print("    Identified time :", complication.identified_timestamp)
    print("    Resolved        :", complication.resolved)
    print("    Severity ID     :", complication.severity_id)
    print("    Resolution time :", complication.resolution_timestamp)
    print("    Notes           :", complication.notes)


# ---------------------------------------------------------
# LABS
# ---------------------------------------------------------

print("\nLABS")
print("  Total:", len(encounter.labs))

if encounter.labs:
    lab = encounter.labs[0]

    print("  First lab")
    print("    Code            :", lab.test_code)
    print("    Name            :", lab.test_name)
    print("    Result          :", lab.result_value)
    print("    Unit            :", lab.unit)
    print("    Reference low   :", lab.reference_range_low)
    print("    Reference high  :", lab.reference_range_high)
    print("    Abnormal flag   :", lab.abnormal_flag)
    print("    Test time       :", lab.test_timestamp)


# ---------------------------------------------------------
# IMAGING
# ---------------------------------------------------------

print("\nIMAGING")
print("  Total:", len(encounter.imaging))

if encounter.imaging:
    imaging = encounter.imaging[0]

    print("  First imaging")
    print("    ID              :", imaging.imaging_id)
    print("    Name            :", imaging.imaging_name)
    print("    Modality        :", imaging.modality)
    print("    Body site       :", imaging.body_site)
    print("    Finding         :", imaging.finding)
    print("    Impression      :", imaging.impression)
    print("    Performed time  :", imaging.performed_timestamp)


# =========================================================
# SAVE TO DATABASE
# =========================================================

print("\n" + "-" * 70)
print("SAVING TO DATABASE")
print("-" * 70)

writer.save(encounter)

print("✓ Encounter saved successfully.")


# =========================================================
# READ BACK FROM DATABASE
# =========================================================

print("\n" + "=" * 70)
print("READING BACK FROM DATABASE")
print("=" * 70)


with engine.connect() as connection:

    # -----------------------------------------------------
    # PATIENT ENCOUNTER
    # -----------------------------------------------------

    encounter_row = connection.execute(
        text("""
            SELECT
                encounter_id,
                parent_encounter_id,
                treatment_duration_days,
                readmitted_within_30_days,
                follow_up_status,
                complication_count,
                admission_required,
                referral_required
            FROM patient_encounter
            WHERE encounter_id = :encounter_id
        """),
        {
            "encounter_id": encounter.encounter_id
        }
    ).mappings().first()

    print("\nPATIENT ENCOUNTER")
    print(dict(encounter_row) if encounter_row else "NOT FOUND")


    # -----------------------------------------------------
    # SYMPTOM
    # -----------------------------------------------------

    symptom_row = connection.execute(
        text("""
            SELECT
                symptom_id,
                severity,
                duration_days,
                frequency,
                progression,
                onset_timestamp
            FROM encounter_symptoms
            WHERE encounter_id = :encounter_id
            ORDER BY encounter_symptom_id
            LIMIT 1
        """),
        {
            "encounter_id": encounter.encounter_id
        }
    ).mappings().first()

    print("\nFIRST STORED SYMPTOM")
    print(dict(symptom_row) if symptom_row else "NOT FOUND")


    # -----------------------------------------------------
    # TREATMENT
    # -----------------------------------------------------

    treatment_row = connection.execute(
        text("""
            SELECT
                treatment_id,
                dose,
                dose_unit,
                frequency,
                duration_days,
                start_timestamp,
                end_timestamp,
                adverse_effect
            FROM encounter_treatments
            WHERE encounter_id = :encounter_id
            ORDER BY encounter_treatment_id
            LIMIT 1
        """),
        {
            "encounter_id": encounter.encounter_id
        }
    ).mappings().first()

    print("\nFIRST STORED TREATMENT")
    print(dict(treatment_row) if treatment_row else "NOT FOUND")


    # -----------------------------------------------------
    # COMPLICATION
    # -----------------------------------------------------

    complication_row = connection.execute(
        text("""
            SELECT
                complication_id,
                identified_timestamp,
                resolved,
                severity_id,
                resolution_timestamp,
                notes
            FROM encounter_complications
            WHERE encounter_id = :encounter_id
            ORDER BY encounter_complication_id
            LIMIT 1
        """),
        {
            "encounter_id": encounter.encounter_id
        }
    ).mappings().first()

    print("\nFIRST STORED COMPLICATION")
    print(
        dict(complication_row)
        if complication_row
        else "NOT FOUND"
    )


    # -----------------------------------------------------
    # LAB
    # -----------------------------------------------------

    lab_row = connection.execute(
        text("""
            SELECT
                test_code,
                test_name,
                result_value,
                unit,
                reference_range_low,
                reference_range_high,
                abnormal_flag,
                test_timestamp
            FROM encounter_labs
            WHERE encounter_id = :encounter_id
            ORDER BY encounter_lab_id
            LIMIT 1
        """),
        {
            "encounter_id": encounter.encounter_id
        }
    ).mappings().first()

    print("\nFIRST STORED LAB")
    print(dict(lab_row) if lab_row else "NOT FOUND")


    # -----------------------------------------------------
    # IMAGING
    # -----------------------------------------------------

    imaging_row = connection.execute(
        text("""
            SELECT
                imaging_id,
                imaging_name,
                modality,
                body_site,
                finding,
                impression,
                performed_timestamp
            FROM encounter_imaging
            WHERE encounter_id = :encounter_id
            ORDER BY encounter_imaging_id
            LIMIT 1
        """),
        {
            "encounter_id": encounter.encounter_id
        }
    ).mappings().first()

    print("\nFIRST STORED IMAGING")
    print(dict(imaging_row) if imaging_row else "NOT FOUND")


# =========================================================
# VERIFICATION
# =========================================================

print("\n" + "=" * 70)
print("ROUND-TRIP VERIFICATION")
print("=" * 70)


# ---------------------------------------------------------
# PATIENT ENCOUNTER CHECKS
# ---------------------------------------------------------

assert encounter_row is not None, \
    "Encounter was not found in patient_encounter."

assert encounter_row["encounter_id"] == encounter.encounter_id

assert encounter_row["parent_encounter_id"] == encounter.parent_encounter_id

assert encounter_row["treatment_duration_days"] == \
    encounter.treatment_duration_days

assert encounter_row["readmitted_within_30_days"] == \
    encounter.readmitted_within_30_days

assert encounter_row["follow_up_status"] == \
    encounter.follow_up_status

assert encounter_row["complication_count"] == \
    len(encounter.complications)

assert encounter_row["admission_required"] == \
    encounter.admission_required

assert encounter_row["referral_required"] == \
    encounter.referral_required

print("✓ Patient encounter fields match")


# ---------------------------------------------------------
# SYMPTOM CHECKS
# ---------------------------------------------------------

if encounter.symptoms:

    assert symptom_row is not None, \
        "Generated symptom was not found in database."

    symptom = encounter.symptoms[0]

    assert symptom_row["symptom_id"] == symptom.symptom_id

    assert symptom_row["severity"] == symptom.severity

    assert symptom_row["duration_days"] == symptom.duration_days

    assert symptom_row["frequency"] == symptom.frequency

    assert symptom_row["progression"] == symptom.progression

    assert symptom_row["onset_timestamp"] == symptom.onset_timestamp

    print("✓ Symptom fields match")

else:

    print("⚠ No symptoms generated; symptom check skipped")


# ---------------------------------------------------------
# TREATMENT CHECKS
# ---------------------------------------------------------

if encounter.treatments:

    assert treatment_row is not None, \
        "Generated treatment was not found in database."

    treatment = encounter.treatments[0]

    assert treatment_row["treatment_id"] == treatment.treatment_id

    assert treatment_row["dose"] == treatment.dose

    assert treatment_row["dose_unit"] == treatment.dose_unit

    assert treatment_row["frequency"] == treatment.frequency

    assert treatment_row["duration_days"] == treatment.duration_days

    assert treatment_row["start_timestamp"] == \
        treatment.start_timestamp

    assert treatment_row["end_timestamp"] == \
        treatment.end_timestamp

    assert treatment_row["adverse_effect"] == \
        treatment.adverse_effect

    print("✓ Treatment fields match")

else:

    print("⚠ No treatments generated; treatment check skipped")


# ---------------------------------------------------------
# COMPLICATION CHECKS
# ---------------------------------------------------------

if encounter.complications:

    assert complication_row is not None, \
        "Generated complication was not found in database."

    complication = encounter.complications[0]

    assert complication_row["complication_id"] == \
        complication.complication_id

    assert complication_row["identified_timestamp"] == \
        complication.identified_timestamp

    assert complication_row["resolved"] == \
        complication.resolved

    assert complication_row["severity_id"] == \
        complication.severity_id

    assert complication_row["resolution_timestamp"] == \
        complication.resolution_timestamp

    assert complication_row["notes"] == \
        complication.notes

    print("✓ Complication fields match")

else:

    print("⚠ No complications generated; complication check skipped")


# ---------------------------------------------------------
# LAB CHECKS
# ---------------------------------------------------------

if encounter.labs:

    assert lab_row is not None, \
        "Generated lab was not found in database."

    lab = encounter.labs[0]

    assert lab_row["test_code"] == lab.test_code

    assert lab_row["test_name"] == lab.test_name

    if lab.result_value is not None:
        assert float(lab_row["result_value"]) == lab.result_value
    else:
        assert lab_row["result_value"] is None

    assert lab_row["unit"] == lab.unit

    if lab.reference_range_low is not None:
        assert float(lab_row["reference_range_low"]) == \
            lab.reference_range_low
    else:
        assert lab_row["reference_range_low"] is None

    if lab.reference_range_high is not None:
        assert float(lab_row["reference_range_high"]) == \
            lab.reference_range_high
    else:
        assert lab_row["reference_range_high"] is None

    # Database stores this as VARCHAR, while model uses bool.
    expected_abnormal_flag = (
        str(lab.abnormal_flag)
        if lab.abnormal_flag is not None
        else None
    )

    assert lab_row["abnormal_flag"] == expected_abnormal_flag

    assert lab_row["test_timestamp"] == lab.test_timestamp

    print("✓ Lab fields match")

else:

    print("⚠ No labs generated; lab check skipped")


# ---------------------------------------------------------
# IMAGING CHECKS
# ---------------------------------------------------------

if encounter.imaging:

    assert imaging_row is not None, \
        "Generated imaging was not found in database."

    imaging = encounter.imaging[0]

    assert imaging_row["imaging_id"] == imaging.imaging_id

    assert imaging_row["imaging_name"] == imaging.imaging_name

    assert imaging_row["modality"] == imaging.modality

    assert imaging_row["body_site"] == imaging.body_site

    assert imaging_row["finding"] == imaging.finding

    assert imaging_row["impression"] == imaging.impression

    assert imaging_row["performed_timestamp"] == \
        imaging.performed_timestamp

    print("✓ Imaging fields match")

else:

    print("⚠ No imaging generated; imaging check skipped")


# =========================================================
# FINAL RESULT
# =========================================================

print("\n" + "=" * 70)
print("✓ ROUND-TRIP VERIFICATION PASSED")
print("=" * 70)
print("\nGenerated data was successfully:")
print("  1. Generated by the simulation pipeline")
print("  2. Written to PostgreSQL")
print("  3. Read back from PostgreSQL")
print("  4. Compared against the original generated data")
print("\nD1-D4 persistence verification is successful.")


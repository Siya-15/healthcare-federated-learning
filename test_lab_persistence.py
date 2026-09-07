from datetime import date

from sqlalchemy import text

from database import get_engine
from database_writer import DatabaseWriter

from loader import load_all_tables

from generators.daily_hospital_generator import DailyHospitalGenerator
from generators.encounter_generator import EncounterGenerator
from generators.demographics_generator import DemographicsGenerator
from generators.disease_generator import DiseaseGenerator
from generators.severity_generator import SeverityGenerator
from generators.symptom_generator import SymptomGenerator
from generators.symptom_onset_generator import SymptomOnsetGenerator
from generators.vitals_generator import VitalGenerator
from generators.lab_generator import LabGenerator
from generators.imaging_generator import ImagingGenerator
from generators.treatment_generator import TreatmentGenerator
from generators.complication_generator import ComplicationGenerator
from generators.outcome_generator import OutcomeGenerator

from simulation.simulation_engine import SimulationEngine
from models.encounter import SimulationContext


# ============================================================
# 1. LOAD TABLES
# ============================================================

print("Loading tables...")

tables = load_all_tables()

print("\nAll tables loaded successfully.\n")


# ============================================================
# 2. CREATE GENERATORS
# ============================================================

daily_generator = DailyHospitalGenerator(tables)
encounter_generator = EncounterGenerator()
demographics_generator = DemographicsGenerator(tables)
disease_generator = DiseaseGenerator(tables)
severity_generator = SeverityGenerator(tables)
symptom_generator = SymptomGenerator(tables)
symptom_onset_generator = SymptomOnsetGenerator()
vitals_generator = VitalGenerator(tables)
lab_generator = LabGenerator(tables)
imaging_generator = ImagingGenerator(tables)
treatment_generator = TreatmentGenerator(tables)
complication_generator = ComplicationGenerator(tables)
outcome_generator = OutcomeGenerator()


# ============================================================
# 3. CREATE SIMULATION ENGINE
# ============================================================

engine = SimulationEngine(
    daily_generator,
    encounter_generator,
    demographics_generator,
    disease_generator,
    severity_generator,
    symptom_generator,
    symptom_onset_generator,
    vitals_generator,
    lab_generator,
    imaging_generator,
    treatment_generator,
    complication_generator,
    outcome_generator
)


# ============================================================
# 4. GENERATE ENCOUNTERS UNTIL IMAGING IS FOUND
# ============================================================

print("=" * 80)
print("GENERATING TEST ENCOUNTER")
print("=" * 80)

encounter = None

for attempt in range(1, 21):

    context = SimulationContext(
        current_date=date(2026, 8, 15),
        hospital_id="H001",
        season="Monsoon",
        outbreak_active=False,
        outbreak_disease=None
    )

    test_encounter = engine.generate_patient(context)

    print(
        f"Attempt {attempt:02d} | "
        f"Disease: {test_encounter.disease_id} | "
        f"Imaging: {len(test_encounter.imaging)}"
    )

    if test_encounter.imaging:
        encounter = test_encounter
        break


# ============================================================
# 5. STOP IF NO IMAGING WAS GENERATED
# ============================================================

if encounter is None:

    print("\n" + "=" * 80)
    print("❌ TEST STOPPED")
    print("=" * 80)

    print(
        "\nNo imaging was generated after 20 attempts."
    )

    print(
        "This is likely a probability/configuration issue "
        "rather than a database persistence issue."
    )

    raise SystemExit(1)


# ============================================================
# 6. DISPLAY GENERATED IMAGING
# ============================================================

print("\n" + "=" * 80)
print("GENERATED IMAGING")
print("=" * 80)

print(f"\nEncounter ID : {encounter.encounter_id}")
print(f"Patient ID   : {encounter.patient_id}")
print(f"Disease ID   : {encounter.disease_id}")
print(f"Severity ID  : {encounter.severity_id}")

print(f"\nGenerated imaging count: {len(encounter.imaging)}")

for imaging in encounter.imaging:

    print("\n----------------------------------------")

    print(f"Imaging Name : {imaging.imaging_name}")
    print(f"Imaging ID   : {imaging.imaging_id}")
    print(f"Modality     : {imaging.modality}")
    print(f"Body Site    : {imaging.body_site}")
    print(f"Finding      : {imaging.finding}")
    print(f"Impression   : {imaging.impression}")
    print(f"Performed    : {imaging.performed_timestamp}")


# ============================================================
# 7. SAVE TO DATABASE
# ============================================================

print("\n" + "=" * 80)
print("SAVING ENCOUNTER")
print("=" * 80)

db_engine = get_engine()

writer = DatabaseWriter(db_engine)

writer.save(encounter)

print(f"\n✅ Encounter saved: {encounter.encounter_id}")


# ============================================================
# 8. READ IMAGING BACK FROM DATABASE
# ============================================================

print("\n" + "=" * 80)
print("READING IMAGING FROM DATABASE")
print("=" * 80)

with db_engine.connect() as connection:

    rows = connection.execute(
        text("""
            SELECT
                encounter_imaging_id,
                encounter_id,
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
        """),
        {
            "encounter_id": encounter.encounter_id
        }
    ).fetchall()


# ============================================================
# 9. DISPLAY STORED IMAGING
# ============================================================

print(f"\nStored imaging count: {len(rows)}")

for row in rows:

    print("\n----------------------------------------")

    print(f"Imaging ID   : {row.imaging_id}")
    print(f"Imaging Name : {row.imaging_name}")
    print(f"Modality     : {row.modality}")
    print(f"Body Site    : {row.body_site}")
    print(f"Finding      : {row.finding}")
    print(f"Impression   : {row.impression}")
    print(f"Performed    : {row.performed_timestamp}")


# ============================================================
# 10. VERIFY COUNTS
# ============================================================

print("\n" + "=" * 80)
print("VERIFYING PERSISTENCE")
print("=" * 80)

generated_count = len(encounter.imaging)
stored_count = len(rows)

print(f"\nGenerated imaging : {generated_count}")
print(f"Stored imaging    : {stored_count}")


# ============================================================
# 11. VERIFY EACH RECORD
# ============================================================

if generated_count != stored_count:

    print("\n❌ COUNT MISMATCH")
    print(
        f"Generated {generated_count} imaging records "
        f"but found {stored_count} in the database."
    )

    raise SystemExit(1)


for generated, stored in zip(encounter.imaging, rows):

    checks = [
        generated.imaging_id == stored.imaging_id,
        generated.imaging_name == stored.imaging_name,
        generated.modality == stored.modality,
        generated.body_site == stored.body_site,
        generated.finding == stored.finding,
        generated.impression == stored.impression,
    ]

    if not all(checks):

        print("\n❌ DATA MISMATCH")

        print("\nGenerated:")
        print(generated)

        print("\nStored:")
        print(stored)

        raise SystemExit(1)


# ============================================================
# 12. SUCCESS
# ============================================================

print("\n" + "=" * 80)
print("✅ IMAGING PERSISTENCE TEST PASSED")
print("=" * 80)

print(
    "\nGeneration → Encounter → DatabaseWriter → PostgreSQL → Read-back"
)

print("\nAll generated imaging records were stored correctly.")
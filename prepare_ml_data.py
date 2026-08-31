import pandas as pd
from sqlalchemy import text

from database import get_engine


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

engine = get_engine()


# ==========================================================
# SYMPTOM LIST
# ==========================================================

SYMPTOMS = [
    "Abdominal Pain",
    "Anaemia",
    "Bleeding",
    "Breathlessness",
    "Chest Pain",
    "Chills",
    "Dehydration",
    "Diarrhoea",
    "Dry Cough",
    "Fatigue",
    "Fever",
    "Headache",
    "Joint Pain",
    "Loss of Appetite",
    "Loss of Smell",
    "Loss of Taste",
    "Muscle Pain",
    "Nausea",
    "Night Sweats",
    "Persistent Cough",
    "Rash",
    "Retro-orbital Pain",
    "Runny Nose",
    "Sore Throat",
    "Sweating",
    "Vomiting",
    "Weight Loss"
]


# ==========================================================
# LOAD ENCOUNTERS
# ==========================================================

encounter_query = """
SELECT
    encounter_id,
    hospital_id,
    age,
    gender,
    occupation,
    temperature,
    heart_rate,
    respiratory_rate,
    systolic_bp,
    diastolic_bp,
    spo2,
    disease_id,
    severity_id,
    admission_status,
    visit_type,
    symptom_onset_days,
    travel_history,
    vaccination_status,
    discharge_status,
    recovery_days
FROM patient_encounter
"""


# ==========================================================
# LOAD SYMPTOMS
# ==========================================================

symptom_query = """
SELECT
    encounter_id,
    symptom_text
FROM encounter_symptoms
"""


with engine.connect() as connection:

    df = pd.read_sql(
        text(encounter_query),
        connection
    )

    symptoms_df = pd.read_sql(
        text(symptom_query),
        connection
    )


# ==========================================================
# CREATE BINARY SYMPTOM COLUMNS
# ==========================================================

for symptom in SYMPTOMS:

    df[symptom] = 0


# ==========================================================
# MAP SYMPTOMS TO ENCOUNTERS
# ==========================================================

for _, row in symptoms_df.iterrows():

    encounter_id = row["encounter_id"]
    symptom = row["symptom_text"]

    if symptom in SYMPTOMS:

        df.loc[
            df["encounter_id"] == encounter_id,
            symptom
        ] = 1


# ==========================================================
# BASIC INFORMATION
# ==========================================================

print("=" * 60)
print("ML DATA PREPARATION")
print("=" * 60)

print(
    "\nTotal encounters:",
    len(df)
)


# ==========================================================
# CREATE HOSPITAL-WISE DATASETS
# ==========================================================

for hospital_id in sorted(
    df["hospital_id"].unique()
):

    hospital_df = df[
        df["hospital_id"] == hospital_id
    ].copy()

    filename = (
        f"ml_data_{hospital_id}.csv"
    )

    hospital_df.to_csv(
        filename,
        index=False
    )

    print(
        f"{hospital_id}: "
        f"{len(hospital_df)} records → "
        f"{filename}"
    )


# ==========================================================
# VALIDATION
# ==========================================================

print("\n" + "=" * 60)
print("VALIDATION")
print("=" * 60)

print(
    "\nTotal columns:",
    len(df.columns)
)

print(
    "Expected columns:",
    20 + len(SYMPTOMS)
)

print(
    "\nSymptom columns found:"
)

missing = [
    symptom
    for symptom in SYMPTOMS
    if symptom not in df.columns
]

if missing:

    print("Missing:", missing)

else:

    print(
        "All 27 symptom columns present."
    )


print(
    "\nML data preparation completed successfully."
)
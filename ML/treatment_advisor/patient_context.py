import sys
import os

# ==========================================================
# ALLOW IMPORT FROM PARENT DIRECTORY
# ==========================================================

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import pandas as pd

from sqlalchemy import text

from database import get_engine


# ==========================================================
# CANONICAL SYMPTOM LIST
# ==========================================================

SYMPTOM_COLUMNS = [
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
    "Weight Loss",
]


# ==========================================================
# CLINICAL CONTEXT FIELDS
# ==========================================================

DEMOGRAPHIC_FIELDS = [
    "age",
    "gender",
]

VITAL_FIELDS = [
    "temperature",
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "spo2",
]

CLASSIFICATION_FIELDS = [
    "disease_id",
    "severity_id",
]


# ==========================================================
# LOAD PATIENT CONTEXT
# ==========================================================

def load_patient_context(encounter_id):

    engine = get_engine()

    encounter_query = """
    SELECT
        encounter_id,
        age,
        gender,
        temperature,
        heart_rate,
        respiratory_rate,
        systolic_bp,
        diastolic_bp,
        spo2,
        disease_id,
        severity_id
    FROM patient_encounter
    WHERE encounter_id = :encounter_id
    """

    symptom_query = """
    SELECT
        sm.symptom_name
    FROM encounter_symptoms es
    INNER JOIN symptom_master sm
        ON es.symptom_id = sm.symptom_id
    WHERE es.encounter_id = :encounter_id
    """

    with engine.connect() as connection:

        patient_df = pd.read_sql(
            text(encounter_query),
            connection,
            params={
                "encounter_id": encounter_id
            }
        )

        symptom_df = pd.read_sql(
            text(symptom_query),
            connection,
            params={
                "encounter_id": encounter_id
            }
        )

    if patient_df.empty:
        raise ValueError(
            f"Encounter not found: {encounter_id}"
        )

    patient = patient_df.iloc[0].to_dict()

    symptoms = set(
        symptom_df["symptom_name"]
        .dropna()
        .tolist()
    )

    symptom_vector = {
        symptom: int(symptom in symptoms)
        for symptom in SYMPTOM_COLUMNS
    }

    context = {
        "encounter_id": patient["encounter_id"],

        "age": patient["age"],
        "gender": patient["gender"],

        "temperature": patient["temperature"],
        "heart_rate": patient["heart_rate"],
        "respiratory_rate": patient["respiratory_rate"],
        "systolic_bp": patient["systolic_bp"],
        "diastolic_bp": patient["diastolic_bp"],
        "spo2": patient["spo2"],

        "disease_id": patient["disease_id"],
        "severity_id": patient["severity_id"],

        "symptoms": sorted(symptoms),

        "symptom_vector": symptom_vector,
    }

    return context


# ==========================================================
# VALIDATE CLINICAL CONTEXT
# ==========================================================

def validate_patient_context(context):

    required_fields = (
        DEMOGRAPHIC_FIELDS
        + VITAL_FIELDS
        + CLASSIFICATION_FIELDS
    )

    missing_fields = []

    for field in required_fields:

        value = context.get(field)

        if value is None or pd.isna(value):

            missing_fields.append(field)

    if not context.get("disease_id"):
        missing_fields.append("disease_id")

    if not context.get("severity_id"):
        missing_fields.append("severity_id")

    symptom_vector = context.get(
        "symptom_vector",
        {}
    )

    missing_symptom_fields = [
        symptom
        for symptom in SYMPTOM_COLUMNS
        if symptom not in symptom_vector
    ]

    missing_fields.extend(
        missing_symptom_fields
    )

    return {
        "valid": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "missing_count": len(missing_fields),
    }


# ==========================================================
# CONTEXT COMPLETENESS
# ==========================================================

def calculate_context_completeness(context):

    required_fields = (
        DEMOGRAPHIC_FIELDS
        + VITAL_FIELDS
        + CLASSIFICATION_FIELDS
    )

    available = 0

    for field in required_fields:

        value = context.get(field)

        if value is not None and not pd.isna(value):
            available += 1

    total = len(required_fields)

    if total == 0:
        return 0.0

    return round(
        available / total,
        4
    )


# ==========================================================
# BUILD FINAL CONTEXT OBJECT
# ==========================================================

def build_patient_context(encounter_id):

    context = load_patient_context(
        encounter_id
    )

    validation = validate_patient_context(
        context
    )

    context["context_valid"] = validation["valid"]

    context["missing_fields"] = (
        validation["missing_fields"]
    )

    context["missing_count"] = (
        validation["missing_count"]
    )

    context["context_completeness"] = (
        calculate_context_completeness(
            context
        )
    )

    return context


# ==========================================================
# DISPLAY CONTEXT
# ==========================================================

def display_patient_context(context):

    print("=" * 70)
    print("OBJECTIVE E1 - PATIENT CLINICAL CONTEXT")
    print("=" * 70)

    print(
        f"\nEncounter ID : "
        f"{context['encounter_id']}"
    )

    print(
        f"Disease      : "
        f"{context['disease_id']}"
    )

    print(
        f"Severity     : "
        f"{context['severity_id']}"
    )

    print("\n" + "-" * 70)
    print("DEMOGRAPHICS")
    print("-" * 70)

    print(
        f"Age          : "
        f"{context['age']}"
    )

    print(
        f"Gender       : "
        f"{context['gender']}"
    )

    print("\n" + "-" * 70)
    print("VITALS")
    print("-" * 70)

    for field in VITAL_FIELDS:

        print(
            f"{field:<20}: "
            f"{context[field]}"
        )

    print("\n" + "-" * 70)
    print("SYMPTOMS")
    print("-" * 70)

    symptoms = context["symptoms"]

    print(
        f"Total symptoms: "
        f"{len(symptoms)}"
    )

    if symptoms:

        for symptom in symptoms:
            print(f"  • {symptom}")

    else:

        print("  No symptoms recorded.")

    print("\n" + "-" * 70)
    print("CONTEXT VALIDATION")
    print("-" * 70)

    print(
        f"Valid              : "
        f"{context['context_valid']}"
    )

    print(
        f"Completeness       : "
        f"{context['context_completeness'] * 100:.2f}%"
    )

    print(
        f"Missing fields     : "
        f"{context['missing_count']}"
    )

    if context["missing_fields"]:

        for field in context["missing_fields"]:
            print(f"  • {field}")


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    engine = get_engine()

    query = """
    SELECT encounter_id
    FROM patient_encounter
    ORDER BY encounter_id
    LIMIT 1
    """

    with engine.connect() as connection:
        result = connection.execute(text(query))
        row = result.fetchone()

    if row is None:
        raise ValueError(
            "No encounters found in patient_encounter."
        )

    encounter_id = row[0]

    print(f"Testing encounter: {encounter_id}")

    context = build_patient_context(
        encounter_id
    )

    display_patient_context(
        context
    )
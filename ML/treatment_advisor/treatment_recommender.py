import sys
import os
import joblib
import pandas as pd

from sqlalchemy import text

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

from database import get_engine
from .candidate_treatments import get_candidate_treatments

from pathlib import Path

ML_DIR = Path(__file__).resolve().parent

# ==========================================================
# SYMPTOM COLUMNS
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
# LOAD MODEL
# ==========================================================




def load_model():

    model_path = ML_DIR / "models" / "treatment_success_model.pkl"

    saved = joblib.load(model_path)

    return (
        saved["model"],
        saved["feature_names"]
    )


# ==========================================================
# LOAD PATIENT
# ==========================================================

def load_patient(encounter_id):

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
        es.encounter_id,
        sm.symptom_name
    FROM encounter_symptoms es
    INNER JOIN symptom_master sm
        ON es.symptom_id = sm.symptom_id
    WHERE es.encounter_id = :encounter_id
    """

    with engine.connect() as connection:

        patient = pd.read_sql(
            text(encounter_query),
            connection,
            params={
                "encounter_id": encounter_id
            }
        )

        symptoms = pd.read_sql(
            text(symptom_query),
            connection,
            params={
                "encounter_id": encounter_id
            }
        )

    if patient.empty:

        raise ValueError(
            f"Encounter not found: {encounter_id}"
        )

    patient = patient.iloc[0].to_dict()

    patient_symptoms = set(
        symptoms["symptom_name"]
    )

    return patient, patient_symptoms


# ==========================================================
# CREATE FEATURES FOR ONE PATIENT + TREATMENT
# ==========================================================

def create_features(
    patient,
    patient_symptoms,
    treatment_id,
    feature_names
):

    row = {}

    # ------------------------------------------------------
    # Numerical features
    # ------------------------------------------------------

    row["age"] = patient["age"]
    row["temperature"] = patient["temperature"]
    row["heart_rate"] = patient["heart_rate"]
    row["respiratory_rate"] = patient["respiratory_rate"]
    row["systolic_bp"] = patient["systolic_bp"]
    row["diastolic_bp"] = patient["diastolic_bp"]
    row["spo2"] = patient["spo2"]

    # ------------------------------------------------------
    # Categorical features
    # ------------------------------------------------------

    for gender in [
        "Male",
        "Female"
    ]:

        row[f"gender_{gender}"] = int(
            patient["gender"] == gender
        )

    # ------------------------------------------------------
    # Disease
    # ------------------------------------------------------

    disease_feature = (
        f"disease_id_{patient['disease_id']}"
    )

    row[disease_feature] = 1

    # ------------------------------------------------------
    # Severity
    # ------------------------------------------------------

    severity_feature = (
        f"severity_id_{patient['severity_id']}"
    )

    row[severity_feature] = 1

    # ------------------------------------------------------
    # Treatment
    # ------------------------------------------------------

    treatment_feature = (
        f"treatment_id_{treatment_id}"
    )

    row[treatment_feature] = 1

    # ------------------------------------------------------
    # Symptoms
    # ------------------------------------------------------

    for symptom in SYMPTOM_COLUMNS:

        row[symptom] = int(
            symptom in patient_symptoms
        )

    # ------------------------------------------------------
    # Match exact training feature order
    # ------------------------------------------------------

    X = pd.DataFrame(
        [row]
    )

    X = X.reindex(
        columns=feature_names,
        fill_value=0
    )

    return X


# ==========================================================
# RANK TREATMENTS
# ==========================================================

def recommend_treatments(
    encounter_id
):

    model, feature_names = load_model()

    patient, patient_symptoms = (
        load_patient(encounter_id)
    )

    candidates = get_candidate_treatments(
        patient["disease_id"],
        patient["severity_id"]
    )

    if candidates.empty:

        return patient, candidates

    recommendations = []

    for _, candidate in candidates.iterrows():

        treatment_id = (
            candidate["treatment_id"]
        )

        X = create_features(
            patient,
            patient_symptoms,
            treatment_id,
            feature_names
        )

        success_probability = (
            model.predict_proba(X)[0][1]
        )

        recommendations.append({
            "treatment_id": treatment_id,
            "success_probability":
                success_probability,
            "priority":
                candidate["priority"],
            "first_line":
                candidate["first_line"],
            "referral_required":
                candidate["referral_required"],
            "comments":
                candidate["comments"],
        })

    recommendations = pd.DataFrame(
        recommendations
    )

    recommendations = (
        recommendations
        .sort_values(
            "success_probability",
            ascending=False
        )
        .reset_index(drop=True)
    )

    recommendations[
        "rank"
    ] = range(
        1,
        len(recommendations) + 1
    )

    return patient, recommendations


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    # ------------------------------------------------------
    # Use an existing encounter from your database
    # ------------------------------------------------------

    encounter_id = "ENC-7B7DEBF90A"

    patient, recommendations = (
        recommend_treatments(
            encounter_id
        )
    )

    print("=" * 60)
    print("OBJECTIVE E - TREATMENT RECOMMENDATION")
    print("=" * 60)

    print(
        f"\nEncounter: "
        f"{patient['encounter_id']}"
    )

    print(
        f"Disease: "
        f"{patient['disease_id']}"
    )

    print(
        f"Severity: "
        f"{patient['severity_id']}"
    )

    print(
        "\nRanked treatment options:"
    )

    if recommendations.empty:

        print(
            "\nNo candidate treatments found."
        )

    else:

        display_columns = [
            "rank",
            "treatment_id",
            "success_probability",
            "priority",
            "first_line",
            "referral_required",
            "comments",
        ]

        output = recommendations[
            display_columns
        ].copy()

        output[
            "success_probability"
        ] = (
            output[
                "success_probability"
            ] * 100
        ).round(2)

        output = output.rename(
            columns={
                "success_probability":
                    "success_probability_percent"
            }
        )

        print(
            output.to_string(
                index=False
            )
        )
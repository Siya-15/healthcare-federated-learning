import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import joblib
import pandas as pd

from sqlalchemy import text

from database import get_engine
from .candidate_treatments import get_candidate_treatments


# ==========================================================
# LOAD SAVED MODEL
# ==========================================================

def load_model():

    saved = joblib.load(
        "treatment_success_model.pkl"
    )

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
    )

    return patient, symptoms


# ==========================================================
# SYMPTOM LIST
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
# CREATE MODEL FEATURES
# ==========================================================

def create_features(
    patient,
    symptoms,
    treatment_id,
    feature_names
):

    row = {}

    # Numerical features
    row["age"] = patient["age"]
    row["temperature"] = patient["temperature"]
    row["heart_rate"] = patient["heart_rate"]
    row["respiratory_rate"] = patient["respiratory_rate"]
    row["systolic_bp"] = patient["systolic_bp"]
    row["diastolic_bp"] = patient["diastolic_bp"]
    row["spo2"] = patient["spo2"]

    # Gender
    row["gender_Male"] = int(
        patient["gender"] == "Male"
    )

    row["gender_Female"] = int(
        patient["gender"] == "Female"
    )

    # Disease
    row[
        f"disease_id_{patient['disease_id']}"
    ] = 1

    # Severity
    row[
        f"severity_id_{patient['severity_id']}"
    ] = 1

    # Treatment
    row[
        f"treatment_id_{treatment_id}"
    ] = 1

    # Symptoms
    for symptom in SYMPTOM_COLUMNS:

        row[symptom] = int(
            symptom in symptoms
        )

    X = pd.DataFrame([row])

    # IMPORTANT:
    # Match exactly the feature order used during training.

    X = X.reindex(
        columns=feature_names,
        fill_value=0
    )

    return X


# ==========================================================
# E4 — EXPECTED RECOVERY
# ==========================================================

def get_recovery_estimate(
    disease_id,
    severity_id
):

    engine = get_engine()

    query = """
    SELECT
        pe.recovery_days

    FROM patient_encounter pe

    WHERE
        pe.disease_id = :disease_id
        AND pe.severity_id = :severity_id
        AND pe.recovery_days IS NOT NULL
    """

    with engine.connect() as connection:

        df = pd.read_sql(
            text(query),
            connection,
            params={
                "disease_id": disease_id,
                "severity_id": severity_id
            }
        )

    if df.empty:
        return None

    return round(
        df["recovery_days"].mean(),
        2
    )


# ==========================================================
# E5 — COMPLICATION / RISK INFORMATION
# ==========================================================

def get_risk_information(
    disease_id,
    severity_id
):

    engine = get_engine()

    query = """
    SELECT
        dcm.complication_id,
        cm.complication_name,
        cm.body_system,
        dcm.frequency,
        cm.description

    FROM disease_complication_mapping dcm

    INNER JOIN complication_master cm
        ON dcm.complication_id =
           cm.complication_id

    WHERE
        dcm.disease_id = :disease_id
        AND dcm.severity_id = :severity_id
    """

    with engine.connect() as connection:

        risks = pd.read_sql(
            text(query),
            connection,
            params={
                "disease_id": disease_id,
                "severity_id": severity_id
            }
        )

    return risks


# ==========================================================
# FINAL TREATMENT ADVISOR
# ==========================================================

def treatment_advisor(encounter_id):

    # ------------------------------------------------------
    # Load model
    # ------------------------------------------------------

    model, feature_names = load_model()

    # ------------------------------------------------------
    # Load patient
    # ------------------------------------------------------

    patient, symptoms = load_patient(
        encounter_id
    )

    disease_id = patient["disease_id"]
    severity_id = patient["severity_id"]

    # ------------------------------------------------------
    # E2 — Candidate treatments
    # ------------------------------------------------------

    candidates = get_candidate_treatments(
        disease_id,
        severity_id
    )

    if candidates.empty:

        return {
            "patient": patient,
            "recommendations": pd.DataFrame(),
            "recovery_days": None,
            "risks": pd.DataFrame()
        }

    # ------------------------------------------------------
    # E1 + E3 — Predict and rank
    # ------------------------------------------------------

    recommendations = []

    for _, candidate in candidates.iterrows():

        treatment_id = (
            candidate["treatment_id"]
        )

        X = create_features(
            patient,
            symptoms,
            treatment_id,
            feature_names
        )

        probability = (
            model.predict_proba(X)[0][1]
        )

        recommendations.append({

            "treatment_id":
                treatment_id,

            "success_probability":
                round(
                    probability * 100,
                    2
                ),

            "priority":
                candidate["priority"],

            "first_line":
                candidate["first_line"],

            "referral_required":
                candidate["referral_required"],

            "comments":
                candidate["comments"]
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

    recommendations["rank"] = (
        range(
            1,
            len(recommendations) + 1
        )
    )

    # ------------------------------------------------------
    # E4 — Recovery
    # ------------------------------------------------------

    recovery_days = get_recovery_estimate(
        disease_id,
        severity_id
    )

    # ------------------------------------------------------
    # E5 — Risks
    # ------------------------------------------------------

    risks = get_risk_information(
        disease_id,
        severity_id
    )

    return {
        "patient": patient,
        "recommendations": recommendations,
        "recovery_days": recovery_days,
        "risks": risks
    }


# ==========================================================
# DISPLAY FINAL ADVISOR
# ==========================================================

if __name__ == "__main__":

    encounter_id = "ENC-7B7DEBF90A"

    result = treatment_advisor(
        encounter_id
    )

    patient = result["patient"]
    recommendations = result["recommendations"]
    recovery_days = result["recovery_days"]
    risks = result["risks"]

    print("=" * 60)
    print("FINAL TREATMENT ADVISOR")
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

    print("\n" + "-" * 60)
    print("RANKED TREATMENT OPTIONS")
    print("-" * 60)

    if recommendations.empty:

        print(
            "\nNo candidate treatments found."
        )

    else:

        for _, row in recommendations.iterrows():

            print(
                f"\n{int(row['rank'])}. "
                f"{row['treatment_id']}"
            )

            print(
                f"   Estimated success: "
                f"{row['success_probability']:.2f}%"
            )

            print(
                f"   Priority: "
                f"{row['priority']}"
            )

            print(
                f"   First-line: "
                f"{row['first_line']}"
            )

            print(
                f"   Referral required: "
                f"{row['referral_required']}"
            )

            print(
                f"   Comment: "
                f"{row['comments']}"
            )

    print("\n" + "-" * 60)
    print("EXPECTED RECOVERY")
    print("-" * 60)

    if recovery_days is None:

        print(
            "No historical recovery estimate available."
        )

    else:

        print(
            f"\nExpected historical recovery: "
            f"{recovery_days} days"
        )

    print("\n" + "-" * 60)
    print("POTENTIAL COMPLICATIONS")
    print("-" * 60)

    if risks.empty:

        print(
            "\nNo complications mapped "
            "for this disease/severity."
        )

    else:

        for _, risk in risks.iterrows():

            print(
                f"\n• {risk['complication_name']}"
            )

            print(
                f"  Frequency: "
                f"{risk['frequency']}"
            )

            print(
                f"  Body system: "
                f"{risk['body_system']}"
            )

            print(
                f"  Description: "
                f"{risk['description']}"
            )

    print("\n" + "-" * 60)
    print("ADVISORY NOTE")
    print("-" * 60)

    print(
        "\nThis output is a decision-support estimate "
        "based on historical encounters and predefined "
        "clinical mappings. It does not constitute an "
        "autonomous prescription."
    )
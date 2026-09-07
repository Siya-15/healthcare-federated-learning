"""
E6 - Treatment Success Model

Random Forest model for estimating historical treatment-success
probability for a patient context + candidate treatment.

Important:
- This is an observational/historical outcome model.
- The output is NOT a causal estimate of treatment effectiveness.
- It must NOT be interpreted as a prescription.
- E7 will handle probability calibration.
- E8 will handle uncertainty.
"""

import os
import sys

# ==========================================================
# ALLOW IMPORT FROM PROJECT ROOT
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


import joblib
import numpy as np
import pandas as pd

from sqlalchemy import text

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from database import get_engine
from ML.treatment_advisor.clinical_eligibility import (
    evaluate_candidates,
    load_treatment_master
)

# ==========================================================
# MODEL ARTIFACT
# ==========================================================

MODEL_FILENAME = "treatment_success_model.pkl"

MODEL_PATH = os.path.join(
    PROJECT_ROOT,
    MODEL_FILENAME
)


# ==========================================================
# DATABASE LOADING
# ==========================================================

def load_data():

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
        severity_id,
        discharge_status,
        recovery_days
    FROM patient_encounter
    """

    treatment_query = """
    SELECT
        encounter_id,
        treatment_id
    FROM encounter_treatments
    WHERE administered = TRUE
    """

    symptom_query = """
    SELECT
        encounter_id,
        symptom_id
    FROM encounter_symptoms
    """

    symptom_master_query = """
    SELECT
        symptom_id,
        symptom_name
    FROM symptom_master
    """

    treatment_master_query = """
    SELECT
        treatment_id,
        treatment_name
    FROM treatment_master
    """

    with engine.connect() as connection:

        encounters = pd.read_sql(
            text(encounter_query),
            connection
        )

        treatments = pd.read_sql(
            text(treatment_query),
            connection
        )

        symptoms = pd.read_sql(
            text(symptom_query),
            connection
        )

        symptom_master = pd.read_sql(
            text(symptom_master_query),
            connection
        )

        treatment_master = pd.read_sql(
            text(treatment_master_query),
            connection
        )

    return (
        encounters,
        treatments,
        symptoms,
        symptom_master,
        treatment_master,
    )


# ==========================================================
# SYMPTOM FEATURES
# ==========================================================

def create_symptom_features(
    symptoms,
    symptom_master
):
    """
    Convert encounter-level symptom records into
    one-hot symptom features.
    """

    symptoms = symptoms.merge(
        symptom_master,
        on="symptom_id",
        how="left"
    )

    symptom_table = (
        symptoms
        .assign(value=1)
        .pivot_table(
            index="encounter_id",
            columns="symptom_name",
            values="value",
            fill_value=0
        )
        .reset_index()
    )

    return symptom_table


# ==========================================================
# DATASET PREPARATION
# ==========================================================

def prepare_dataset():

    (
        encounters,
        treatments,
        symptoms,
        symptom_master,
        treatment_master,
    ) = load_data()

    symptom_features = create_symptom_features(
        symptoms,
        symptom_master
    )

    data = encounters.merge(
        symptom_features,
        on="encounter_id",
        how="left"
    )

    data = data.merge(
        treatments,
        on="encounter_id",
        how="inner"
    )

    data = data.merge(
        treatment_master,
        on="treatment_id",
        how="left"
    )

    # ------------------------------------------------------
    # TARGET
    # ------------------------------------------------------

    data["treatment_success"] = (
        data["discharge_status"] == "Recovered"
    ).astype(int)

    # ------------------------------------------------------
    # ENSURE ALL SYMPTOM COLUMNS EXIST
    # ------------------------------------------------------

    symptom_names = (
        symptom_master["symptom_name"]
        .tolist()
    )

    for symptom in symptom_names:

        if symptom not in data.columns:
            data[symptom] = 0

    data[symptom_names] = (
        data[symptom_names]
        .fillna(0)
        .astype(int)
    )

    # ------------------------------------------------------
    # FEATURES
    # ------------------------------------------------------

    numerical_features = [
        "age",
        "temperature",
        "heart_rate",
        "respiratory_rate",
        "systolic_bp",
        "diastolic_bp",
        "spo2",
    ]

    categorical_features = [
        "gender",
        "disease_id",
        "severity_id",
        "treatment_id",
    ]

    feature_data = data[
        numerical_features
        + categorical_features
        + symptom_names
    ].copy()

    feature_data = pd.get_dummies(
        feature_data,
        columns=categorical_features,
        dtype=int
    )

    feature_data = feature_data.fillna(0)

    X = feature_data
    y = data["treatment_success"]

    return (
        data,
        X,
        y,
        feature_data.columns.tolist()
    )


# ==========================================================
# TRAIN MODEL
# ==========================================================

def train_model():

    (
        data,
        X,
        y,
        feature_names
    ) = prepare_dataset()

    print("=" * 70)
    print("OBJECTIVE E - E6 TREATMENT SUCCESS MODEL")
    print("=" * 70)

    print(
        f"\nTraining records: {len(data)}"
    )

    print(
        f"Features: {len(feature_names)}"
    )

    print("\nOutcome distribution:")

    print(
        y.value_counts()
        .rename({
            0: "Not Success",
            1: "Success"
        })
        .to_string()
    )

    # ------------------------------------------------------
    # GROUPED TRAIN/TEST SPLIT
    # ------------------------------------------------------

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42
    )

    train_idx, test_idx = next(
        splitter.split(
            X,
            y,
            groups=data["encounter_id"]
        )
    )

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    # ------------------------------------------------------
    # VERIFY ENCOUNTER ISOLATION
    # ------------------------------------------------------

    train_encounters = set(
        data.iloc[train_idx]["encounter_id"]
    )

    test_encounters = set(
        data.iloc[test_idx]["encounter_id"]
    )

    overlap = train_encounters.intersection(
        test_encounters
    )

    print(
        f"\nUnique training encounters: "
        f"{len(train_encounters)}"
    )

    print(
        f"Unique testing encounters: "
        f"{len(test_encounters)}"
    )

    print(
        f"Encounter overlap: {len(overlap)}"
    )

    if overlap:
        raise ValueError(
            "Data leakage detected: "
            "encounters occur in both train and test."
        )

    # ------------------------------------------------------
    # RANDOM FOREST
    # ------------------------------------------------------

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_split=5,
        random_state=42,
        class_weight="balanced"
    )

    print("\nTraining Random Forest...")

    model.fit(
        X_train,
        y_train
    )

    print("Model trained successfully.")

    # ------------------------------------------------------
    # PREDICTIONS
    # ------------------------------------------------------

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    # ------------------------------------------------------
    # EVALUATION
    # ------------------------------------------------------

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    auc = roc_auc_score(
        y_test,
        probabilities
    )

    print(
        f"\nAccuracy: {accuracy:.4f}"
    )

    print(
        f"ROC-AUC: {auc:.4f}"
    )

    print("\nClassification report:")

    print(
        classification_report(
            y_test,
            predictions
        )
    )

    # ------------------------------------------------------
    # FEATURE IMPORTANCE
    # ------------------------------------------------------

    importance = pd.DataFrame({
        "feature": feature_names,
        "importance": model.feature_importances_
    })

    importance = (
        importance
        .sort_values(
            "importance",
            ascending=False
        )
    )

    print("\nTop 15 important features:")

    print(
        importance
        .head(15)
        .to_string(index=False)
    )

    # ------------------------------------------------------
    # SAVE MODEL
    # ------------------------------------------------------

    artifact = {
        "model": model,
        "feature_names": feature_names,
    }

    joblib.dump(
        artifact,
        MODEL_PATH
    )

    print(
        f"\nModel saved as: {MODEL_PATH}"
    )

    return (
        model,
        data,
        feature_names
    )


# ==========================================================
# LOAD TRAINED MODEL
# ==========================================================

def load_model():

    if not os.path.exists(MODEL_PATH):

        raise FileNotFoundError(
            "Treatment success model not found. "
            "Run train_model() first."
        )

    artifact = joblib.load(
        MODEL_PATH
    )

    if not isinstance(artifact, dict):
        raise ValueError(
            "Invalid treatment model artifact."
        )

    if "model" not in artifact:
        raise ValueError(
            "Model artifact missing 'model'."
        )

    if "feature_names" not in artifact:
        raise ValueError(
            "Model artifact missing 'feature_names'."
        )

    return (
        artifact["model"],
        artifact["feature_names"]
    )


# ==========================================================
# BUILD INFERENCE FEATURES
# ==========================================================

def build_prediction_features(
    patient_context,
    treatment_id,
    feature_names
):
    """
    Construct an inference row using the exact feature
    representation expected by the trained model.

    The patient_context follows the canonical E1 structure.
    """

    row = {}

    # ------------------------------------------------------
    # Numerical patient features
    # ------------------------------------------------------

    numerical_features = [
        "age",
        "temperature",
        "heart_rate",
        "respiratory_rate",
        "systolic_bp",
        "diastolic_bp",
        "spo2",
    ]

    for feature in numerical_features:

        row[feature] = patient_context.get(
            feature,
            0
        )

    # ------------------------------------------------------
    # Categorical features
    # ------------------------------------------------------

    categorical_values = {
        "gender": patient_context.get(
            "gender",
            ""
        ),

        "disease_id": patient_context.get(
            "disease_id",
            ""
        ),

        "severity_id": patient_context.get(
            "severity_id",
            ""
        ),

        "treatment_id": treatment_id,
    }

    # ------------------------------------------------------
    # Identify symptom columns
    # ------------------------------------------------------

    symptom_columns = [
        column
        for column in feature_names
        if column not in numerical_features
        and not column.startswith("gender_")
        and not column.startswith("disease_id_")
        and not column.startswith("severity_id_")
        and not column.startswith("treatment_id_")
    ]

    # ------------------------------------------------------
    # Patient symptoms
    # ------------------------------------------------------

    patient_symptoms = patient_context.get(
        "symptoms",
        []
    )

    if isinstance(patient_symptoms, dict):

        active_symptoms = {
            name
            for name, value in patient_symptoms.items()
            if value
        }

    elif isinstance(patient_symptoms, list):

        active_symptoms = set(
            patient_symptoms
        )

    else:

        active_symptoms = set()

    for symptom in symptom_columns:

        row[symptom] = (
            1
            if symptom in active_symptoms
            else 0
        )

    # ------------------------------------------------------
    # One-hot categorical features
    # ------------------------------------------------------

    for category, value in categorical_values.items():

        prefix = f"{category}_"

        for feature in feature_names:

            if feature.startswith(prefix):

                row[feature] = (
                    1
                    if str(value)
                    == feature[len(prefix):]
                    else 0
                )

    # ------------------------------------------------------
    # Exact training schema
    # ------------------------------------------------------

    prediction = pd.DataFrame(
        [row]
    )

    prediction = prediction.reindex(
        columns=feature_names,
        fill_value=0
    )

    prediction = prediction.apply(
        pd.to_numeric,
        errors="coerce"
    ).fillna(0)

    return prediction


# ==========================================================
# PREDICT TREATMENT SUCCESS
# ==========================================================

def predict_treatment_success(
    patient_context,
    treatment_id
):
    """
    Predict raw historical treatment-success probability
    for a patient context + treatment.

    Calibration is intentionally handled by E7.
    Uncertainty is intentionally handled by E8.
    """

    model, feature_names = load_model()

    prediction_features = build_prediction_features(
        patient_context,
        treatment_id,
        feature_names
    )

    probability = float(
        model.predict_proba(
            prediction_features
        )[0, 1]
    )

    prediction = int(
        probability >= 0.5
    )

    return {
        "treatment_id": treatment_id,

        "raw_success_probability": round(
            probability,
            6
        ),

        "raw_success_percentage": round(
            probability * 100,
            2
        ),

        "predicted_success": prediction,

        "model_type": (
            "Random Forest Classifier"
        ),

        "probability_status": (
            "RAW_UNCALIBRATED"
        ),

        "interpretation": (
            "Historical outcome association from the "
            "project treatment-success model. This is "
            "not a causal estimate of treatment effectiveness "
            "and is not an autonomous prescribing decision."
        ),
    }


# ==========================================================
# BATCH PREDICTION
# ==========================================================

def predict_treatments(
    patient_context,
    treatment_ids
):
    """
    Predict raw treatment-success probabilities
    for multiple candidate treatments.
    """

    results = []

    for treatment_id in treatment_ids:

        results.append(
            predict_treatment_success(
                patient_context,
                treatment_id
            )
        )

    return results


# ==========================================================
# MODEL VALIDATION
# ==========================================================

def validate_model_artifact():

    model, feature_names = load_model()

    if not hasattr(
        model,
        "predict_proba"
    ):
        raise ValueError(
            "Loaded model does not support predict_proba()."
        )

    if not feature_names:
        raise ValueError(
            "Feature list is empty."
        )

    if len(feature_names) != len(
        model.feature_importances_
    ):
        raise ValueError(
            "Feature names do not match model dimensions."
        )

    return True


# ==========================================================
# FIND VALID E1 TEST ENCOUNTER
# ==========================================================

def find_valid_test_encounter():
    """
    Find a real encounter that can successfully pass
    through the canonical E2 patient-context pipeline.
    """

    from ML.treatment_advisor.candidate_treatments import (
        generate_candidates_for_encounter
    )

    engine = get_engine()

    sample_query = text("""
        SELECT encounter_id
        FROM patient_encounter
        ORDER BY visit_timestamp
    """)

    with engine.connect() as connection:

        sample = pd.read_sql(
            sample_query,
            connection
        )

    if sample.empty:

        raise ValueError(
            "No encounters available for E6 testing."
        )

    # Try a limited number of encounters rather than
    # querying the database indefinitely.
    max_attempts = min(
        100,
        len(sample)
    )

    for candidate_id in sample[
        "encounter_id"
    ].head(max_attempts):

        try:

            (
                context,
                candidates,
                _
            ) = generate_candidates_for_encounter(
                candidate_id
            )

            if not candidates.empty:

                return candidate_id, context

        except Exception:

            continue

    raise ValueError(
        "Could not find an encounter that successfully "
        "passes the E1 -> E2 candidate-generation pipeline."
    )


# ==========================================================
# E6 PIPELINE VALIDATION
# ==========================================================
def run_e6_pipeline_test():
    """
    Validate the complete E1 -> E2 -> E3 -> E4 -> E6 path.

    E2's generate_candidates_for_encounter() is the canonical
    E1 -> E2 integration point, so E6 uses that function rather
    than manually passing an E1 context into E2.
    """

    from ML.treatment_advisor.candidate_treatments import (
        generate_candidates_for_encounter
    )

    from ML.treatment_advisor.clinical_eligibility import (
        evaluate_candidates
    )

    from ML.treatment_advisor.e4_configuration import (
        enrich_candidates
    )

    # ------------------------------------------------------
    # Find a valid encounter
    # ------------------------------------------------------

    encounter_id, _ = find_valid_test_encounter()

    print(
        f"\nTesting encounter: {encounter_id}"
    )

    # ------------------------------------------------------
    # E1 -> E2
    #
    # Use E2's canonical pipeline function.
    # ------------------------------------------------------

    (
        context,
        candidates,
        candidate_records
    ) = generate_candidates_for_encounter(
        encounter_id
    )

    if candidates.empty:

        raise ValueError(
            "E2 returned no treatment candidates."
        )

    print(
        f"Hospital: "
        f"{context.get('hospital_id', 'Retrieved separately')}"
    )

    print(
        f"Disease: "
        f"{context.get('disease_id')}"
    )

    print(
        f"Severity: "
        f"{context.get('severity_id')}"
    )

    print(
        f"\nE2 candidates: "
        f"{len(candidates)}"
    )

    # ------------------------------------------------------
    # Retrieve hospital for E4
    # ------------------------------------------------------

    engine = get_engine()

    hospital_query = text("""
        SELECT hospital_id
        FROM patient_encounter
        WHERE encounter_id = :encounter_id
    """)

    with engine.connect() as connection:

        hospital_result = pd.read_sql(
            hospital_query,
            connection,
            params={
                "encounter_id": encounter_id
            }
        )

    if hospital_result.empty:

        raise ValueError(
            f"Hospital not found for encounter: "
            f"{encounter_id}"
        )

    hospital_id = hospital_result.iloc[0][
        "hospital_id"
    ]

    if pd.isna(hospital_id):

        raise ValueError(
            f"Hospital ID is missing for encounter: "
            f"{encounter_id}"
        )

    hospital_id = str(hospital_id)

    print(
        f"Hospital used for E4: {hospital_id}"
    )

    # ------------------------------------------------------
    # E3 - Clinical Eligibility
    # ------------------------------------------------------

    treatment_master = load_treatment_master()

    eligible_candidates = evaluate_candidates(
        candidates,
        treatment_master
    )

    if eligible_candidates.empty:

        raise ValueError(
            "E3 returned no candidate evaluations."
        )

    print(
        f"E3 evaluated candidates: "
        f"{len(eligible_candidates)}"
    )

    # ------------------------------------------------------
    # E4 - Configuration Enrichment
    # ------------------------------------------------------

    enriched_candidates = enrich_candidates(
        eligible_candidates,
        hospital_id
    )

    if enriched_candidates.empty:

        raise ValueError(
            "E4 returned no enriched candidates."
        )

    print(
        f"E4 enriched candidates: "
        f"{len(enriched_candidates)}"
    )

    # ------------------------------------------------------
    # E6 - Treatment Success Prediction
    # ------------------------------------------------------

    print(
        "\nE6 RAW TREATMENT SUCCESS PREDICTIONS"
    )

    print(
        "-" * 70
    )

    results = []

    for _, candidate in enriched_candidates.iterrows():

        treatment_id = candidate["treatment_id"]

        prediction = predict_treatment_success(
            context,
            treatment_id
        )

        results.append({
            "treatment_id": treatment_id,
            "treatment_name": candidate["treatment_name"],
            "raw_success_probability": prediction[
                "raw_success_probability"
            ]
            
        })

    if not results:

        raise ValueError(
            "E6 generated no treatment predictions."
        )

    return results

# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    print("=" * 70)
    print("E6 - TREATMENT SUCCESS MODEL")
    print("=" * 70)

    # ------------------------------------------------------
    # Step 1: Train/rebuild model
    # ------------------------------------------------------

    model, data, feature_names = train_model()

    # ------------------------------------------------------
    # Step 2: Validate saved artifact
    # ------------------------------------------------------

    print(
        "\nValidating saved model artifact..."
    )

    validate_model_artifact()

    print(
        "Model artifact: VALID"
    )

    # ------------------------------------------------------
    # Step 3: Validate E1 → E2 → E3 → E4 → E6
    # ------------------------------------------------------

    results = run_e6_pipeline_test()

    # ------------------------------------------------------
    # Final validation
    # ------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "E6 VALIDATION: PASSED"
    )

    print(
        "=" * 70
    )
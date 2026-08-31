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
import numpy as np
import joblib

from sqlalchemy import text

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score,
)

from database import get_engine


# ==========================================================
# LOAD DATA FROM DATABASE
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
# PREPARE SYMPTOM FEATURES
# ==========================================================

def create_symptom_features(
    symptoms,
    symptom_master
):

    # Map S001 → Fever, etc.
    symptoms = symptoms.merge(
        symptom_master,
        on="symptom_id",
        how="left"
    )

    # Convert symptom records into one-hot columns
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
# PREPARE COMPLETE TRAINING DATASET
# ==========================================================

def prepare_dataset():

    (
        encounters,
        treatments,
        symptoms,
        symptom_master,
        treatment_master,
    ) = load_data()

    # ------------------------------------------------------
    # Create symptom columns
    # ------------------------------------------------------

    symptom_features = create_symptom_features(
        symptoms,
        symptom_master
    )

    # ------------------------------------------------------
    # Merge patient + symptoms
    # ------------------------------------------------------

    data = encounters.merge(
        symptom_features,
        on="encounter_id",
        how="left"
    )

    # ------------------------------------------------------
    # Merge administered treatments
    # ------------------------------------------------------

    data = data.merge(
        treatments,
        on="encounter_id",
        how="inner"
    )

    # ------------------------------------------------------
    # Treatment names
    # ------------------------------------------------------

    data = data.merge(
        treatment_master,
        on="treatment_id",
        how="left"
    )

    # ------------------------------------------------------
    # Define target
    #
    # Recovered = successful outcome
    # Stable / Referred = non-success for this prototype
    # ------------------------------------------------------

    data["treatment_success"] = (
        data["discharge_status"]
        == "Recovered"
    ).astype(int)

    # ------------------------------------------------------
    # Fill missing symptom values
    # ------------------------------------------------------

    symptom_names = symptom_master[
        "symptom_name"
    ].tolist()

    for symptom in symptom_names:

        if symptom not in data.columns:

            data[symptom] = 0

    data[symptom_names] = (
        data[symptom_names]
        .fillna(0)
        .astype(int)
    )

    # ------------------------------------------------------
    # Select patient features
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

    # ------------------------------------------------------
    # One-hot encode categorical variables
    # ------------------------------------------------------

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

    print("=" * 60)
    print("OBJECTIVE E - TREATMENT SUCCESS MODEL")
    print("=" * 60)

    print(
        f"\nTraining records: {len(data)}"
    )

    print(
        f"Features: {len(feature_names)}"
    )

    print(
        "\nOutcome distribution:"
    )

    print(
        y.value_counts()
        .rename({
            0: "Not Success",
            1: "Success"
        })
        .to_string()
    )

   
    # ------------------------------------------------------
    # Train/test split by encounter
    #
    # All treatment rows belonging to the same encounter
    # stay in either training OR testing.
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

    # Verify that no encounter appears in both sets

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
            "some encounters appear in both train and test."
        )

    # ------------------------------------------------------
    # Random Forest
    # ------------------------------------------------------

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_split=5,
        random_state=42,
        class_weight="balanced"
    )

    print(
        "\nTraining Random Forest..."
    )

    model.fit(
        X_train,
        y_train
    )

    print(
        "Model trained successfully."
    )

    # ------------------------------------------------------
    # Predictions
    # ------------------------------------------------------

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    # ------------------------------------------------------
    # Evaluation
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

    print(
        "\nClassification report:"
    )

    print(
        classification_report(
            y_test,
            predictions
        )
    )

    # ------------------------------------------------------
    # Feature importance
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

    print(
        "\nTop 15 important features:"
    )

    print(
        importance
        .head(15)
        .to_string(index=False)
    )

    # ------------------------------------------------------
    # Save trained model
    # ------------------------------------------------------

    joblib.dump(
        {
            "model": model,
            "feature_names": feature_names,
        },
        "treatment_success_model.pkl"
    )

    print(
        "\nModel saved as "
        "treatment_success_model.pkl"
    )

    return (
        model,
        data,
        feature_names
    )


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    train_model()
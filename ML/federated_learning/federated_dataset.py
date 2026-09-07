"""
Objective C - C3
Standardized Federated Dataset

Ensures every hospital uses the exact same:
    - feature columns
    - target columns
    - column ordering
    - data types
    - binary encoding
    - matrix dimensions
"""

import numpy as np
import pandas as pd


# ==========================================================
# STANDARD FEDERATED FEATURES
# ==========================================================

FEDERATED_FEATURE_COLUMNS = [
    "age",
    "temperature",
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "spo2",
    "symptom_onset_days",
    "travel_history",
    "vaccination_status",
]


# ==========================================================
# STANDARD FEDERATED TARGETS
# ==========================================================

FEDERATED_TARGET_COLUMNS = [
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


EXPECTED_FEATURE_COUNT = 10
EXPECTED_TARGET_COUNT = 27


# ==========================================================
# STANDARD DATASET VALIDATION
# ==========================================================

def validate_standard_schema(df):
    """
    Validate that the dataframe contains exactly the
    required federated features and targets.
    """

    required_columns = (
        FEDERATED_FEATURE_COLUMNS
        + FEDERATED_TARGET_COLUMNS
    )

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing federated columns: "
            f"{missing_columns}"
        )

    return True


# ==========================================================
# FEATURE STANDARDIZATION
# ==========================================================

def standardize_features(df):
    """
    Extract features in the canonical order and
    convert them to numeric values.
    """

    validate_standard_schema(df)

    X = df[
        FEDERATED_FEATURE_COLUMNS
    ].copy()

    # ------------------------------------------------------
    # Numeric features
    # ------------------------------------------------------

    numeric_columns = [
        "age",
        "temperature",
        "heart_rate",
        "respiratory_rate",
        "systolic_bp",
        "diastolic_bp",
        "spo2",
        "symptom_onset_days",
    ]

    for column in numeric_columns:

        X[column] = pd.to_numeric(
            X[column],
            errors="coerce",
        )

    # ------------------------------------------------------
    # Travel history
    # ------------------------------------------------------

    X["travel_history"] = (
        X["travel_history"]
        .map({
            True: 1,
            False: 0,
            "True": 1,
            "False": 0,
            "true": 1,
            "false": 0,
            1: 1,
            0: 0,
        })
        .fillna(0)
        .astype(np.float32)
    )

    # ------------------------------------------------------
    # Vaccination status
    # ------------------------------------------------------

    X["vaccination_status"] = (
        X["vaccination_status"]
        .map({
            "Vaccinated": 1,
            "Not Vaccinated": 0,
            "vaccinated": 1,
            "not vaccinated": 0,
            True: 1,
            False: 0,
            1: 1,
            0: 0,
        })
        .fillna(0)
        .astype(np.float32)
    )

    # ------------------------------------------------------
    # Missing numeric values
    # ------------------------------------------------------

    X[numeric_columns] = (
        X[numeric_columns]
        .fillna(0)
    )

    # ------------------------------------------------------
    # Final numeric representation
    # ------------------------------------------------------

    X = X.astype(np.float32)

    return X


# ==========================================================
# TARGET STANDARDIZATION
# ==========================================================

def standardize_targets(df):
    """
    Extract the 27 symptom targets in the canonical order.

    Every target is represented as binary:
        0 = symptom absent
        1 = symptom present
    """

    validate_standard_schema(df)

    y = df[
        FEDERATED_TARGET_COLUMNS
    ].copy()

    for column in FEDERATED_TARGET_COLUMNS:

        y[column] = pd.to_numeric(
            y[column],
            errors="coerce",
        )

    y = (
        y.fillna(0)
        .clip(lower=0, upper=1)
        .astype(np.float32)
    )

    return y


# ==========================================================
# COMPLETE STANDARDIZATION
# ==========================================================

def standardize_federated_dataset(df):
    """
    Convert a minimized hospital dataframe into the
    canonical federated representation.
    """

    X = standardize_features(df)

    y = standardize_targets(df)

    if len(X) != len(y):
        raise ValueError(
            "Feature and target row counts do not match."
        )

    if X.shape[1] != EXPECTED_FEATURE_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_FEATURE_COUNT} "
            f"features, got {X.shape[1]}."
        )

    if y.shape[1] != EXPECTED_TARGET_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_TARGET_COUNT} "
            f"targets, got {y.shape[1]}."
        )

    return X, y


# ==========================================================
# STANDARDIZATION AUDIT
# ==========================================================

def audit_federated_dataset(
    X,
    y,
    hospital_id=None,
):
    """
    Return a structured audit of the standardized
    federated dataset.
    """

    issues = []

    # ------------------------------------------------------
    # DIMENSION CHECKS
    # ------------------------------------------------------

    if X.shape[1] != EXPECTED_FEATURE_COUNT:
        issues.append(
            f"Incorrect feature count: "
            f"expected {EXPECTED_FEATURE_COUNT}, "
            f"got {X.shape[1]}."
        )

    if y.shape[1] != EXPECTED_TARGET_COUNT:
        issues.append(
            f"Incorrect target count: "
            f"expected {EXPECTED_TARGET_COUNT}, "
            f"got {y.shape[1]}."
        )

    if len(X) != len(y):
        issues.append(
            "Feature/target row count mismatch."
        )

    # ------------------------------------------------------
    # COLUMN ORDER CHECKS
    # ------------------------------------------------------

    feature_order_correct = (
        list(X.columns)
        == FEDERATED_FEATURE_COLUMNS
    )

    target_order_correct = (
        list(y.columns)
        == FEDERATED_TARGET_COLUMNS
    )

    if not feature_order_correct:
        issues.append(
            "Feature column ordering is incorrect."
        )

    if not target_order_correct:
        issues.append(
            "Target column ordering is incorrect."
        )

    # ------------------------------------------------------
    # NUMERIC FEATURE CHECK
    # ------------------------------------------------------

    numeric_features = all(
        pd.api.types.is_numeric_dtype(
            X[column]
        )
        for column in X.columns
    )

    if not numeric_features:
        issues.append(
            "One or more features are not numeric."
        )

    # ------------------------------------------------------
    # NUMERIC TARGET CHECK
    # ------------------------------------------------------

    numeric_targets = all(
        pd.api.types.is_numeric_dtype(
            y[column]
        )
        for column in y.columns
    )

    if not numeric_targets:
        issues.append(
            "One or more targets are not numeric."
        )

    # ------------------------------------------------------
    # BINARY TARGET CHECK
    # ------------------------------------------------------

    target_values = np.unique(
        y.to_numpy()
    )

    invalid_targets = [
        value
        for value in target_values
        if value not in (0, 1)
    ]

    binary_targets = (
        len(invalid_targets) == 0
    )

    if not binary_targets:
        issues.append(
            "Targets contain values other than 0/1: "
            f"{invalid_targets}"
        )

    # ------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------

    return {
        "hospital_id": hospital_id,

        "feature_count": X.shape[1],

        "target_count": y.shape[1],

        "record_count": len(X),

        "feature_order_correct":
            feature_order_correct,

        "target_order_correct":
            target_order_correct,

        "numeric_features":
            numeric_features,

        "numeric_targets":
            numeric_targets,

        "binary_targets":
            binary_targets,

        "passed":
            len(issues) == 0,

        "issues":
            issues,
    }
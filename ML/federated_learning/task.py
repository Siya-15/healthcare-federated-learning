"""
Federated Learning Task Definition

Objective C:
Privacy-Preserving Federated Healthcare Learning

C1:
Data minimization

C3:
Standardized federated dataset

The federated model uses:
    10 input features
    27 symptom targets
"""

import os

import pandas as pd

from sklearn.model_selection import train_test_split


# ==========================================================
# C3 STANDARDIZED FEDERATED DATASET
# ==========================================================

from .federated_dataset import (
    FEDERATED_FEATURE_COLUMNS,
    FEDERATED_TARGET_COLUMNS,
    standardize_federated_dataset,
)


# ==========================================================
# C1 DATA MINIMIZATION
# ==========================================================

from ..privacy.data_minimization_enforcer import (
    enforce_federated_minimization,
)


# ==========================================================
# DATA LOCATION
# ==========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ==========================================================
# MODEL DIMENSIONS
# ==========================================================

INPUT_DIM = len(
    FEDERATED_FEATURE_COLUMNS
)

OUTPUT_DIM = len(
    FEDERATED_TARGET_COLUMNS
)


# ==========================================================
# LOAD HOSPITAL DATA
# ==========================================================

def load_data(hospital_id):
    """
    Load, minimize, standardize, and split one
    hospital's local federated dataset.

    Pipeline:

        Hospital CSV
              ↓
        C1 minimization
              ↓
        C3 standardization
              ↓
        Train/test split
              ↓
        NumPy arrays
    """

    filename = os.path.join(
        BASE_DIR,
        f"ml_data_{hospital_id}.csv"
    )

    if not os.path.exists(filename):

        raise FileNotFoundError(
            f"Hospital dataset not found: "
            f"{filename}"
        )

    # ------------------------------------------------------
    # LOAD LOCAL HOSPITAL DATA
    # ------------------------------------------------------

    df = pd.read_csv(
        filename
    )

    print(
        f"[{hospital_id}] "
        f"Original records: {len(df)}"
    )

    print(
        f"[{hospital_id}] "
        f"Original columns: {len(df.columns)}"
    )

    # ------------------------------------------------------
    # C1 - DATA MINIMIZATION
    # ------------------------------------------------------

    df = enforce_federated_minimization(
        df
    )

    print(
        f"[{hospital_id}] "
        f"After C1 minimization: "
        f"{len(df.columns)} columns"
    )

    # ------------------------------------------------------
    # C3 - STANDARDIZATION
    # ------------------------------------------------------

    X, y = standardize_federated_dataset(
        df
    )

    print(
        f"[{hospital_id}] "
        f"C3 standardized features: "
        f"{X.shape[1]}"
    )

    print(
        f"[{hospital_id}] "
        f"C3 standardized targets: "
        f"{y.shape[1]}"
    )

    # ------------------------------------------------------
    # VALIDATE MODEL DIMENSIONS
    # ------------------------------------------------------

    if X.shape[1] != INPUT_DIM:

        raise ValueError(
            f"[{hospital_id}] "
            f"Expected {INPUT_DIM} features, "
            f"got {X.shape[1]}"
        )

    if y.shape[1] != OUTPUT_DIM:

        raise ValueError(
            f"[{hospital_id}] "
            f"Expected {OUTPUT_DIM} targets, "
            f"got {y.shape[1]}"
        )

    # ------------------------------------------------------
    # TRAIN / TEST SPLIT
    # ------------------------------------------------------
    #
    # Keep the existing project behavior:
    # 80% training
    # 20% testing
    # No shuffle
    #
    # This preserves temporal ordering in the
    # locally generated hospital data.
    # ------------------------------------------------------

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = train_test_split(
        X,
        y,
        test_size=0.2,
        shuffle=False,
    )

    # ------------------------------------------------------
    # CONVERT TO NUMPY
    # ------------------------------------------------------
    #
    # The PyTorch model currently expects
    # NumPy-compatible matrices.
    # ------------------------------------------------------

    X_train = X_train.to_numpy()
    X_test = X_test.to_numpy()

    y_train = y_train.to_numpy()
    y_test = y_test.to_numpy()

    # ------------------------------------------------------
    # FINAL VALIDATION
    # ------------------------------------------------------

    if X_train.shape[1] != 10:

        raise ValueError(
            f"[{hospital_id}] "
            "Training data must contain "
            "exactly 10 features."
        )

    if X_test.shape[1] != 10:

        raise ValueError(
            f"[{hospital_id}] "
            "Test data must contain "
            "exactly 10 features."
        )

    if y_train.shape[1] != 27:

        raise ValueError(
            f"[{hospital_id}] "
            "Training targets must contain "
            "exactly 27 symptoms."
        )

    if y_test.shape[1] != 27:

        raise ValueError(
            f"[{hospital_id}] "
            "Test targets must contain "
            "exactly 27 symptoms."
        )

    if len(X_train) != len(y_train):

        raise ValueError(
            f"[{hospital_id}] "
            "Training feature/target row mismatch."
        )

    if len(X_test) != len(y_test):

        raise ValueError(
            f"[{hospital_id}] "
            "Test feature/target row mismatch."
        )

    # ------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------

    print(
        f"[{hospital_id}] "
        f"X_train: {X_train.shape}"
    )

    print(
        f"[{hospital_id}] "
        f"X_test: {X_test.shape}"
    )

    print(
        f"[{hospital_id}] "
        f"y_train: {y_train.shape}"
    )

    print(
        f"[{hospital_id}] "
        f"y_test: {y_test.shape}"
    )

    return (
        X_train,
        X_test,
        y_train,
        y_test,
    )


# ==========================================================
# MODEL INFORMATION
# ==========================================================

def get_feature_columns():
    """
    Return the canonical federated feature ordering.
    """

    return list(
        FEDERATED_FEATURE_COLUMNS
    )


def get_target_columns():
    """
    Return the canonical federated target ordering.
    """

    return list(
        FEDERATED_TARGET_COLUMNS
    )


def get_input_dimension():
    """
    Return federated model input dimension.
    """

    return INPUT_DIM


def get_output_dimension():
    """
    Return federated model output dimension.
    """

    return OUTPUT_DIM
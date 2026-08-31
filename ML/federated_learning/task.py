import numpy as np
import pandas as pd

from pytorch_tabnet.tab_model import TabNetClassifier


# ==========================================================
# INPUT FEATURES
# ==========================================================

FEATURE_COLUMNS = [
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
# MULTI-LABEL SYMPTOM TARGETS
# ==========================================================

TARGET_COLUMNS = [
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
# CREATE MODEL
# ==========================================================

def create_model():

    return TabNetClassifier(
        n_d=16,
        n_a=16,
        n_steps=3,
        gamma=1.3,
        lambda_sparse=1e-4,
        seed=42,
        verbose=0,
    )


# ==========================================================
# PREPARE FEATURES
# ==========================================================

def prepare_features(df):

    X = df[FEATURE_COLUMNS].copy()

    # ------------------------------------------------------
    # Boolean travel history
    # ------------------------------------------------------

    X["travel_history"] = (
        X["travel_history"]
        .map({
            True: 1,
            False: 0,
            "True": 1,
            "False": 0,
        })
        .fillna(0)
        .astype(int)
    )

    # ------------------------------------------------------
    # Vaccination status
    # ------------------------------------------------------

    X["vaccination_status"] = (
        X["vaccination_status"]
        .map({
            "Vaccinated": 1,
            "Not Vaccinated": 0,
        })
        .fillna(0)
        .astype(int)
    )

    # ------------------------------------------------------
    # Missing values
    # ------------------------------------------------------

    X = X.fillna(0)

    return X.values.astype(np.float32)


# ==========================================================
# LOAD HOSPITAL DATA
# ==========================================================

def load_data(hospital_id):

    filename = f"ml_data_{hospital_id}.csv"

    df = pd.read_csv(filename)

    # ------------------------------------------------------
    # Validate columns
    # ------------------------------------------------------

    required_columns = (
        FEATURE_COLUMNS + TARGET_COLUMNS
    )

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            f"{hospital_id}: Missing columns: {missing}"
        )

    # ------------------------------------------------------
    # Features
    # ------------------------------------------------------

    X = prepare_features(df)

    # ------------------------------------------------------
    # Multi-label targets
    #
    # Each patient can have multiple symptoms.
    # ------------------------------------------------------

    y = (
        df[TARGET_COLUMNS]
        .fillna(0)
        .astype(int)
        .values
    )

    # ------------------------------------------------------
    # 80/20 split
    # ------------------------------------------------------

    split = int(len(X) * 0.8)

    X_train = X[:split]
    X_test = X[split:]

    y_train = y[:split]
    y_test = y[split:]

    return (
        X_train,
        X_test,
        y_train,
        y_test,
    )
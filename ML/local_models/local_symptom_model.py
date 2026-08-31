import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

from pytorch_tabnet.tab_model import TabNetClassifier


# ==========================================================
# CONFIGURATION
# ==========================================================

HOSPITAL_ID = "H001"
FILE = f"ml_data_{HOSPITAL_ID}.csv"


# ==========================================================
# LOAD DATA
# ==========================================================

df = pd.read_csv(FILE)

print("=" * 60)
print("LOCAL SYMPTOM CLASSIFICATION MODEL")
print("=" * 60)

print(f"Hospital: {HOSPITAL_ID}")
print(f"Records : {len(df)}")


# ==========================================================
# COLUMNS
# ==========================================================

base_columns = [
    "encounter_id",
    "hospital_id",
    "age",
    "gender",
    "occupation",
    "temperature",
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "spo2",
    "disease_id",
    "severity_id",
    "admission_status",
    "visit_type",
    "symptom_onset_days",
    "travel_history",
    "vaccination_status",
    "discharge_status",
    "recovery_days"
]


# Everything outside the encounter columns
# is a symptom label.

symptom_columns = [
    column
    for column in df.columns
    if column not in base_columns
]


print(f"\nNumber of symptom labels: {len(symptom_columns)}")


# ==========================================================
# FEATURES
# ==========================================================

feature_columns = [
    "age",
    "temperature",
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "spo2",
    "symptom_onset_days",
    "travel_history",
    "vaccination_status"
]

X = df[feature_columns].copy()


# ==========================================================
# PREPROCESSING
# ==========================================================

X = X.fillna(0)

X["travel_history"] = (
    X["travel_history"]
    .map({
        True: 1,
        False: 0,
        "True": 1,
        "False": 0
    })
    .fillna(0)
    .astype(int)
)

X["vaccination_status"] = (
    X["vaccination_status"]
    .map({
        "Vaccinated": 1,
        "Not Vaccinated": 0
    })
    .fillna(0)
    .astype(int)
)


X = X.values.astype(np.float32)


# ==========================================================
# TRAIN / TEST SPLIT
# ==========================================================

indices = np.arange(len(df))

train_indices, test_indices = train_test_split(
    indices,
    test_size=0.20,
    random_state=42
)

X_train = X[train_indices]
X_test = X[test_indices]


print(f"Training records: {len(X_train)}")
print(f"Testing records : {len(X_test)}")


# ==========================================================
# TRAIN ONE MODEL PER SYMPTOM
# ==========================================================

local_models = {}

results = {}


for symptom in symptom_columns:

    print("\n" + "-" * 60)
    print(f"Training model for: {symptom}")
    print("-" * 60)

    y = df[symptom].values.astype(int)

    y_train = y[train_indices]
    y_test = y[test_indices]


    # ------------------------------------------------------
    # Check that both classes exist
    # ------------------------------------------------------

    if len(np.unique(y_train)) < 2:

        print(
            f"Skipping {symptom}: "
            "training data contains only one class."
        )

        continue


    # ------------------------------------------------------
    # Create TabNet model
    # ------------------------------------------------------

    model = TabNetClassifier(
        n_d=16,
        n_a=16,
        n_steps=3,
        gamma=1.3,
        lambda_sparse=1e-4,
        seed=42,
        verbose=0
    )


    # ------------------------------------------------------
    # Train
    # ------------------------------------------------------

    model.fit(
        X_train,
        y_train,
        eval_set=[
            (X_test, y_test)
        ],
        max_epochs=20,
        patience=5,
        batch_size=128,
        virtual_batch_size=64
    )


    # ------------------------------------------------------
    # Predict
    # ------------------------------------------------------

    predictions = model.predict(X_test)


    # ------------------------------------------------------
    # Evaluate
    # ------------------------------------------------------

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )


    print(
        f"F1 Score: {f1:.4f}"
    )


    # ------------------------------------------------------
    # Store model
    # ------------------------------------------------------

    local_models[symptom] = model

    results[symptom] = f1


# ==========================================================
# SUMMARY
# ==========================================================

print("\n" + "=" * 60)
print("LOCAL MODEL SUMMARY")
print("=" * 60)

print(
    f"Successfully trained models: "
    f"{len(local_models)} / {len(symptom_columns)}"
)


for symptom, score in results.items():

    print(
        f"{symptom:25s} → F1: {score:.4f}"
    )


# ==========================================================
# FEDERATION-READY MODEL PARAMETERS
# ==========================================================

print("\n" + "=" * 60)
print("FEDERATION CHECK")
print("=" * 60)


for symptom, model in local_models.items():

    parameters = model.network.state_dict()

    print(
        f"{symptom:25s} → "
        f"{len(parameters)} parameter tensors"
    )


print("\nLocal model training completed.")
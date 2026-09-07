import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor


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
# LOAD SYMPTOM DATA
# ==========================================================

def load_symptom_data(hospital_id):

    filename = f"ml_data_{hospital_id}.csv"

    df = pd.read_csv(filename)

    missing = [
        symptom
        for symptom in SYMPTOM_COLUMNS
        if symptom not in df.columns
    ]

    if missing:

        raise ValueError(
            f"{hospital_id}: Missing symptom columns: "
            f"{missing}"
        )

    X = (
        df[SYMPTOM_COLUMNS]
        .fillna(0)
        .astype(float)
        .values
    )

    return df, X


# ==========================================================
# CREATE AUTOENCODER
# ==========================================================

def create_autoencoder():

    return MLPRegressor(
        hidden_layer_sizes=(16, 8, 16),
        activation="relu",
        solver="adam",
        learning_rate_init=0.001,
        max_iter=500,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.2,
        n_iter_no_change=20,
    )


# ==========================================================
# TRAIN ON HISTORICAL BASELINE + SCORE CURRENT DATA
# ==========================================================

def detect_anomalies(
    hospital_id,
    baseline_end="2026-07-31"
):

    df, _ = load_symptom_data(hospital_id)

    # ------------------------------------------------------
    # Validate timestamp
    # ------------------------------------------------------

    if "visit_timestamp" not in df.columns:

        raise ValueError(
            f"{hospital_id}: visit_timestamp is required "
            "for temporal anomaly detection."
        )

    df["visit_timestamp"] = pd.to_datetime(
        df["visit_timestamp"]
    )

    baseline_end = pd.Timestamp(
        baseline_end
    )

    # ------------------------------------------------------
    # Split historical baseline and current window
    # ------------------------------------------------------

    baseline_df = df[
        df["visit_timestamp"] <= baseline_end
    ].copy()

    current_df = df[
        df["visit_timestamp"] > baseline_end
    ].copy()

    if baseline_df.empty:

        raise ValueError(
            f"{hospital_id}: Historical baseline is empty."
        )

    if current_df.empty:

        raise ValueError(
            f"{hospital_id}: Current surveillance window is empty."
        )

    # ------------------------------------------------------
    # Extract symptom features
    # ------------------------------------------------------

    X_baseline = (
        baseline_df[SYMPTOM_COLUMNS]
        .fillna(0)
        .astype(float)
        .values
    )

    X_current = (
        current_df[SYMPTOM_COLUMNS]
        .fillna(0)
        .astype(float)
        .values
    )

    # ------------------------------------------------------
    # Train autoencoder ONLY on historical baseline
    # ------------------------------------------------------

    model = create_autoencoder()

    model.fit(
        X_baseline,
        X_baseline
    )

    # ------------------------------------------------------
    # Calculate baseline reconstruction errors
    #
    # These establish the normal error distribution.
    # ------------------------------------------------------

    baseline_reconstructed = model.predict(
        X_baseline
    )

    baseline_error = np.mean(
        (X_baseline - baseline_reconstructed) ** 2,
        axis=1
    )

    # ------------------------------------------------------
    # Calculate current reconstruction errors
    # ------------------------------------------------------

    current_reconstructed = model.predict(
        X_current
    )

    current_error = np.mean(
        (X_current - current_reconstructed) ** 2,
        axis=1
    )

    # ------------------------------------------------------
    # Determine threshold from HISTORICAL data
    #
    # The threshold is no longer influenced by the
    # current surveillance window.
    # ------------------------------------------------------

    threshold = np.percentile(
        baseline_error,
        95
    )

    is_anomaly = (
        current_error >= threshold
    )

    # ------------------------------------------------------
    # Create results for CURRENT encounters only
    # ------------------------------------------------------

    results = current_df[
        [
            "encounter_id",
            "hospital_id",
            "visit_timestamp",
            "disease_id",
            "severity_id",
        ]
    ].copy()

    results["anomaly_score"] = (
        current_error
    )

    results["anomaly_threshold"] = (
        threshold
    )

    results["is_anomalous"] = (
        is_anomaly
    )

    return results, model


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    hospital_id = "H001"

    results, model = detect_anomalies(
        hospital_id
    )

    print("=" * 60)
    print("EMERGING SYMPTOM / ANOMALY DETECTION")
    print("=" * 60)

    print(
        f"\nHospital: {hospital_id}"
    )

    print(
        f"\nCurrent records analysed: {len(results)}"
    )

    print(
        f"Anomalies detected: "
        f"{results['is_anomalous'].sum()}"
    )

    print(
        f"\nAnomaly threshold: "
        f"{results['anomaly_threshold'].iloc[0]:.6f}"
    )

    

    print(
        "\nTop 10 unusual encounters:"
    )

    print(
        results
        .sort_values(
            "anomaly_score",
            ascending=False
        )
        .head(10)
        .to_string(index=False)
    )
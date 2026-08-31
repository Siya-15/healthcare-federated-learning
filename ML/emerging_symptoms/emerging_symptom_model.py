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
# TRAIN + SCORE
# ==========================================================

def detect_anomalies(hospital_id):

    df, X = load_symptom_data(hospital_id)

    # ------------------------------------------------------
    # Train autoencoder
    #
    # Input = symptom vector
    # Target = same symptom vector
    # ------------------------------------------------------

    model = create_autoencoder()

    model.fit(
        X,
        X
    )

    # ------------------------------------------------------
    # Reconstruct symptom vectors
    # ------------------------------------------------------

    reconstructed = model.predict(X)

    # ------------------------------------------------------
    # Reconstruction error
    # ------------------------------------------------------

    reconstruction_error = np.mean(
        (X - reconstructed) ** 2,
        axis=1
    )

    # ------------------------------------------------------
    # Determine anomaly threshold
    #
    # Top 5% most unusual cases are flagged.
    # ------------------------------------------------------

    threshold = np.percentile(
        reconstruction_error,
        95
    )

    is_anomaly = (
        reconstruction_error >= threshold
    )

    # ------------------------------------------------------
    # Create results
    # ------------------------------------------------------

    results = df[
        [
            "encounter_id",
            "hospital_id",
            "disease_id",
            "severity_id",
        ]
    ].copy()

    results["anomaly_score"] = (
        reconstruction_error
    )

    results["anomaly_threshold"] = threshold

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
        f"Records analysed: {len(results)}"
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
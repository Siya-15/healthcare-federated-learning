import pandas as pd

from .emerging_symptom_model import (
    SYMPTOM_COLUMNS,
    detect_anomalies,
)


# ==========================================================
# FIND RECURRING ANOMALOUS SYMPTOM PATTERNS
# ==========================================================

def find_patterns(hospital_id):

    results, _ = detect_anomalies(hospital_id)

    # Load original data to get symptom columns
    df = pd.read_csv(
        f"ml_data_{hospital_id}.csv"
    )

    # ------------------------------------------------------
    # Keep only anomalous encounters
    # ------------------------------------------------------

    anomalous_ids = results.loc[
        results["is_anomalous"],
        "encounter_id"
    ]

    anomalous_df = df[
        df["encounter_id"].isin(anomalous_ids)
    ].copy()

    # ------------------------------------------------------
    # Create a symptom-pattern string
    # ------------------------------------------------------

    def get_pattern(row):

        symptoms = [
            symptom
            for symptom in SYMPTOM_COLUMNS
            if row[symptom] == 1
        ]

        return " + ".join(symptoms)

    anomalous_df["symptom_pattern"] = (
        anomalous_df.apply(
            get_pattern,
            axis=1
        )
    )

    # ------------------------------------------------------
    # Count recurring patterns
    # ------------------------------------------------------

    pattern_counts = (
        anomalous_df[
            "symptom_pattern"
        ]
        .value_counts()
        .reset_index()
    )

    pattern_counts.columns = [
        "symptom_pattern",
        "occurrences"
    ]

    # ------------------------------------------------------
    # Only keep patterns appearing more than once
    # ------------------------------------------------------

    recurring_patterns = pattern_counts[
        pattern_counts["occurrences"] >= 2
    ].copy()

    return (
        anomalous_df,
        recurring_patterns
    )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    hospital_id = "H001"

    anomalous_df, patterns = (
        find_patterns(hospital_id)
    )

    print("=" * 60)
    print("RECURRING ANOMALOUS SYMPTOM PATTERNS")
    print("=" * 60)

    print(
        f"\nHospital: {hospital_id}"
    )

    print(
        f"Anomalous encounters: "
        f"{len(anomalous_df)}"
    )

    print(
        f"Recurring patterns: "
        f"{len(patterns)}"
    )

    print(
        "\nMost common unusual patterns:"
    )

    print(
        patterns
        .head(15)
        .to_string(index=False)
    )
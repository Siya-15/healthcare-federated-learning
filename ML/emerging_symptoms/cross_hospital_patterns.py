import pandas as pd

from .emerging_symptom_model import (
    SYMPTOM_COLUMNS,
    detect_anomalies,
)


# ==========================================================
# FIND ANOMALOUS PATTERNS FOR ONE HOSPITAL
# ==========================================================

def get_hospital_patterns(hospital_id):

    results, _ = detect_anomalies(hospital_id)

    df = pd.read_csv(
        f"ml_data_{hospital_id}.csv"
    )

    anomalous_ids = results.loc[
        results["is_anomalous"],
        "encounter_id"
    ]

    anomalous_df = df[
        df["encounter_id"].isin(anomalous_ids)
    ].copy()

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

    return anomalous_df[
        [
            "hospital_id",
            "encounter_id",
            "symptom_pattern",
        ]
    ]


# ==========================================================
# CROSS-HOSPITAL ANALYSIS
# ==========================================================

def analyze_all_hospitals():

    all_patterns = []

    hospitals = [
        f"H{i:03d}"
        for i in range(1, 11)
    ]

    for hospital_id in hospitals:

        print(
            f"Processing {hospital_id}..."
        )

        hospital_patterns = (
            get_hospital_patterns(
                hospital_id
            )
        )

        all_patterns.append(
            hospital_patterns
        )

    combined = pd.concat(
        all_patterns,
        ignore_index=True
    )

    # ------------------------------------------------------
    # Count each pattern per hospital
    # ------------------------------------------------------

    hospital_counts = (
        combined
        .groupby(
            [
                "symptom_pattern",
                "hospital_id",
            ]
        )
        .size()
        .reset_index(
            name="occurrences"
        )
    )

    # ------------------------------------------------------
    # Count number of hospitals affected
    # ------------------------------------------------------

    cross_hospital = (
        hospital_counts
        .groupby("symptom_pattern")
        .agg(
            hospitals_affected=(
                "hospital_id",
                "nunique"
            ),
            total_occurrences=(
                "occurrences",
                "sum"
            ),
        )
        .reset_index()
    )

    # ------------------------------------------------------
    # Keep patterns occurring in at least 2 hospitals
    # ------------------------------------------------------

    cross_hospital = cross_hospital[
        cross_hospital[
            "hospitals_affected"
        ] >= 2
    ].copy()

    # ------------------------------------------------------
    # Sort strongest cross-hospital signals first
    # ------------------------------------------------------

    cross_hospital = (
        cross_hospital
        .sort_values(
            [
                "hospitals_affected",
                "total_occurrences",
            ],
            ascending=False
        )
    )

    return (
        combined,
        hospital_counts,
        cross_hospital,
    )


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("CROSS-HOSPITAL ANOMALOUS SYMPTOM ANALYSIS")
    print("=" * 60)

    (
        combined,
        hospital_counts,
        cross_hospital,
    ) = analyze_all_hospitals()

    print(
        "\nCross-hospital patterns found:",
        len(cross_hospital)
    )

    print(
        "\nTop cross-hospital signals:"
    )

    print(
        cross_hospital
        .head(15)
        .to_string(index=False)
    )

    # ------------------------------------------------------
    # Save results
    # ------------------------------------------------------

    cross_hospital.to_csv(
        "cross_hospital_symptom_patterns.csv",
        index=False
    )

    hospital_counts.to_csv(
        "hospital_symptom_pattern_counts.csv",
        index=False
    )

    print(
        "\nResults saved successfully."
    )
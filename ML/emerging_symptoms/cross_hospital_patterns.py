from pathlib import Path

import pandas as pd

from .emerging_symptom_model import (
    SYMPTOM_COLUMNS,
    detect_anomalies,
)


# ==========================================================
# OUTPUT LOCATION
#
# Anchored to ML/data so the artifacts always land in the
# same place, whatever working directory the script was
# launched from.
# ==========================================================

DATA_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
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

    # ------------------------------------------------------
    # Per-hospital summary
    #
    # detect_anomalies flags a fixed top 5% of encounters,
    # so anomalies_flagged scales with the dataset size by
    # construction and is not itself an outbreak signal.
    # recurring_patterns is the figure worth reporting.
    # ------------------------------------------------------

    pattern_counts = (
        anomalous_df["symptom_pattern"]
        .value_counts()
    )

    summary = {

        "hospital_id": hospital_id,

        "encounters_analysed": int(
            len(results)
        ),

        "anomalies_flagged": int(
            results["is_anomalous"].sum()
        ),

        "anomaly_threshold": float(
            results["anomaly_threshold"].iloc[0]
        ),

        "distinct_patterns": int(
            pattern_counts.size
        ),

        "recurring_patterns": int(
            (pattern_counts >= 2).sum()
        ),

    }

    patterns = anomalous_df[
        [
            "hospital_id",
            "encounter_id",
            "symptom_pattern",
        ]
    ]

    return patterns, summary


# ==========================================================
# CROSS-HOSPITAL ANALYSIS
# ==========================================================

def analyze_all_hospitals():

    all_patterns = []

    all_summaries = []

    hospitals = [
        f"H{i:03d}"
        for i in range(1, 11)
    ]

    for hospital_id in hospitals:

        print(
            f"Processing {hospital_id}..."
        )

        hospital_patterns, summary = (
            get_hospital_patterns(
                hospital_id
            )
        )

        all_patterns.append(
            hospital_patterns
        )

        all_summaries.append(
            summary
        )

    combined = pd.concat(
        all_patterns,
        ignore_index=True
    )

    anomaly_summary = pd.DataFrame(
        all_summaries
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
        anomaly_summary,
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
        anomaly_summary,
    ) = analyze_all_hospitals()

    print(
        "\nCross-hospital patterns found:",
        len(cross_hospital)
    )

    print(
        "\nPer-hospital summary:"
    )

    print(
        anomaly_summary
        .to_string(index=False)
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

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    cross_hospital.to_csv(
        DATA_DIR
        / "cross_hospital_symptom_patterns.csv",
        index=False
    )

    hospital_counts.to_csv(
        DATA_DIR
        / "hospital_symptom_pattern_counts.csv",
        index=False
    )

    anomaly_summary.to_csv(
        DATA_DIR
        / "hospital_anomaly_summary.csv",
        index=False
    )

    print(
        f"\nResults saved to {DATA_DIR}"
    )
"""
Objective A3 — Privacy-Preserving Cross-Hospital
Emerging Symptom Pattern Analysis

Pipeline:

    Hospital H001 ──┐
    Hospital H002 ──┤
    Hospital H003 ──┤
         ...        ├──> Local aggregate signals
    Hospital H010 ──┘
                         ↓
                  Cross-hospital analysis
                         ↓
              Geographic / institutional spread
                         ↓
                Objective A3 signal

IMPORTANT PRIVACY BOUNDARY
--------------------------

This module does NOT centrally collect patient-level
encounter records.

Each hospital first performs Objective A1/A2 locally.

Only aggregate pattern-level information is combined:

    - symptom pattern
    - hospital ID
    - prevalence
    - prevalence growth
    - anomalous occurrence count
    - persistence
    - emergence score
    - alert level

No patient IDs or individual encounters are used
by the cross-hospital aggregation layer.
"""

from pathlib import Path

import pandas as pd

from emerging_symptom_patterns import (
    analyze_temporal_patterns,
)


# ============================================================
# CONFIGURATION
# ============================================================

HOSPITALS = [
    f"H{i:03d}"
    for i in range(1, 11)
]

# Same baseline used by Objective A2
DEFAULT_BASELINE_END = "2026-07-31"

# A pattern must appear in at least this many hospitals
# to be considered a cross-hospital signal.
MIN_HOSPITALS_AFFECTED = 2

# Output directory
OUTPUT_DIR = Path(__file__).resolve().parent


# ============================================================
# LOCAL HOSPITAL ANALYSIS
# ============================================================

def analyze_hospital_locally(
    hospital_id,
    baseline_end=DEFAULT_BASELINE_END,
):
    """
    Run Objective A2 for one hospital.

    This represents processing that would conceptually
    happen inside the hospital/local node.

    The resulting dataframe contains only aggregate
    symptom-pattern information.

    Patient-level records are NOT returned.
    """

    print()
    print("=" * 80)
    print(
        f"LOCAL ANALYSIS: {hospital_id}"
    )
    print("=" * 80)

    result = analyze_temporal_patterns(
        hospital_id=hospital_id,
        baseline_end=baseline_end,
    )

    if result is None or result.empty:

        print(
            f"No emerging patterns found for "
            f"{hospital_id}."
        )

        return pd.DataFrame()

    # ========================================================
    # PRIVACY BOUNDARY
    # ========================================================
    #
    # Only aggregate fields are allowed to leave the
    # hospital-level analysis.
    #
    # Explicitly exclude:
    #
    #     encounter_id
    #     patient_id
    #     visit_timestamp
    #
    # ========================================================

    aggregate_columns = [

        "hospital_id",

        "symptom_pattern",

        "baseline_occurrences",

        "current_pattern_occurrences",

        "current_anomalous_occurrences",

        "baseline_prevalence",

        "current_prevalence",

        "prevalence_growth",

        "baseline_daily_average",

        "current_daily_average",

        "current_weekly_average",

        "current_week_count",

        "peak_weekly_count",

        "week_over_week_growth",

        "baseline_relative_growth",

        "persistence_weeks",

        "emergence_score",

        "alert_level",
    ]

    missing_columns = [
        column
        for column in aggregate_columns
        if column not in result.columns
    ]

    if missing_columns:

        raise ValueError(
            f"{hospital_id} A2 output is missing "
            f"required columns: {missing_columns}"
        )

    local_aggregate = result[
        aggregate_columns
    ].copy()

    # Ensure hospital ID is present and normalized
    local_aggregate[
        "hospital_id"
    ] = hospital_id

    print(
        f"Aggregate patterns produced: "
        f"{len(local_aggregate)}"
    )

    return local_aggregate


# ============================================================
# CROSS-HOSPITAL AGGREGATION
# ============================================================

def aggregate_cross_hospital_patterns(
    hospital_results
):
    """
    Combine aggregate pattern signals from multiple hospitals.

    Input:
        A list of hospital-level aggregate dataframes.

    Output:
        Cross-hospital summary dataframe.

    No patient-level information is processed here.
    """

    valid_results = [
        result
        for result in hospital_results
        if result is not None
        and not result.empty
    ]

    if not valid_results:

        return pd.DataFrame()

    combined = pd.concat(
        valid_results,
        ignore_index=True,
    )

    # ========================================================
    # HOSPITAL-LEVEL PATTERN SUMMARY
    # ========================================================
    #
    # Each row represents:
    #
    #     one hospital
    #     one symptom pattern
    #
    # There are no individual encounters here.
    # ========================================================

    hospital_counts = (
        combined
        .groupby(
            [
                "symptom_pattern",
                "hospital_id",
            ],
            as_index=False,
        )
        .agg(

            occurrences=(
                "current_anomalous_occurrences",
                "sum",
            ),

            current_prevalence=(
                "current_prevalence",
                "max",
            ),

            prevalence_growth=(
                "prevalence_growth",
                "max",
            ),

            persistence_weeks=(
                "persistence_weeks",
                "max",
            ),

            emergence_score=(
                "emergence_score",
                "max",
            ),
        )
    )

    # ========================================================
    # CROSS-HOSPITAL SUMMARY
    # ========================================================

    cross_hospital = (
        hospital_counts
        .groupby(
            "symptom_pattern",
            as_index=False,
        )
        .agg(

            hospitals_affected=(
                "hospital_id",
                "nunique",
            ),

            total_anomalous_occurrences=(
                "occurrences",
                "sum",
            ),

            mean_current_prevalence=(
                "current_prevalence",
                "mean",
            ),

            max_current_prevalence=(
                "current_prevalence",
                "max",
            ),

            mean_prevalence_growth=(
                "prevalence_growth",
                "mean",
            ),

            max_prevalence_growth=(
                "prevalence_growth",
                "max",
            ),

            mean_persistence_weeks=(
                "persistence_weeks",
                "mean",
            ),

            max_persistence_weeks=(
                "persistence_weeks",
                "max",
            ),

            mean_emergence_score=(
                "emergence_score",
                "mean",
            ),

            max_emergence_score=(
                "emergence_score",
                "max",
            ),
        )
    )

    # ========================================================
    # HOSPITAL COVERAGE
    # ========================================================

    total_hospitals = len(
        HOSPITALS
    )

    cross_hospital[
        "hospital_coverage"
    ] = (
        cross_hospital[
            "hospitals_affected"
        ]
        /
        total_hospitals
    )

    # ========================================================
    # SPREAD LEVEL
    # ========================================================

    def determine_spread_level(
        hospitals_affected
    ):
        """
        Determine how widely a pattern is distributed.

            1 hospital      = LOCAL
            2-3 hospitals   = LIMITED
            4-6 hospitals   = WIDESPREAD
            7+ hospitals    = MULTI-HOSPITAL
        """

        if hospitals_affected <= 1:

            return "LOCAL"

        if hospitals_affected <= 3:

            return "LIMITED"

        if hospitals_affected <= 6:

            return "WIDESPREAD"

        return "MULTI-HOSPITAL"

    cross_hospital[
        "spread_level"
    ] = (
        cross_hospital[
            "hospitals_affected"
        ]
        .apply(
            determine_spread_level
        )
    )

    # ========================================================
    # CROSS-HOSPITAL EMERGENCE SCORE
    # ========================================================
    #
    # We combine:
    #
    #   1. Hospital coverage        30%
    #   2. Mean local emergence     30%
    #   3. Mean prevalence growth   20%
    #   4. Persistence              20%
    #
    # This determines whether an emerging pattern
    # is becoming a broader surveillance signal.
    # ========================================================

    cross_hospital[
        "coverage_score"
    ] = (
        cross_hospital[
            "hospital_coverage"
        ]
        .clip(
            lower=0,
            upper=1,
        )
    )

    cross_hospital[
        "local_emergence_score"
    ] = (
        cross_hospital[
            "mean_emergence_score"
        ]
        .clip(
            lower=0,
            upper=100,
        )
        / 100
    )

    cross_hospital[
        "growth_score"
    ] = (
        cross_hospital[
            "mean_prevalence_growth"
        ]
        .clip(
            lower=0,
            upper=1,
        )
    )

    cross_hospital[
        "persistence_score"
    ] = (
        cross_hospital[
            "mean_persistence_weeks"
        ]
        .clip(
            lower=0,
            upper=5,
        )
        / 5
    )

    cross_hospital[
        "cross_hospital_score"
    ] = (

        0.30
        * cross_hospital[
            "coverage_score"
        ]

        +

        0.30
        * cross_hospital[
            "local_emergence_score"
        ]

        +

        0.20
        * cross_hospital[
            "growth_score"
        ]

        +

        0.20
        * cross_hospital[
            "persistence_score"
        ]

    ) * 100

    cross_hospital[
        "cross_hospital_score"
    ] = cross_hospital[
        "cross_hospital_score"
    ].round(2)

    # ========================================================
    # CROSS-HOSPITAL ALERT LEVEL
    # ========================================================

    def determine_cross_hospital_alert(
        score,
        hospitals_affected,
        anomalous_occurrences,
    ):
        """
        Assign cross-hospital surveillance alert.

        Safeguards prevent a pattern from receiving
        a severe alert based solely on high percentage
        growth in one or two hospitals.
        """

        # ----------------------------------------------------
        # CRITICAL
        # ----------------------------------------------------

        if (
            score >= 75
            and hospitals_affected >= 5
            and anomalous_occurrences >= 25
        ):

            return "CRITICAL"

        # ----------------------------------------------------
        # HIGH
        # ----------------------------------------------------

        if (
            score >= 55
            and hospitals_affected >= 3
            and anomalous_occurrences >= 10
        ):

            return "HIGH"

        # ----------------------------------------------------
        # MODERATE
        # ----------------------------------------------------

        if (
            score >= 35
            and hospitals_affected >= 2
            and anomalous_occurrences >= 5
        ):

            return "MODERATE"

        return "LOW"

    cross_hospital[
        "alert_level"
    ] = cross_hospital.apply(

        lambda row:
            determine_cross_hospital_alert(

                score=row[
                    "cross_hospital_score"
                ],

                hospitals_affected=row[
                    "hospitals_affected"
                ],

                anomalous_occurrences=row[
                    "total_anomalous_occurrences"
                ],
            ),

        axis=1,
    )

    # ========================================================
    # FILTER
    # ========================================================
    #
    # Only patterns appearing in at least two hospitals
    # are considered true cross-hospital signals.
    # ========================================================

    cross_hospital = cross_hospital[
        cross_hospital[
            "hospitals_affected"
        ]
        >= MIN_HOSPITALS_AFFECTED
    ].copy()

    # ========================================================
    # SORT
    # ========================================================

    cross_hospital = (
        cross_hospital
        .sort_values(
            [
                "cross_hospital_score",
                "hospitals_affected",
                "total_anomalous_occurrences",
            ],
            ascending=[
                False,
                False,
                False,
            ],
        )
        .reset_index(
            drop=True
        )
    )

    # ========================================================
    # REMOVE INTERNAL SCORING COMPONENTS
    # ========================================================
    #
    # These are useful during calculation but don't need
    # to be part of the final surveillance output.
    # ========================================================

    cross_hospital = cross_hospital[
        [
            "symptom_pattern",

            "hospitals_affected",

            "hospital_coverage",

            "total_anomalous_occurrences",

            "mean_current_prevalence",

            "max_current_prevalence",

            "mean_prevalence_growth",

            "max_prevalence_growth",

            "mean_persistence_weeks",

            "max_persistence_weeks",

            "mean_emergence_score",

            "max_emergence_score",

            "spread_level",

            "cross_hospital_score",

            "alert_level",
        ]
    ]

    return (
        combined,
        hospital_counts,
        cross_hospital,
    )


# ============================================================
# COMPLETE A3 ANALYSIS
# ============================================================

def analyze_all_hospitals(
    baseline_end=DEFAULT_BASELINE_END
):
    """
    Execute the complete A3 cross-hospital analysis.

    Each hospital is processed independently first.

    Only aggregate pattern-level results are subsequently
    combined.
    """

    print()
    print("=" * 80)
    print(
        "OBJECTIVE A3 — CROSS-HOSPITAL "
        "EMERGING SYMPTOM ANALYSIS"
    )
    print("=" * 80)

    hospital_results = []

    # ========================================================
    # PROCESS HOSPITALS LOCALLY
    # ========================================================

    for hospital_id in HOSPITALS:

        try:

            local_result = (
                analyze_hospital_locally(
                    hospital_id,
                    baseline_end=baseline_end,
                )
            )

            if not local_result.empty:

                hospital_results.append(
                    local_result
                )

        except Exception as error:

            print()
            print(
                f"ERROR processing "
                f"{hospital_id}: {error}"
            )

    # ========================================================
    # CHECK RESULTS
    # ========================================================

    if not hospital_results:

        print()
        print(
            "No hospital-level results available."
        )

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )

    # ========================================================
    # AGGREGATE
    # ========================================================

    (
        combined,
        hospital_counts,
        cross_hospital,
    ) = aggregate_cross_hospital_patterns(
        hospital_results
    )

    return (
        combined,
        hospital_counts,
        cross_hospital,
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    (
        combined,
        hospital_counts,
        cross_hospital,
    ) = analyze_all_hospitals()

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print(
        "CROSS-HOSPITAL ANALYSIS SUMMARY"
    )
    print("=" * 80)

    print(
        f"Hospitals processed : "
        f"{combined['hospital_id'].nunique()}"
        if not combined.empty
        else "Hospitals processed : 0"
    )

    print(
        f"Hospital-pattern records : "
        f"{len(hospital_counts)}"
    )

    print(
        f"Cross-hospital patterns : "
        f"{len(cross_hospital)}"
    )

    # ========================================================
    # TOP SIGNALS
    # ========================================================

    print()
    print(
        "TOP CROSS-HOSPITAL SIGNALS"
    )
    print("=" * 80)

    if cross_hospital.empty:

        print(
            "No patterns currently meet the "
            "cross-hospital threshold."
        )

    else:

        display_columns = [

            "symptom_pattern",

            "hospitals_affected",

            "hospital_coverage",

            "total_anomalous_occurrences",

            "mean_prevalence_growth",

            "mean_persistence_weeks",

            "mean_emergence_score",

            "cross_hospital_score",

            "spread_level",

            "alert_level",
        ]

        print(
            cross_hospital[
                display_columns
            ]
            .head(15)
            .to_string(
                index=False
            )
        )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    combined_output = (
        OUTPUT_DIR
        / "cross_hospital_aggregate_signals.csv"
    )

    hospital_counts_output = (
        OUTPUT_DIR
        / "hospital_symptom_pattern_aggregates.csv"
    )

    cross_hospital_output = (
        OUTPUT_DIR
        / "cross_hospital_symptom_patterns.csv"
    )

    combined.to_csv(
        combined_output,
        index=False,
    )

    hospital_counts.to_csv(
        hospital_counts_output,
        index=False,
    )

    cross_hospital.to_csv(
        cross_hospital_output,
        index=False,
    )

    print()
    print(
        "Aggregate results saved:"
    )

    print(
        f"  {combined_output}"
    )

    print(
        f"  {hospital_counts_output}"
    )

    print(
        f"  {cross_hospital_output}"
    )

    print()
    print(
        "A3 cross-hospital analysis completed."
    )
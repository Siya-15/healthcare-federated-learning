"""
B12 - Explainability Engine

Purpose
-------
Provides a structured explanation for every B10/B11 outbreak-risk
assessment.

B12 answers:

    "Why did I get this alert?"

It explains:

1. Overall risk score
2. Alert level
3. Individual evidence scores
4. Weighted contribution of each evidence source
5. Primary risk drivers
6. Supporting evidence
7. Missing/weak corroboration
8. Associated disease, where available
9. Recommended interpretation
10. Recommended surveillance action

Input
-----
B10:
    outbreak_risk_engine.csv

B11:
    alert_engine.csv

Outputs
-------
explainability_engine.csv
explainability_latest.csv
alert_explanations.csv
"""

from pathlib import Path

import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

B10_FILE = BASE_DIR / "outbreak_risk_engine.csv"
B11_FILE = BASE_DIR / "alert_engine.csv"

OUTPUT_FILE = BASE_DIR / "explainability_engine.csv"
LATEST_OUTPUT_FILE = BASE_DIR / "explainability_latest.csv"
ALERT_EXPLANATIONS_FILE = BASE_DIR / "alert_explanations.csv"


# ============================================================================
# WEIGHTS
# ============================================================================

WEIGHTS = {
    "baseline": 0.15,
    "anomaly": 0.15,
    "temporal": 0.15,
    "persistence": 0.15,
    "spatial": 0.15,
    "objective_a": 0.10,
    "severity": 0.15,
}


# ============================================================================
# THRESHOLDS
# ============================================================================

MODERATE_THRESHOLD = 35.0
STRONG_THRESHOLD = 55.0


# ============================================================================
# LOAD B10
# ============================================================================

def load_b10():

    print(
        "Loading B10 composite risk data..."
    )

    df = pd.read_csv(
        B10_FILE
    )

    print(
        f"B10 rows: {len(df)}"
    )

    required = [
        "week",
        "symptom_id",
        "risk_score",
        "risk_alert",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            f"B10 missing required columns: "
            f"{missing}"
        )

    return df


# ============================================================================
# LOAD B11
# ============================================================================

def load_b11():

    print(
        "Loading B11 alert data..."
    )

    df = pd.read_csv(
        B11_FILE
    )

    print(
        f"B11 rows: {len(df)}"
    )

    required = [
        "week",
        "symptom_id",
        "alert_id",
        "alert_level",
        "alert_priority",
        "alert_status",
        "recommended_action",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            f"B11 missing required columns: "
            f"{missing}"
        )

    return df


# ============================================================================
# NUMERIC CONVERSION
# ============================================================================

def convert_numeric(
    df,
    columns,
):

    df = df.copy()

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0.0)

    return df


# ============================================================================
# BUILD EVIDENCE CONTRIBUTIONS
# ============================================================================

def calculate_contributions(
    df,
):

    df = df.copy()

    evidence_map = {
        "baseline": (
            "baseline_score",
            WEIGHTS["baseline"],
        ),

        "anomaly": (
            "anomaly_score",
            WEIGHTS["anomaly"],
        ),

        "temporal": (
            "temporal_score",
            WEIGHTS["temporal"],
        ),

        "persistence": (
            "persistence_score",
            WEIGHTS["persistence"],
        ),

        "spatial": (
            "spatial_score",
            WEIGHTS["spatial"],
        ),

        "objective_a": (
            "b8_pattern_score",
            WEIGHTS["objective_a"],
        ),

        "severity": (
            "severity_score",
            WEIGHTS["severity"],
        ),
    }

    for evidence_name, (
        score_column,
        weight,
    ) in evidence_map.items():

        if score_column not in df.columns:

            df[score_column] = 0.0

        df[score_column] = pd.to_numeric(
            df[score_column],
            errors="coerce",
        ).fillna(0.0).clip(
            0,
            100
        )

        contribution_column = (
            f"{evidence_name}_contribution"
        )

        df[contribution_column] = (
            df[score_column]
            * weight
        ).round(2)

    return df


# ============================================================================
# PRIMARY DRIVERS
# ============================================================================

def identify_primary_drivers(
    row,
):

    evidence = {
        "Historical baseline": row.get(
            "baseline_score",
            0.0,
        ),

        "Statistical anomaly": row.get(
            "anomaly_score",
            0.0,
        ),

        "Temporal acceleration": row.get(
            "temporal_score",
            0.0,
        ),

        "Persistence": row.get(
            "persistence_score",
            0.0,
        ),

        "Spatial propagation": row.get(
            "spatial_score",
            0.0,
        ),

        "Objective A emerging/atypical signal":
            row.get(
                "b8_pattern_score",
                0.0,
            ),

        "Severity burden": row.get(
            "severity_score",
            0.0,
        ),
    }

    ranked = sorted(
        evidence.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    strong = [
        name
        for name, score in ranked
        if score >= STRONG_THRESHOLD
    ]

    moderate = [
        name
        for name, score in ranked
        if (
            MODERATE_THRESHOLD
            <= score
            < STRONG_THRESHOLD
        )
    ]

    if strong:

        primary = strong[:3]

    elif moderate:

        primary = moderate[:3]

    else:

        primary = [
            ranked[0][0]
        ]

    return primary


# ============================================================================
# WEAK / MISSING EVIDENCE
# ============================================================================

def identify_missing_evidence(
    row,
):

    evidence = {
        "Historical baseline":
            row.get(
                "baseline_score",
                0.0,
            ),

        "Statistical anomaly":
            row.get(
                "anomaly_score",
                0.0,
            ),

        "Temporal acceleration":
            row.get(
                "temporal_score",
                0.0,
            ),

        "Persistence":
            row.get(
                "persistence_score",
                0.0,
            ),

        "Spatial propagation":
            row.get(
                "spatial_score",
                0.0,
            ),

        "Objective A":
            row.get(
                "b8_pattern_score",
                0.0,
            ),

        "Severity burden":
            row.get(
                "severity_score",
                0.0,
            ),
    }

    weak = [
        name
        for name, score in evidence.items()
        if score < MODERATE_THRESHOLD
    ]

    return weak


# ============================================================================
# EVIDENCE COUNTS
# ============================================================================

def calculate_evidence_counts(
    row,
):

    evidence = [
        row.get(
            "baseline_score",
            0.0,
        ),

        row.get(
            "anomaly_score",
            0.0,
        ),

        row.get(
            "temporal_score",
            0.0,
        ),

        row.get(
            "persistence_score",
            0.0,
        ),

        row.get(
            "spatial_score",
            0.0,
        ),

        row.get(
            "b8_pattern_score",
            0.0,
        ),

        row.get(
            "severity_score",
            0.0,
        ),
    ]

    strong = sum(
        score >= STRONG_THRESHOLD
        for score in evidence
    )

    moderate = sum(
        score >= MODERATE_THRESHOLD
        for score in evidence
    )

    return strong, moderate


# ============================================================================
# INTERPRETATION
# ============================================================================

def build_interpretation(
    row,
):

    level = str(
        row.get(
            "alert_level",
            "GREEN",
        )
    ).upper()

    score = float(
        row.get(
            "risk_score",
            0.0,
        )
    )

    strong_count = int(
        row.get(
            "strong_evidence_count",
            0,
        )
    )

    moderate_count = int(
        row.get(
            "moderate_evidence_count",
            0,
        )
    )

    if level == "GREEN":

        return (
            f"The composite risk score is {score:.1f}. "
            "Current evidence does not indicate a "
            "significant outbreak-level concern. "
            "Routine surveillance should continue."
        )

    if level == "YELLOW":

        return (
            f"The composite risk score is {score:.1f}. "
            f"There are {moderate_count} evidence sources "
            "showing at least moderate abnormality, "
            f"including {strong_count} strong signal(s). "
            "The signal warrants enhanced observation "
            "but does not currently meet the criteria "
            "for an escalated outbreak alert."
        )

    if level == "ORANGE":

        return (
            f"The composite risk score is {score:.1f}. "
            f"Multiple evidence sources support the signal "
            f"({moderate_count} moderate-or-strong and "
            f"{strong_count} strong). "
            "The evidence justifies escalated outbreak "
            "surveillance and further investigation."
        )

    return (
        f"The composite risk score is {score:.1f}. "
        f"Multiple strong evidence sources "
        f"({strong_count}) support the signal. "
        "The evidence warrants immediate outbreak "
        "investigation and coordinated response."
    )


# ============================================================================
# DETAILED EXPLANATION
# ============================================================================

def build_detailed_explanation(
    row,
):

    level = str(
        row.get(
            "alert_level",
            "GREEN",
        )
    ).upper()

    score = float(
        row.get(
            "risk_score",
            0.0,
        )
    )

    drivers = identify_primary_drivers(
        row
    )

    weak = identify_missing_evidence(
        row
    )

    driver_text = (
        ", ".join(
            drivers
        )
    )

    if weak:

        weak_text = (
            ", ".join(
                weak
            )
        )

    else:

        weak_text = (
            "No major evidence category is currently weak."
        )

    disease_id = row.get(
        "best_matching_disease_id",
        None,
    )

    if pd.isna(
        disease_id
    ):

        disease_text = (
            "No specific disease association "
            "was available."
        )

    else:

        disease_text = (
            f"The associated disease is "
            f"{disease_id}."
        )

    return (
        f"Alert level: {level}. "
        f"Composite risk score: {score:.1f}. "
        f"Primary risk drivers: {driver_text}. "
        f"Weaker or missing corroboration: "
        f"{weak_text}. "
        f"{disease_text}"
    )


# ============================================================================
# BUILD EXPLAINABILITY TABLE
# ============================================================================

def build_explainability(
    b10,
    b11,
):

    print(
        "\nBuilding structured explanations..."
    )

    b10 = b10.copy()
    b11 = b11.copy()

    # --------------------------------------------------------------
    # Normalize dates
    # --------------------------------------------------------------

    b10["week"] = pd.to_datetime(
        b10["week"],
        errors="coerce",
    )

    b11["week"] = pd.to_datetime(
        b11["week"],
        errors="coerce",
    )

    # --------------------------------------------------------------
    # Avoid duplicate B11 columns
    # --------------------------------------------------------------

    b11_columns = [
        "week",
        "symptom_id",
        "alert_id",
        "alert_level",
        "alert_priority",
        "alert_status",
        "alert_type",
        "recommended_action",
    ]

    b11_subset = b11[
        [
            c
            for c in b11_columns
            if c in b11.columns
        ]
    ].copy()

    # --------------------------------------------------------------
    # Merge B10 and B11
    # --------------------------------------------------------------

    df = b10.merge(
        b11_subset,
        on=[
            "week",
            "symptom_id",
        ],
        how="left",
        suffixes=(
            "",
            "_b11",
        ),
    )

    # --------------------------------------------------------------
    # Use B11 alert metadata as operational truth.
    # --------------------------------------------------------------

    if (
        "alert_level_b11"
        in df.columns
    ):

        df["alert_level"] = (
            df[
                "alert_level_b11"
            ]
            .fillna(
                df["risk_alert"]
            )
        )

    else:

        df["alert_level"] = (
            df["risk_alert"]
        )

    # --------------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------------

    df = convert_numeric(
        df,
        [
            "risk_score",
            "baseline_score",
            "anomaly_score",
            "temporal_score",
            "persistence_score",
            "spatial_score",
            "b8_pattern_score",
            "severity_score",
        ],
    )

    # --------------------------------------------------------------
    # Calculate weighted contributions
    # --------------------------------------------------------------

    df = calculate_contributions(
        df
    )

    # --------------------------------------------------------------
    # Evidence counts
    # --------------------------------------------------------------

    counts = (
        df.apply(
            calculate_evidence_counts,
            axis=1,
            result_type="expand",
        )
    )

    counts.columns = [
        "strong_evidence_count_explainability",
        "moderate_evidence_count_explainability",
    ]

    df = pd.concat(
        [
            df,
            counts,
        ],
        axis=1,
    )

    # --------------------------------------------------------------
    # Primary drivers
    # --------------------------------------------------------------

    df["primary_drivers"] = (
        df.apply(
            lambda row:
                "; ".join(
                    identify_primary_drivers(
                        row
                    )
                ),
            axis=1,
        )
    )

    # --------------------------------------------------------------
    # Weak evidence
    # --------------------------------------------------------------

    df["weak_or_missing_evidence"] = (
        df.apply(
            lambda row:
                "; ".join(
                    identify_missing_evidence(
                        row
                    )
                ),
            axis=1,
        )
    )

    # --------------------------------------------------------------
    # Interpretation
    # --------------------------------------------------------------

    df["explainability_interpretation"] = (
        df.apply(
            build_interpretation,
            axis=1,
        )
    )

    # --------------------------------------------------------------
    # Detailed explanation
    # --------------------------------------------------------------

    df["detailed_explanation"] = (
        df.apply(
            build_detailed_explanation,
            axis=1,
        )
    )

    # --------------------------------------------------------------
    # Evidence contribution summary
    # --------------------------------------------------------------

    def contribution_summary(
        row
    ):

        contributions = {
            "baseline":
                row.get(
                    "baseline_contribution",
                    0.0,
                ),

            "anomaly":
                row.get(
                    "anomaly_contribution",
                    0.0,
                ),

            "temporal":
                row.get(
                    "temporal_contribution",
                    0.0,
                ),

            "persistence":
                row.get(
                    "persistence_contribution",
                    0.0,
                ),

            "spatial":
                row.get(
                    "spatial_contribution",
                    0.0,
                ),

            "objective_a":
                row.get(
                    "objective_a_contribution",
                    0.0,
                ),

            "severity":
                row.get(
                    "severity_contribution",
                    0.0,
                ),
        }

        ranked = sorted(
            contributions.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return "; ".join(
            [
                f"{name}={value:.2f}"
                for name, value in ranked
            ]
        )

    df["weighted_evidence_breakdown"] = (
        df.apply(
            contribution_summary,
            axis=1,
        )
    )

    return df


# ============================================================================
# LATEST
# ============================================================================

def build_latest(
    df,
):

    latest_week = df[
        "week"
    ].max()

    latest = (
        df[
            df["week"] == latest_week
        ]
        .sort_values(
            [
                "alert_severity",
                "risk_score",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .reset_index(
            drop=True
        )
    )

    return latest


# ============================================================================
# ALERT-FOCUSED OUTPUT
# ============================================================================

def build_alert_explanations(
    latest,
):

    columns = [
        "alert_id",
        "week",
        "symptom_id",
        "symptom_name",
        "alert_level",
        "alert_priority",
        "alert_status",
        "risk_score",
        "primary_drivers",
        "weak_or_missing_evidence",
        "weighted_evidence_breakdown",
        "detailed_explanation",
        "recommended_action",
    ]

    available = [
        c
        for c in columns
        if c in latest.columns
    ]

    return latest[
        available
    ].copy()


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)
    print("B12 - EXPLAINABILITY ENGINE")
    print("=" * 80)

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    b10 = load_b10()

    b11 = load_b11()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    result = build_explainability(
        b10,
        b11,
    )

    # ------------------------------------------------------------------
    # Create alert severity for sorting
    # ------------------------------------------------------------------

    severity_map = {
        "GREEN": 0,
        "YELLOW": 1,
        "ORANGE": 2,
        "RED": 3,
    }

    result["alert_severity"] = (
        result["alert_level"]
        .map(
            severity_map
        )
        .fillna(0)
    )

    # ------------------------------------------------------------------
    # Latest
    # ------------------------------------------------------------------

    latest = build_latest(
        result
    )

    alert_explanations = (
        build_alert_explanations(
            latest
        )
    )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    latest.to_csv(
        LATEST_OUTPUT_FILE,
        index=False
    )

    alert_explanations.to_csv(
        ALERT_EXPLANATIONS_FILE,
        index=False
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B12 COMPLETE")
    print("=" * 80)

    print(
        f"Time range: "
        f"{result['week'].min().date()} → "
        f"{result['week'].max().date()}"
    )

    print(
        f"Total explainability records: "
        f"{len(result)}"
    )

    print(
        f"Latest week: "
        f"{latest['week'].max().date()}"
    )

    print(
        "\nLatest explainability alert levels:"
    )

    print(
        latest[
            "alert_level"
        ]
        .value_counts()
        .to_string()
    )

    # ------------------------------------------------------------------
    # Current alerts
    # ------------------------------------------------------------------

    current_alerts = latest[
        latest["alert_level"].isin(
            [
                "YELLOW",
                "ORANGE",
                "RED",
            ]
        )
    ].copy()

    print(
        f"\nLatest alerts requiring "
        f"attention: {len(current_alerts)}"
    )

    if len(current_alerts) > 0:

        print(
            "\nCurrent alert explanations:"
        )

        display_columns = [
            "alert_id",
            "symptom_id",
            "symptom_name",
            "alert_level",
            "risk_score",
            "primary_drivers",
            "weak_or_missing_evidence",
        ]

        available = [
            c
            for c in display_columns
            if c in current_alerts.columns
        ]

        print(
            current_alerts[
                available
            ]
            .to_string(
                index=False
            )
        )

    # ------------------------------------------------------------------
    # Strongest explanation
    # ------------------------------------------------------------------

    if len(latest) > 0:

        strongest = latest.iloc[0]

        print(
            "\nStrongest current explanation:"
        )

        print(
            strongest[
                "detailed_explanation"
            ]
        )

        print(
            "\nWeighted evidence breakdown:"
        )

        print(
            strongest[
                "weighted_evidence_breakdown"
            ]
        )

        print(
            "\nRecommended action:"
        )

        print(
            strongest.get(
                "recommended_action",
                "Continue surveillance.",
            )
        )

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    print(
        f"\nMain output: "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Latest output: "
        f"{LATEST_OUTPUT_FILE}"
    )

    print(
        f"Alert explanations: "
        f"{ALERT_EXPLANATIONS_FILE}"
    )

    print("\n" + "=" * 80)
    print("B12 READY FOR REVIEW")
    print("=" * 80)


if __name__ == "__main__":
    main()
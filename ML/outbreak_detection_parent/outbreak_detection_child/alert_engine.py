"""
B11 - Alert Engine

Purpose
-------
Converts the frozen B10 composite outbreak-risk output into
an operational alert layer.

B10 answers:
    "How much outbreak risk is present?"

B11 answers:
    "What alert should be issued and what does it mean?"

Alert levels
------------
GREEN  - Routine surveillance
YELLOW - Watch / investigate
ORANGE - Escalated outbreak surveillance
RED    - Critical outbreak alert

B11 does NOT recalculate outbreak risk.
It consumes B10 as its source of truth.

Outputs
-------
alert_engine.csv
alert_engine_latest.csv
active_alerts.csv
"""

from pathlib import Path

import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

B10_FILE = BASE_DIR / "outbreak_risk_engine.csv"

OUTPUT_FILE = BASE_DIR / "alert_engine.csv"
LATEST_OUTPUT_FILE = BASE_DIR / "alert_engine_latest.csv"
ACTIVE_ALERTS_FILE = BASE_DIR / "active_alerts.csv"


# ============================================================================
# CONFIGURATION
# ============================================================================

ALERT_LEVELS = {
    "GREEN": {
        "priority": "ROUTINE",
        "severity": 0,
        "action": (
            "Continue routine surveillance and periodic review."
        ),
    },

    "YELLOW": {
        "priority": "WATCH",
        "severity": 1,
        "action": (
            "Review the affected symptom/disease trend, "
            "verify recent clinical records, and continue "
            "enhanced surveillance."
        ),
    },

    "ORANGE": {
        "priority": "HIGH",
        "severity": 2,
        "action": (
            "Initiate escalated outbreak surveillance, "
            "review affected hospitals, investigate the "
            "supporting epidemiological signals, and "
            "increase monitoring frequency."
        ),
    },

    "RED": {
        "priority": "CRITICAL",
        "severity": 3,
        "action": (
            "Initiate immediate outbreak investigation, "
            "coordinate affected hospitals and public-health "
            "teams, and continuously monitor the evolving signal."
        ),
    },
}


# ============================================================================
# HELPERS
# ============================================================================

def safe_numeric(
    df,
    columns,
):

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0.0)

    return df


def safe_bool(
    value,
):

    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "y",
    }


# ============================================================================
# LOAD B10
# ============================================================================

def load_b10():

    print(
        "Loading B10 composite outbreak-risk output..."
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
        "outbreak_signal",
        "risk_explanation",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            f"B10 missing required columns: "
            f"{missing}"
        )

    return df


# ============================================================================
# NORMALIZE B10
# ============================================================================

def normalize_b10(
    df,
):

    df = df.copy()

    # --------------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------------

    df = safe_numeric(
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
            "strong_evidence_count",
            "moderate_evidence_count",
            "severe_cases",
            "disease_total_cases",
        ],
    )

    # --------------------------------------------------------------
    # Alert
    # --------------------------------------------------------------

    df["risk_alert"] = (
        df["risk_alert"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    valid_alerts = set(
        ALERT_LEVELS.keys()
    )

    invalid_alerts = set(
        df["risk_alert"].unique()
    ) - valid_alerts

    if invalid_alerts:

        raise ValueError(
            f"Invalid B10 alert levels: "
            f"{invalid_alerts}"
        )

    # --------------------------------------------------------------
    # Boolean
    # --------------------------------------------------------------

    df["outbreak_signal"] = (
        df["outbreak_signal"]
        .apply(safe_bool)
    )

    # --------------------------------------------------------------
    # Week
    # --------------------------------------------------------------

    df["week"] = (
        pd.to_datetime(
            df["week"],
            errors="coerce",
        )
    )

    if df["week"].isna().any():

        raise ValueError(
            "B10 contains invalid week values."
        )

    return df


# ============================================================================
# ALERT CLASSIFICATION
# ============================================================================

def classify_alert_level(
    row,
):

    risk_alert = row[
        "risk_alert"
    ]

    risk_score = row[
        "risk_score"
    ]

    outbreak_signal = row[
        "outbreak_signal"
    ]

    # B10 remains the source of truth.
    #
    # B11 does not independently override the B10
    # composite risk classification.

    if risk_alert == "RED":

        return "RED"

    if risk_alert == "ORANGE":

        return "ORANGE"

    if risk_alert == "YELLOW":

        return "YELLOW"

    return "GREEN"


# ============================================================================
# ALERT METADATA
# ============================================================================

def attach_alert_metadata(
    df,
):

    df = df.copy()

    df["alert_level"] = (
        df.apply(
            classify_alert_level,
            axis=1,
        )
    )

    df["alert_priority"] = (
        df["alert_level"]
        .map(
            lambda level:
                ALERT_LEVELS[level][
                    "priority"
                ]
        )
    )

    df["alert_severity"] = (
        df["alert_level"]
        .map(
            lambda level:
                ALERT_LEVELS[level][
                    "severity"
                ]
        )
    )

    df["recommended_action"] = (
        df["alert_level"]
        .map(
            lambda level:
                ALERT_LEVELS[level][
                    "action"
                ]
        )
    )

    return df


# ============================================================================
# ALERT TYPE
# ============================================================================

def determine_alert_type(
    row,
):

    level = row[
        "alert_level"
    ]

    if level == "GREEN":

        return "ROUTINE_SURVEILLANCE"

    if level == "YELLOW":

        return "SURVEILLANCE_WATCH"

    if level == "ORANGE":

        return "ESCALATED_OUTBREAK_SURVEILLANCE"

    if level == "RED":

        return "CRITICAL_OUTBREAK_ALERT"

    return "UNKNOWN"


# ============================================================================
# EXPLAINABILITY
# ============================================================================

def build_alert_explanation(
    row,
):

    level = row[
        "alert_level"
    ]

    score = row[
        "risk_score"
    ]

    evidence = []

    # --------------------------------------------------------------
    # B3
    # --------------------------------------------------------------

    if row.get(
        "baseline_score",
        0
    ) >= 35:

        evidence.append(
            f"historical baseline deviation "
            f"({row['baseline_score']:.1f})"
        )

    # --------------------------------------------------------------
    # B4
    # --------------------------------------------------------------

    if row.get(
        "anomaly_score",
        0
    ) >= 35:

        evidence.append(
            f"statistical anomaly "
            f"({row['anomaly_score']:.1f})"
        )

    # --------------------------------------------------------------
    # B5
    # --------------------------------------------------------------

    if row.get(
        "temporal_score",
        0
    ) >= 35:

        evidence.append(
            f"temporal acceleration "
            f"({row['temporal_score']:.1f})"
        )

    # --------------------------------------------------------------
    # B6
    # --------------------------------------------------------------

    if row.get(
        "persistence_score",
        0
    ) >= 35:

        evidence.append(
            f"persistent signal "
            f"({row['persistence_score']:.1f})"
        )

    # --------------------------------------------------------------
    # B7
    # --------------------------------------------------------------

    if row.get(
        "spatial_score",
        0
    ) >= 35:

        evidence.append(
            f"spatial propagation "
            f"({row['spatial_score']:.1f})"
        )

    # --------------------------------------------------------------
    # B8
    # --------------------------------------------------------------

    if row.get(
        "b8_pattern_score",
        0
    ) >= 35:

        evidence.append(
            f"Objective A atypical/emerging evidence "
            f"({row['b8_pattern_score']:.1f})"
        )

    # --------------------------------------------------------------
    # B9
    # --------------------------------------------------------------

    if row.get(
        "severity_score",
        0
    ) >= 35:

        disease_id = row.get(
            "best_matching_disease_id",
            None,
        )

        if pd.isna(
            disease_id
        ):

            evidence.append(
                f"severity burden "
                f"({row['severity_score']:.1f})"
            )

        else:

            evidence.append(
                f"severity burden from "
                f"disease {disease_id} "
                f"({row['severity_score']:.1f})"
            )

    # --------------------------------------------------------------
    # Final explanation
    # --------------------------------------------------------------

    if evidence:

        evidence_text = (
            "Supporting evidence: "
            +
            "; ".join(
                evidence
            )
            +
            "."
        )

    else:

        evidence_text = (
            "No major abnormal supporting "
            "evidence was identified."
        )

    if level == "GREEN":

        interpretation = (
            "The signal remains within routine "
            "surveillance conditions."
        )

    elif level == "YELLOW":

        interpretation = (
            "The signal warrants continued observation "
            "and clinical review but does not currently "
            "meet the criteria for an escalated outbreak alert."
        )

    elif level == "ORANGE":

        interpretation = (
            "Multiple supporting indicators justify "
            "escalated outbreak surveillance."
        )

    else:

        interpretation = (
            "Multiple strong indicators justify "
            "immediate outbreak investigation."
        )

    return (
        f"B11 classified this signal as {level} "
        f"with a composite risk score of {score:.1f}. "
        f"{interpretation} "
        f"{evidence_text}"
    )


# ============================================================================
# ALERT STATUS
# ============================================================================

def determine_alert_status(
    row,
):

    if row[
        "alert_level"
    ] in {
        "ORANGE",
        "RED",
    }:

        return "ACTIVE"

    if row[
        "alert_level"
    ] == "YELLOW":

        return "WATCH"

    return "ROUTINE"


# ============================================================================
# ALERT ID
# ============================================================================

def create_alert_id(
    row,
    index,
):

    week_text = (
        row["week"]
        .strftime("%Y%m%d")
    )

    symptom_id = str(
        row["symptom_id"]
    )

    level = str(
        row["alert_level"]
    )

    return (
        f"ALT-{week_text}-"
        f"{symptom_id}-"
        f"{level}-{index + 1:04d}"
    )


# ============================================================================
# BUILD ALERT DATASET
# ============================================================================

def build_alerts(
    b10,
):

    print(
        "\nBuilding operational alerts..."
    )

    df = normalize_b10(
        b10
    )

    df = attach_alert_metadata(
        df
    )

    df["alert_type"] = (
        df.apply(
            determine_alert_type,
            axis=1,
        )
    )

    df["alert_status"] = (
        df.apply(
            determine_alert_status,
            axis=1,
        )
    )

    df["alert_explanation"] = (
        df.apply(
            build_alert_explanation,
            axis=1,
        )
    )

    # --------------------------------------------------------------
    # Alert IDs
    # --------------------------------------------------------------

    df = df.reset_index(
        drop=True
    )

    df["alert_id"] = [
        create_alert_id(
            row,
            index,
        )
        for index, row
        in df.iterrows()
    ]

    # --------------------------------------------------------------
    # Recommended action
    # --------------------------------------------------------------

    # Keep the action generated from alert level.
    #
    # B11 is an operational surveillance layer and
    # does not prescribe patient treatment.

    # --------------------------------------------------------------
    # Sort by week + priority + score
    # --------------------------------------------------------------

    df = (
        df
        .sort_values(
            [
                "week",
                "alert_severity",
                "risk_score",
            ],
            ascending=[
                True,
                False,
                False,
            ],
        )
        .reset_index(
            drop=True
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
# ACTIVE ALERTS
# ============================================================================

def build_active_alerts(
    latest,
):

    active = latest[
        latest["alert_status"].isin(
            [
                "WATCH",
                "ACTIVE",
            ]
        )
    ].copy()

    return active


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)
    print("B11 - ALERT ENGINE")
    print("=" * 80)

    # ------------------------------------------------------------------
    # Load B10
    # ------------------------------------------------------------------

    b10 = load_b10()

    # ------------------------------------------------------------------
    # Build alerts
    # ------------------------------------------------------------------

    alerts = build_alerts(
        b10
    )

    latest = build_latest(
        alerts
    )

    active = build_active_alerts(
        latest
    )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    alerts.to_csv(
        OUTPUT_FILE,
        index=False
    )

    latest.to_csv(
        LATEST_OUTPUT_FILE,
        index=False
    )

    active.to_csv(
        ACTIVE_ALERTS_FILE,
        index=False
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B11 COMPLETE")
    print("=" * 80)

    print(
        f"Time range: "
        f"{alerts['week'].min().date()} → "
        f"{alerts['week'].max().date()}"
    )

    print(
        f"Total alert records: "
        f"{len(alerts)}"
    )

    print(
        f"Latest week: "
        f"{latest['week'].max().date()}"
    )

    print(
        "\nLatest alert levels:"
    )

    print(
        latest[
            "alert_level"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nLatest alert statuses:"
    )

    print(
        latest[
            "alert_status"
        ]
        .value_counts()
        .to_string()
    )

    print(
        f"\nLatest watch/active alerts: "
        f"{len(active)}"
    )

    # ------------------------------------------------------------------
    # Current alerts
    # ------------------------------------------------------------------

    if len(active) > 0:

        print(
            "\nCurrent operational alerts:"
        )

        display_columns = [
            "alert_id",
            "symptom_id",
            "symptom_name",
            "alert_level",
            "alert_priority",
            "risk_score",
            "alert_type",
            "alert_status",
            "best_matching_disease_id",
        ]

        available = [
            c
            for c in display_columns
            if c in active.columns
        ]

        print(
            active[
                available
            ]
            .head(15)
            .to_string(
                index=False
            )
        )

    else:

        print(
            "\nNo current watch or active alerts."
        )

    # ------------------------------------------------------------------
    # Strongest current alert
    # ------------------------------------------------------------------

    if len(latest) > 0:

        strongest = latest.iloc[0]

        print(
            "\nStrongest current alert:"
        )

        print(
            f"Alert ID: "
            f"{strongest['alert_id']}"
        )

        print(
            f"Symptom: "
            f"{strongest.get('symptom_name', strongest['symptom_id'])}"
        )

        print(
            f"Level: "
            f"{strongest['alert_level']}"
        )

        print(
            f"Priority: "
            f"{strongest['alert_priority']}"
        )

        print(
            f"Risk score: "
            f"{strongest['risk_score']:.2f}"
        )

        print(
            f"Status: "
            f"{strongest['alert_status']}"
        )

        print(
            "\nExplanation:"
        )

        print(
            strongest[
                "alert_explanation"
            ]
        )

        print(
            "\nRecommended action:"
        )

        print(
            strongest[
                "recommended_action"
            ]
        )

    # ------------------------------------------------------------------
    # Output files
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
        f"Active alerts output: "
        f"{ACTIVE_ALERTS_FILE}"
    )

    print("\n" + "=" * 80)
    print("B11 READY FOR REVIEW")
    print("=" * 80)


if __name__ == "__main__":
    main()
from pathlib import Path

import pandas as pd
import numpy as np


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent

B3_FILE = CURRENT_DIR / "cross_hospital_symptom_surveillance.csv"
B4_FILE = CURRENT_DIR / "symptom_historical_baseline.csv"
B5_FILE = CURRENT_DIR / "symptom_anomaly_detection.csv"
B6_FILE = CURRENT_DIR / "symptom_persistence_detection.csv"

OUTPUT_FILE = CURRENT_DIR / "outbreak_risk_assessment.csv"


# -------------------------------------------------------------------
# Load helper
# -------------------------------------------------------------------

def load_csv(path, name):

    if not path.exists():
        raise FileNotFoundError(
            f"{name} output not found: {path}"
        )

    df = pd.read_csv(path)

    if "week" in df.columns:
        df["week"] = pd.to_datetime(
            df["week"],
            errors="coerce"
        )

    return df


# -------------------------------------------------------------------
# Load B3
# -------------------------------------------------------------------

def load_b3():

    df = load_csv(
        B3_FILE,
        "B3"
    )

    required = [
        "week",
        "symptom_id",
        "symptom_name",
        "hospitals_observed",
        "hospitals_increasing",
        "average_growth_rate",
        "spread_proportion",
        "cross_hospital_alert",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"B3 missing columns: {missing}"
        )

    return df


# -------------------------------------------------------------------
# Load B4
# -------------------------------------------------------------------

def load_b4():

    df = load_csv(
        B4_FILE,
        "B4"
    )

    required = [
        "week",
        "symptom_id",
        "symptom_name",
        "current_cases",
        "historical_mean",
        "historical_std",
        "deviation_from_baseline",
        "deviation_percent",
        "z_score",
        "baseline_alert",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"B4 missing columns: {missing}"
        )

    return df


# -------------------------------------------------------------------
# Load B5
# -------------------------------------------------------------------

def load_b5():

    df = load_csv(
        B5_FILE,
        "B5"
    )

    required = [
        "week",
        "symptom_id",
        "symptom_name",
        "anomaly_score",
        "anomaly_alert",
        "potential_outbreak",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"B5 missing columns: {missing}"
        )

    return df


# -------------------------------------------------------------------
# Load B6
# -------------------------------------------------------------------

def load_b6():

    df = load_csv(
        B6_FILE,
        "B6"
    )

    required = [
        "week",
        "symptom_id",
        "symptom_name",
        "persistent_hospitals",
        "strong_anomaly_hospitals",
        "max_hospital_consecutive_weeks",
        "cross_hospital_consecutive_weeks",
        "persistence_score",
        "cross_hospital_persistence_alert",
        "persistent_outbreak_signal",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"B6 missing columns: {missing}"
        )

    return df


# -------------------------------------------------------------------
# Prepare B4
# -------------------------------------------------------------------

def prepare_b4(b4):

    columns = [
        "week",
        "symptom_id",
        "symptom_name",
        "current_cases",
        "historical_mean",
        "historical_std",
        "deviation_from_baseline",
        "deviation_percent",
        "z_score",
        "baseline_alert",
    ]

    df = b4[columns].copy()

    numeric_columns = [
        "current_cases",
        "historical_mean",
        "historical_std",
        "deviation_from_baseline",
        "deviation_percent",
        "z_score",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # B4 contains one row per hospital.
    # For B7 we need a symptom-level view.
    #
    # We therefore aggregate the current hospital baseline
    # evidence into:
    #
    #   average z-score
    #   maximum z-score
    #   number of hospitals with baseline anomalies
    #
    # Only actual anomaly alerts count as anomalous hospitals.

    df["baseline_anomalous"] = (
        df["baseline_alert"].isin(
            [
                "YELLOW",
                "ORANGE",
                "RED",
            ]
        )
    )

    df["baseline_strong"] = (
        df["baseline_alert"].isin(
            [
                "ORANGE",
                "RED",
            ]
        )
    )

    result = (
        df.groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
            ],
            as_index=False
        )
        .agg(
            average_z_score=(
                "z_score",
                "mean"
            ),

            maximum_z_score=(
                "z_score",
                "max"
            ),

            baseline_anomalous_hospitals=(
                "baseline_anomalous",
                "sum"
            ),

            baseline_strong_hospitals=(
                "baseline_strong",
                "sum"
            ),
        )
    )

    return result


# -------------------------------------------------------------------
# Prepare B5
# -------------------------------------------------------------------

def prepare_b5(b5):

    columns = [
        "week",
        "symptom_id",
        "symptom_name",
        "anomaly_score",
        "anomaly_alert",
        "potential_outbreak",
    ]

    df = b5[columns].copy()

    df["anomaly_score"] = pd.to_numeric(
        df["anomaly_score"],
        errors="coerce"
    )

    df["potential_outbreak"] = (
        df["potential_outbreak"]
        .fillna(False)
        .astype(bool)
    )

    return df


# -------------------------------------------------------------------
# Prepare B6
# -------------------------------------------------------------------

def prepare_b6(b6):

    columns = [
        "week",
        "symptom_id",
        "symptom_name",
        "persistent_hospitals",
        "strong_anomaly_hospitals",
        "max_hospital_consecutive_weeks",
        "cross_hospital_consecutive_weeks",
        "persistence_score",
        "cross_hospital_persistence_alert",
        "persistent_outbreak_signal",
    ]

    df = b6[columns].copy()

    numeric_columns = [
        "persistent_hospitals",
        "strong_anomaly_hospitals",
        "max_hospital_consecutive_weeks",
        "cross_hospital_consecutive_weeks",
        "persistence_score",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df["persistent_outbreak_signal"] = (
        df["persistent_outbreak_signal"]
        .fillna(False)
        .astype(bool)
    )

    return df


# -------------------------------------------------------------------
# Build final B7 dataset
# -------------------------------------------------------------------

def build_risk_dataset(
    b3,
    b4,
    b5,
    b6
):

    baseline = prepare_b4(b4)
    anomaly = prepare_b5(b5)
    persistence = prepare_b6(b6)

    # ---------------------------------------------------------------
    # B3 columns
    # ---------------------------------------------------------------

    surveillance = b3[
        [
            "week",
            "symptom_id",
            "symptom_name",
            "hospitals_observed",
            "hospitals_increasing",
            "average_growth_rate",
            "spread_proportion",
            "cross_hospital_alert",
        ]
    ].copy()

    # ---------------------------------------------------------------
    # Merge all layers
    # ---------------------------------------------------------------

    result = surveillance.merge(
        baseline,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    result = result.merge(
        anomaly,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    result = result.merge(
        persistence,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    return result


# -------------------------------------------------------------------
# Calculate B7 risk score
# -------------------------------------------------------------------

def calculate_risk_score(row):

    # ---------------------------------------------------------------
    # COMPONENT 1 — Cross-hospital spread
    # Weight: 25%
    # ---------------------------------------------------------------

    spread = row["spread_proportion"]

    if pd.isna(spread):
        spread = 0

    spread_score = (
        max(
            0,
            min(
                spread,
                1
            )
        )
        * 25
    )

    # ---------------------------------------------------------------
    # COMPONENT 2 — Current growth
    # Weight: 20%
    # ---------------------------------------------------------------

    growth = row[
        "average_growth_rate"
    ]

    if pd.isna(growth):
        growth = 0

    growth = max(
        0,
        min(
            growth,
            100
        )
    )

    growth_score = (
        growth / 100
    ) * 20

    # ---------------------------------------------------------------
    # COMPONENT 3 — Anomaly strength
    # Weight: 25%
    # ---------------------------------------------------------------

    anomaly_score = row[
        "anomaly_score"
    ]

    if pd.isna(anomaly_score):
        anomaly_score = 0

    anomaly_score = max(
        0,
        min(
            anomaly_score,
            100
        )
    )

    anomaly_component = (
        anomaly_score / 100
    ) * 25

    # ---------------------------------------------------------------
    # COMPONENT 4 — Persistence
    # Weight: 20%
    # ---------------------------------------------------------------

    persistence_score = row[
        "persistence_score"
    ]

    if pd.isna(persistence_score):
        persistence_score = 0

    persistence_score = max(
        0,
        min(
            persistence_score,
            100
        )
    )

    persistence_component = (
        persistence_score / 100
    ) * 20

    # ---------------------------------------------------------------
    # COMPONENT 5 — Hospital growth coverage
    # Weight: 10%
    # ---------------------------------------------------------------

    hospitals_increasing = row[
        "hospitals_increasing"
    ]

    if pd.isna(hospitals_increasing):
        hospitals_increasing = 0

    growth_hospital_component = (
        min(
            hospitals_increasing / 5,
            1
        )
        * 10
    )

    score = (
        spread_score
        + growth_score
        + anomaly_component
        + persistence_component
        + growth_hospital_component
    )

    return round(
        min(score, 100),
        2
    )


# -------------------------------------------------------------------
# Final outbreak risk classification
# -------------------------------------------------------------------

def classify_risk(row):

    score = row[
        "outbreak_risk_score"
    ]

    persistent_signal = bool(
        row[
            "persistent_outbreak_signal"
        ]
    )

    anomaly_alert = row[
        "anomaly_alert"
    ]

    cross_alert = row[
        "cross_hospital_alert"
    ]

    persistence_alert = row[
        "cross_hospital_persistence_alert"
    ]

    hospitals_increasing = row[
        "hospitals_increasing"
    ]

    persistent_hospitals = row[
        "persistent_hospitals"
    ]

    # ---------------------------------------------------------------
    # RED
    #
    # Requires a strong combination of:
    #   - high numerical score
    #   - multi-hospital persistence
    #   - current growth
    #
    # This avoids turning isolated anomalies into outbreaks.
    # ---------------------------------------------------------------

    if (
        score >= 75
        and persistent_hospitals >= 4
        and hospitals_increasing >= 3
        and (
            persistent_signal
            or persistence_alert == "RED"
        )
    ):
        return "RED"

    # ---------------------------------------------------------------
    # ORANGE
    # ---------------------------------------------------------------

    if (
        score >= 55
        and (
            persistence_alert in [
                "ORANGE",
                "RED",
            ]
            or cross_alert in [
                "ORANGE",
                "RED",
            ]
        )
    ):
        return "ORANGE"

    # ---------------------------------------------------------------
    # YELLOW
    #
    # Early warning / investigation signal.
    # ---------------------------------------------------------------

    if (
        score >= 35
        and (
            anomaly_alert in [
                "YELLOW",
                "ORANGE",
                "RED",
            ]
            or cross_alert in [
                "YELLOW",
                "ORANGE",
                "RED",
            ]
            or persistence_alert in [
                "YELLOW",
                "ORANGE",
                "RED",
            ]
        )
    ):
        return "YELLOW"

    return "GREEN"


# -------------------------------------------------------------------
# Risk interpretation
# -------------------------------------------------------------------

def generate_interpretation(row):

    risk = row[
        "outbreak_risk_level"
    ]

    if risk == "RED":

        return (
            "High-risk multi-hospital outbreak signal "
            "with sustained anomaly and current growth."
        )

    if risk == "ORANGE":

        return (
            "Significant cross-hospital signal requiring "
            "public-health investigation."
        )

    if risk == "YELLOW":

        return (
            "Early warning signal; monitor trend and "
            "investigate contributing hospitals."
        )

    return (
        "No significant persistent outbreak signal."
    )


# -------------------------------------------------------------------
# Main B7 pipeline
# -------------------------------------------------------------------

def run_b7():

    print("=" * 80)
    print("B7 - FINAL OUTBREAK RISK ASSESSMENT")
    print("=" * 80)

    # ---------------------------------------------------------------
    # Load
    # ---------------------------------------------------------------

    b3 = load_b3()
    b4 = load_b4()
    b5 = load_b5()
    b6 = load_b6()

    print(
        f"B3 input rows: {len(b3)}"
    )

    print(
        f"B4 input rows: {len(b4)}"
    )

    print(
        f"B5 input rows: {len(b5)}"
    )

    print(
        f"B6 input rows: {len(b6)}"
    )

    # ---------------------------------------------------------------
    # Build combined dataset
    # ---------------------------------------------------------------

    result = build_risk_dataset(
        b3,
        b4,
        b5,
        b6
    )

    print(
        f"Combined rows: {len(result)}"
    )

    # ---------------------------------------------------------------
    # Calculate risk
    # ---------------------------------------------------------------

    result[
        "outbreak_risk_score"
    ] = result.apply(
        calculate_risk_score,
        axis=1
    )

    # ---------------------------------------------------------------
    # Classify
    # ---------------------------------------------------------------

    result[
        "outbreak_risk_level"
    ] = result.apply(
        classify_risk,
        axis=1
    )

    # ---------------------------------------------------------------
    # Interpretation
    # ---------------------------------------------------------------

    result[
        "risk_interpretation"
    ] = result.apply(
        generate_interpretation,
        axis=1
    )

    # ---------------------------------------------------------------
    # Final signal
    # ---------------------------------------------------------------

    result[
        "final_outbreak_signal"
    ] = (
        result[
            "outbreak_risk_level"
        ].isin(
            [
                "ORANGE",
                "RED",
            ]
        )
    )

    # ---------------------------------------------------------------
    # Sort
    # ---------------------------------------------------------------

    result = result.sort_values(
        [
            "week",
            "outbreak_risk_score",
        ],
        ascending=[
            True,
            False,
        ]
    )

    # ---------------------------------------------------------------
    # Save
    # ---------------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    print()
    print(
        f"Output rows: {len(result)}"
    )

    print(
        f"Output saved: {OUTPUT_FILE}"
    )

    print()
    print(
        "Final outbreak risk summary:"
    )

    print(
        result[
            "outbreak_risk_level"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print(
        "Final outbreak signals:",
        int(
            result[
                "final_outbreak_signal"
            ].sum()
        )
    )

    # ---------------------------------------------------------------
    # Latest week
    # ---------------------------------------------------------------

    latest_week = result[
        "week"
    ].max()

    latest = result[
        result["week"] == latest_week
    ].copy()

    latest = latest.sort_values(
        "outbreak_risk_score",
        ascending=False
    )

    print()
    print(
        f"Latest surveillance week: "
        f"{latest_week.date()}"
    )

    print()

    print(
        latest[
            [
                "symptom_id",
                "symptom_name",
                "hospitals_observed",
                "hospitals_increasing",
                "baseline_anomalous_hospitals",
                "persistent_hospitals",
                "cross_hospital_consecutive_weeks",
                "anomaly_score",
                "persistence_score",
                "outbreak_risk_score",
                "outbreak_risk_level",
                "final_outbreak_signal",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print()
    print("=" * 80)
    print("B7 COMPLETE")
    print("=" * 80)

    return result


if __name__ == "__main__":
    run_b7()
from pathlib import Path

import pandas as pd
import numpy as np


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent

B2_FILE = CURRENT_DIR / "symptom_weekly_surveillance.csv"
B3_FILE = CURRENT_DIR / "cross_hospital_symptom_surveillance.csv"
B4_FILE = CURRENT_DIR / "symptom_historical_baseline.csv"

OUTPUT_FILE = CURRENT_DIR / "symptom_anomaly_detection.csv"

TOTAL_HOSPITALS = 10


# -------------------------------------------------------------------
# Load B2
# -------------------------------------------------------------------

def load_b2():

    if not B2_FILE.exists():
        raise FileNotFoundError(
            f"B2 output not found: {B2_FILE}"
        )

    df = pd.read_csv(B2_FILE)

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce"
    )

    return df


# -------------------------------------------------------------------
# Load B3
# -------------------------------------------------------------------

def load_b3():

    if not B3_FILE.exists():
        raise FileNotFoundError(
            f"B3 output not found: {B3_FILE}"
        )

    df = pd.read_csv(B3_FILE)

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce"
    )

    return df


# -------------------------------------------------------------------
# Load B4
# -------------------------------------------------------------------

def load_b4():

    if not B4_FILE.exists():
        raise FileNotFoundError(
            f"B4 output not found: {B4_FILE}"
        )

    df = pd.read_csv(B4_FILE)

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce"
    )

    numeric_columns = [
        "historical_mean",
        "historical_std",
        "deviation_percent",
        "z_score",
    ]

    for column in numeric_columns:

        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


# -------------------------------------------------------------------
# Build B4 hospital-level anomaly information
# -------------------------------------------------------------------

def aggregate_baseline_signals(b4):

    # Only observations with enough history
    valid = b4[
        b4["baseline_alert"]
        != "INSUFFICIENT_HISTORY"
    ].copy()

    if valid.empty:
        return pd.DataFrame(
            columns=[
                "week",
                "symptom_id",
                "symptom_name",
                "average_baseline_z",
                "max_baseline_z",
                "average_deviation_percent",
                "baseline_red_hospitals",
                "baseline_orange_hospitals",
                "baseline_yellow_hospitals",
            ]
        )

    # Replace infinite values before aggregation
    valid["z_score"] = (
        valid["z_score"]
        .replace([np.inf, -np.inf], np.nan)
    )

    valid["deviation_percent"] = (
        valid["deviation_percent"]
        .replace([np.inf, -np.inf], np.nan)
    )

    # ---------------------------------------------------------------
    # Hospital alert counts
    # ---------------------------------------------------------------

    valid["is_red"] = (
        valid["baseline_alert"] == "RED"
    )

    valid["is_orange"] = (
        valid["baseline_alert"] == "ORANGE"
    )

    valid["is_yellow"] = (
        valid["baseline_alert"] == "YELLOW"
    )

    result = (
        valid.groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
            ],
            as_index=False
        )
        .agg(
            average_baseline_z=(
                "z_score",
                "mean"
            ),

            max_baseline_z=(
                "z_score",
                "max"
            ),

            average_deviation_percent=(
                "deviation_percent",
                "mean"
            ),

            baseline_red_hospitals=(
                "is_red",
                "sum"
            ),

            baseline_orange_hospitals=(
                "is_orange",
                "sum"
            ),

            baseline_yellow_hospitals=(
                "is_yellow",
                "sum"
            ),
        )
    )

    return result


# -------------------------------------------------------------------
# Normalize historical anomaly
# -------------------------------------------------------------------

def historical_score(z):

    if pd.isna(z):
        return 0.0

    # Cap extreme values so one tiny-count symptom
    # does not dominate the composite score.
    z = max(0.0, min(z, 5.0))

    return (z / 5.0) * 100.0


# -------------------------------------------------------------------
# Normalize cross-hospital spread
# -------------------------------------------------------------------

def spread_score(row):

    spread = row["spread_proportion"]

    if pd.isna(spread):
        return 0.0

    return max(
        0.0,
        min(spread * 100.0, 100.0)
    )


# -------------------------------------------------------------------
# Normalize coordinated growth
# -------------------------------------------------------------------

def growth_score(row):

    growth = row["average_growth_rate"]

    if pd.isna(growth):
        return 0.0

    # Negative growth = no growth signal
    growth = max(0.0, growth)

    # Cap at 100% growth
    growth = min(growth, 100.0)

    return growth


# -------------------------------------------------------------------
# Normalize strong hospital alerts
# -------------------------------------------------------------------

def strong_hospital_score(row):

    strong = row["hospitals_orange_red"]

    if pd.isna(strong):
        return 0.0

    return min(
        (strong / TOTAL_HOSPITALS) * 100.0,
        100.0
    )


# -------------------------------------------------------------------
# Calculate composite anomaly score
# -------------------------------------------------------------------

def calculate_anomaly_score(row):

    historical = historical_score(
        row["max_baseline_z"]
    )

    spread = spread_score(row)

    growth = growth_score(row)

    strong = strong_hospital_score(row)

    score = (
        0.35 * historical
        + 0.30 * spread
        + 0.20 * growth
        + 0.15 * strong
    )

    return round(
        max(0.0, min(score, 100.0)),
        2
    )


# -------------------------------------------------------------------
# Classify anomaly
# -------------------------------------------------------------------

def classify_anomaly(score):

    if score >= 75:
        return "RED"

    if score >= 55:
        return "ORANGE"

    if score >= 35:
        return "YELLOW"

    return "GREEN"


# -------------------------------------------------------------------
# Determine outbreak signal
# -------------------------------------------------------------------

def determine_outbreak_signal(row):

    # A meaningful signal requires multiple hospitals
    # and evidence of either abnormality or growth.

    if row["hospitals_observed"] < 3:
        return False

    if row["hospitals_increasing"] < 2:
        return False

    if row["anomaly_score"] < 35:
        return False

    return True


# -------------------------------------------------------------------
# Main B5 pipeline
# -------------------------------------------------------------------

def run_b5():

    print("=" * 80)
    print("B5 - SYMPTOM ANOMALY / DEVIATION DETECTION")
    print("=" * 80)

    # ---------------------------------------------------------------
    # Load
    # ---------------------------------------------------------------

    b2 = load_b2()
    b3 = load_b3()
    b4 = load_b4()

    print(
        f"B2 rows: {len(b2)}"
    )

    print(
        f"B3 rows: {len(b3)}"
    )

    print(
        f"B4 rows: {len(b4)}"
    )

    # ---------------------------------------------------------------
    # B3 contains the cross-hospital signal
    # ---------------------------------------------------------------

    b3_columns = [
        "week",
        "symptom_id",
        "symptom_name",
        "hospitals_observed",
        "hospitals_increasing",
        "hospitals_orange_red",
        "average_growth_rate",
        "spread_proportion",
        "cross_hospital_alert",
        "potential_outbreak_signal",
    ]

    b3 = b3[b3_columns].copy()

    # ---------------------------------------------------------------
    # B4 hospital-level anomaly information
    # ---------------------------------------------------------------

    baseline = aggregate_baseline_signals(
        b4
    )

    # ---------------------------------------------------------------
    # Merge B3 + B4
    # ---------------------------------------------------------------

    result = b3.merge(
        baseline,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    # ---------------------------------------------------------------
    # Calculate composite anomaly score
    # ---------------------------------------------------------------

    result["anomaly_score"] = result.apply(
        calculate_anomaly_score,
        axis=1
    )

    # ---------------------------------------------------------------
    # Alert
    # ---------------------------------------------------------------

    result["anomaly_alert"] = (
        result["anomaly_score"]
        .apply(classify_anomaly)
    )

    # ---------------------------------------------------------------
    # Outbreak signal
    # ---------------------------------------------------------------

    result["potential_outbreak"] = result.apply(
        determine_outbreak_signal,
        axis=1
    )

    # ---------------------------------------------------------------
    # Fill missing numerical values
    # ---------------------------------------------------------------

    count_columns = [
        "baseline_red_hospitals",
        "baseline_orange_hospitals",
        "baseline_yellow_hospitals",
    ]

    for column in count_columns:

        result[column] = (
            result[column]
            .fillna(0)
            .astype(int)
        )

    # ---------------------------------------------------------------
    # Sort
    # ---------------------------------------------------------------

    result = result.sort_values(
        [
            "week",
            "anomaly_score",
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
    print("Anomaly alert summary:")

    print(
        result["anomaly_alert"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print(
        "Potential outbreak signals:",
        int(
            result["potential_outbreak"]
            .sum()
        )
    )

    # ---------------------------------------------------------------
    # Latest week
    # ---------------------------------------------------------------

    latest_week = result["week"].max()

    latest = result[
        result["week"] == latest_week
    ].copy()

    latest = latest.sort_values(
        "anomaly_score",
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
                "average_growth_rate",
                "average_baseline_z",
                "max_baseline_z",
                "spread_proportion",
                "anomaly_score",
                "anomaly_alert",
                "potential_outbreak",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print()
    print("=" * 80)
    print("B5 COMPLETE")
    print("=" * 80)

    return result


if __name__ == "__main__":
    run_b5()
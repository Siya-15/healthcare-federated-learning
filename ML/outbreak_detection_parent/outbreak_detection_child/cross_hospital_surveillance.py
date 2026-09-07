from pathlib import Path

import pandas as pd
import numpy as np


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent

INPUT_FILE = CURRENT_DIR / "symptom_weekly_surveillance.csv"
OUTPUT_FILE = CURRENT_DIR / "cross_hospital_symptom_surveillance.csv"

TOTAL_HOSPITALS = 10


# -------------------------------------------------------------------
# Load B2 output
# -------------------------------------------------------------------

def load_symptom_surveillance():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"B2 output not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "week",
        "hospital_id",
        "symptom_id",
        "symptom_name",
        "case_count",
        "previous_cases",
        "growth_rate",
        "hospital_total_cases",
        "incidence_proportion",
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    return df


# -------------------------------------------------------------------
# Prepare data
# -------------------------------------------------------------------

def prepare_data(df):
    df = df.copy()

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce"
    )

    df["growth_rate"] = pd.to_numeric(
        df["growth_rate"],
        errors="coerce"
    )

    df["case_count"] = pd.to_numeric(
        df["case_count"],
        errors="coerce"
    )

    df["incidence_proportion"] = pd.to_numeric(
        df["incidence_proportion"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "week",
            "hospital_id",
            "symptom_id",
            "case_count",
        ]
    )

    return df


# -------------------------------------------------------------------
# Hospital-level signal classification
# -------------------------------------------------------------------

def classify_growth(growth):
    if pd.isna(growth):
        return "NO_PREVIOUS_DATA"

    if growth < 25:
        return "GREEN"

    if growth < 50:
        return "YELLOW"

    if growth < 100:
        return "ORANGE"

    return "RED"


# -------------------------------------------------------------------
# Cross-hospital aggregation
# -------------------------------------------------------------------

def calculate_cross_hospital_spread(df):

    # ---------------------------------------------------------------
    # Number of hospitals where symptom is observed
    # ---------------------------------------------------------------

    observed = (
        df.groupby(
            ["week", "symptom_id", "symptom_name"]
        )
        .agg(
            hospitals_observed=(
                "hospital_id",
                "nunique"
            ),

            total_cases=(
                "case_count",
                "sum"
            ),

            average_cases_per_hospital=(
                "case_count",
                "mean"
            ),

            average_growth_rate=(
                "growth_rate",
                "mean"
            ),

            median_growth_rate=(
                "growth_rate",
                "median"
            ),

            average_incidence_proportion=(
                "incidence_proportion",
                "mean"
            ),
        )
        .reset_index()
    )

    # ---------------------------------------------------------------
    # Hospitals with increasing symptom activity
    # ---------------------------------------------------------------

    increasing = (
        df.assign(
            is_increasing=df["growth_rate"] > 25
        )
        .groupby(
            ["week", "symptom_id", "symptom_name"]
        )
        .agg(
            hospitals_increasing=(
                "is_increasing",
                "sum"
            )
        )
        .reset_index()
    )

    # ---------------------------------------------------------------
    # Hospitals with strong increase
    # ---------------------------------------------------------------

    orange_red = (
        df.assign(
            strong_alert=df["growth_rate"] >= 50
        )
        .groupby(
            ["week", "symptom_id", "symptom_name"]
        )
        .agg(
            hospitals_orange_red=(
                "strong_alert",
                "sum"
            )
        )
        .reset_index()
    )

    # ---------------------------------------------------------------
    # Merge
    # ---------------------------------------------------------------

    result = observed.merge(
        increasing,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    result = result.merge(
        orange_red,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    # ---------------------------------------------------------------
    # Spread proportion
    # ---------------------------------------------------------------

    result["spread_proportion"] = (
        result["hospitals_observed"] /
        TOTAL_HOSPITALS
    )

    result["increasing_hospital_proportion"] = (
        result["hospitals_increasing"] /
        TOTAL_HOSPITALS
    )

    # ---------------------------------------------------------------
    # Cross-hospital alert
    #
    # This is a prototype project threshold, not a
    # clinical/public-health standard.
    # ---------------------------------------------------------------

    def determine_alert(row):

        spread = row["spread_proportion"]
        increasing = row["increasing_hospital_proportion"]
        strong = row["hospitals_orange_red"]

        # RED:
        # widespread signal + several hospitals showing
        # strong increases
        if spread >= 0.75 and strong >= 5:
            return "RED"

        # ORANGE:
        # signal present in at least half of hospitals
        # and meaningful increase across hospitals
        if spread >= 0.50 and increasing >= 0.30:
            return "ORANGE"

        # YELLOW:
        # signal spreading to multiple hospitals
        # or showing moderate coordinated growth
        if spread >= 0.30 and increasing >= 0.20:
            return "YELLOW"

        return "GREEN"

    result["cross_hospital_alert"] = result.apply(
        determine_alert,
        axis=1
    )

    # ---------------------------------------------------------------
    # Potential outbreak signal
    # ---------------------------------------------------------------

    result["potential_outbreak_signal"] = (
        (
            result["hospitals_observed"] >= 3
        )
        &
        (
            result["hospitals_increasing"] >= 2
        )
        &
        (
            result["average_growth_rate"] >= 25
        )
    )

    return result


# -------------------------------------------------------------------
# Rank strongest cross-hospital signals
# -------------------------------------------------------------------

def rank_signals(df):

    df = df.copy()

    alert_score = {
        "GREEN": 0,
        "YELLOW": 1,
        "ORANGE": 2,
        "RED": 3,
    }

    df["alert_score"] = (
        df["cross_hospital_alert"]
        .map(alert_score)
        .fillna(0)
    )

    df = df.sort_values(
        [
            "week",
            "alert_score",
            "hospitals_observed",
            "average_growth_rate",
        ],
        ascending=[
            True,
            False,
            False,
            False,
        ]
    )

    return df.drop(
        columns=["alert_score"]
    )


# -------------------------------------------------------------------
# Main B3 pipeline
# -------------------------------------------------------------------

def run_b3():

    print("=" * 80)
    print("B3 - CROSS-HOSPITAL SYMPTOM SURVEILLANCE")
    print("=" * 80)

    # Load B2
    df = load_symptom_surveillance()

    print(f"B2 input rows: {len(df)}")

    # Prepare
    df = prepare_data(df)

    # Calculate cross-hospital spread
    result = calculate_cross_hospital_spread(df)

    # Rank
    result = rank_signals(result)

    # Save
    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print(f"Output rows: {len(result)}")
    print(f"Output saved: {OUTPUT_FILE}")

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    print()
    print("Cross-hospital alert summary:")

    print(
        result["cross_hospital_alert"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print(
        "Potential outbreak signals:",
        int(
            result["potential_outbreak_signal"]
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
        [
            "cross_hospital_alert",
            "hospitals_observed",
            "average_growth_rate",
        ],
        ascending=[
            True,
            False,
            False,
        ]
    )

    print()
    print(f"Latest surveillance week: {latest_week.date()}")

    print()

    print(
        latest[
            [
                "symptom_id",
                "symptom_name",
                "hospitals_observed",
                "hospitals_increasing",
                "average_growth_rate",
                "spread_proportion",
                "cross_hospital_alert",
                "potential_outbreak_signal",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )

    print()
    print("=" * 80)
    print("B3 COMPLETE")
    print("=" * 80)

    return result


if __name__ == "__main__":
    run_b3()
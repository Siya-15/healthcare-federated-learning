from pathlib import Path

import pandas as pd
import numpy as np


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent

INPUT_FILE = CURRENT_DIR / "symptom_weekly_surveillance.csv"
OUTPUT_FILE = CURRENT_DIR / "symptom_historical_baseline.csv"

TOTAL_HOSPITALS = 10
MINIMUM_HISTORY_WEEKS = 4


# -------------------------------------------------------------------
# Load B2 data
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
        "hospital_total_cases",
        "incidence_proportion",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
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

    df["case_count"] = pd.to_numeric(
        df["case_count"],
        errors="coerce"
    )

    df["hospital_total_cases"] = pd.to_numeric(
        df["hospital_total_cases"],
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
# Build complete hospital × symptom × week grid
# -------------------------------------------------------------------

def build_complete_grid(df):

    weeks = sorted(
        df["week"].unique()
    )

    hospitals = sorted(
        df["hospital_id"].unique()
    )

    symptoms = (
        df[
            [
                "symptom_id",
                "symptom_name",
            ]
        ]
        .drop_duplicates()
        .sort_values("symptom_id")
    )

    # Cartesian product
    grid = pd.MultiIndex.from_product(
        [
            weeks,
            hospitals,
            symptoms["symptom_id"],
        ],
        names=[
            "week",
            "hospital_id",
            "symptom_id",
        ],
    ).to_frame(index=False)

    # Add symptom names
    grid = grid.merge(
        symptoms,
        on="symptom_id",
        how="left"
    )

    # Add observed case counts
    observed = df[
        [
            "week",
            "hospital_id",
            "symptom_id",
            "case_count",
        ]
    ]

    grid = grid.merge(
        observed,
        on=[
            "week",
            "hospital_id",
            "symptom_id",
        ],
        how="left"
    )

    # Missing symptom = zero cases
    grid["case_count"] = (
        grid["case_count"]
        .fillna(0)
    )

    return grid


# -------------------------------------------------------------------
# Calculate historical baseline
# -------------------------------------------------------------------

def calculate_baseline(df):

    df = df.sort_values(
        [
            "hospital_id",
            "symptom_id",
            "week",
        ]
    ).copy()

    group_columns = [
        "hospital_id",
        "symptom_id",
    ]

    # ---------------------------------------------------------------
    # Previous observations
    #
    # shift() ensures the current week is NOT included in its
    # own historical baseline.
    # ---------------------------------------------------------------

    df["historical_mean"] = (
        df.groupby(group_columns)["case_count"]
        .transform(
            lambda x: x.shift(1).expanding().mean()
        )
    )

    df["historical_std"] = (
        df.groupby(group_columns)["case_count"]
        .transform(
            lambda x: x.shift(1).expanding().std()
        )
    )

    df["historical_weeks"] = (
        df.groupby(group_columns)
        .cumcount()
    )

    # ---------------------------------------------------------------
    # Current cases
    # ---------------------------------------------------------------

    df["current_cases"] = df["case_count"]

    # ---------------------------------------------------------------
    # Absolute deviation
    # ---------------------------------------------------------------

    df["deviation_from_baseline"] = (
        df["current_cases"] -
        df["historical_mean"]
    )

    # ---------------------------------------------------------------
    # Percentage deviation
    # ---------------------------------------------------------------

    def calculate_deviation_percent(row):

        baseline = row["historical_mean"]
        current = row["current_cases"]

        if pd.isna(baseline):
            return np.nan

        if baseline == 0:

            if current == 0:
                return 0.0

            return np.inf

        return (
            (current - baseline) /
            baseline
        ) * 100

    df["deviation_percent"] = df.apply(
        calculate_deviation_percent,
        axis=1
    )

    # ---------------------------------------------------------------
    # Z-score
    # ---------------------------------------------------------------

    def calculate_z_score(row):

        mean = row["historical_mean"]
        std = row["historical_std"]
        current = row["current_cases"]

        if pd.isna(mean):
            return np.nan

        # Not enough variation to calculate a meaningful z-score
        if pd.isna(std) or std == 0:

            if current > mean:
                return np.inf

            if current == mean:
                return 0.0

            return -np.inf

        return (
            (current - mean) /
            std
        )

    df["z_score"] = df.apply(
        calculate_z_score,
        axis=1
    )

    return df


# -------------------------------------------------------------------
# Baseline alert classification
# -------------------------------------------------------------------

def classify_baseline_alert(row):

    history = row["historical_weeks"]
    z_score = row["z_score"]
    deviation = row["deviation_percent"]

    # Not enough historical observations
    if history < MINIMUM_HISTORY_WEEKS:
        return "INSUFFICIENT_HISTORY"

    # Missing baseline
    if pd.isna(z_score):
        return "INSUFFICIENT_HISTORY"

    # Strong statistical deviation
    if z_score >= 3:
        return "RED"

    # Moderate/strong deviation
    if z_score >= 2:
        return "ORANGE"

    # Noticeable deviation
    if z_score >= 1.5:
        return "YELLOW"

    # Handle cases where baseline is zero
    if np.isinf(deviation) and deviation > 0:
        return "ORANGE"

    return "GREEN"


# -------------------------------------------------------------------
# Add alert classification
# -------------------------------------------------------------------

def add_alerts(df):

    df = df.copy()

    df["baseline_alert"] = df.apply(
        classify_baseline_alert,
        axis=1
    )

    return df


# -------------------------------------------------------------------
# Select output columns
# -------------------------------------------------------------------

def prepare_output(df):

    output = df[
        [
            "week",
            "hospital_id",
            "symptom_id",
            "symptom_name",
            "current_cases",
            "historical_weeks",
            "historical_mean",
            "historical_std",
            "deviation_from_baseline",
            "deviation_percent",
            "z_score",
            "baseline_alert",
        ]
    ].copy()

    output = output.sort_values(
        [
            "week",
            "hospital_id",
            "symptom_id",
        ]
    )

    return output


# -------------------------------------------------------------------
# Main B4 pipeline
# -------------------------------------------------------------------

def run_b4():

    print("=" * 80)
    print("B4 - HISTORICAL SYMPTOM BASELINE")
    print("=" * 80)

    # Load B2
    df = load_symptom_surveillance()

    print(
        f"B2 input rows: {len(df)}"
    )

    # Prepare
    df = prepare_data(df)

    # Build complete time series
    baseline_data = build_complete_grid(df)

    print(
        f"Complete grid rows: "
        f"{len(baseline_data)}"
    )

    # Calculate baseline
    baseline_data = calculate_baseline(
        baseline_data
    )

    # Add alerts
    baseline_data = add_alerts(
        baseline_data
    )

    # Prepare final output
    output = prepare_output(
        baseline_data
    )

    # Save
    output.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    print()
    print(
        f"Output rows: {len(output)}"
    )

    print(
        f"Output saved: {OUTPUT_FILE}"
    )

    print()
    print("Baseline alert summary:")

    print(
        output["baseline_alert"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # ---------------------------------------------------------------
    # Latest week
    # ---------------------------------------------------------------

    latest_week = output["week"].max()

    latest = output[
        output["week"] == latest_week
    ].copy()

    latest = latest[
        latest["baseline_alert"]
        != "INSUFFICIENT_HISTORY"
    ]

    latest = latest.sort_values(
        [
            "z_score",
            "deviation_percent",
        ],
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
                "hospital_id",
                "symptom_id",
                "symptom_name",
                "current_cases",
                "historical_mean",
                "historical_std",
                "deviation_percent",
                "z_score",
                "baseline_alert",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print()
    print("=" * 80)
    print("B4 COMPLETE")
    print("=" * 80)

    return output


if __name__ == "__main__":
    run_b4()
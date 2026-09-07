from pathlib import Path

import numpy as np
import pandas as pd


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent

B2_FILE = CURRENT_DIR / "symptom_weekly_surveillance.csv"
OUTPUT_FILE = CURRENT_DIR / "temporal_acceleration.csv"

# Exponential fitting
MIN_FIT_WEEKS = 4
RECENT_FIT_WEEKS = 6

# Change-point detection
MIN_PREVIOUS_CASES = 5
MIN_CURRENT_CASES = 8

POSITIVE_GROWTH_THRESHOLD = 10.0
CHANGE_POINT_GROWTH_JUMP = 25.0
CHANGE_POINT_ACCELERATION = 15.0

# A change point older than this is not treated as a
# current temporal-acceleration signal.
RECENT_CHANGE_POINT_WEEKS = 2


# -------------------------------------------------------------------
# Load B2
# -------------------------------------------------------------------

def load_b2():

    if not B2_FILE.exists():
        raise FileNotFoundError(
            f"B2 output not found: {B2_FILE}"
        )

    df = pd.read_csv(B2_FILE)

    required = [
        "week",
        "hospital_id",
        "symptom_id",
        "symptom_name",
        "case_count",
        "previous_cases",
        "growth_rate",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"B2 missing required columns: {missing}"
        )

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce"
    )

    numeric_columns = [
        "case_count",
        "previous_cases",
        "growth_rate",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna(
        subset=[
            "week",
            "hospital_id",
            "symptom_id",
        ]
    )

    return df


# -------------------------------------------------------------------
# Build hospital trajectories
# -------------------------------------------------------------------

def build_hospital_trajectory(b2):

    df = b2[
        [
            "week",
            "hospital_id",
            "symptom_id",
            "symptom_name",
            "case_count",
            "previous_cases",
            "growth_rate",
        ]
    ].copy()

    df = df.sort_values(
        [
            "hospital_id",
            "symptom_id",
            "week",
        ]
    ).reset_index(drop=True)

    # ---------------------------------------------------------------
    # Previous growth
    # ---------------------------------------------------------------

    df["previous_growth_rate"] = (
        df.groupby(
            [
                "hospital_id",
                "symptom_id",
            ]
        )["growth_rate"]
        .shift(1)
    )

    # ---------------------------------------------------------------
    # Growth acceleration
    # ---------------------------------------------------------------

    df["growth_acceleration"] = (
        df["growth_rate"]
        - df["previous_growth_rate"]
    )

    # ---------------------------------------------------------------
    # Previous case change
    # ---------------------------------------------------------------

    df["previous_case_change"] = (
        df.groupby(
            [
                "hospital_id",
                "symptom_id",
            ]
        )["previous_cases"]
        .shift(1)
    )

    # ---------------------------------------------------------------
    # Second-order case acceleration
    # ---------------------------------------------------------------

    df["case_acceleration"] = (
        df["case_count"]
        - 2 * df["previous_cases"]
        + df["previous_case_change"]
    )

    return df


# -------------------------------------------------------------------
# Change-point detection
# -------------------------------------------------------------------

def detect_change_points(df):

    df = df.copy()

    df["change_point"] = False
    df["change_point_strength"] = 0.0

    grouped_indices = (
        df.groupby(
            [
                "hospital_id",
                "symptom_id",
            ]
        ).groups
    )

    for (
        hospital_id,
        symptom_id
    ), indices in grouped_indices.items():

        indices = list(indices)

        indices = sorted(
            indices,
            key=lambda idx: df.loc[idx, "week"]
        )

        for position in range(
            1,
            len(indices)
        ):

            current_index = indices[
                position
            ]

            previous_index = indices[
                position - 1
            ]

            current_cases = df.loc[
                current_index,
                "case_count"
            ]

            previous_cases = df.loc[
                current_index,
                "previous_cases"
            ]

            current_growth = df.loc[
                current_index,
                "growth_rate"
            ]

            previous_growth = df.loc[
                previous_index,
                "growth_rate"
            ]

            acceleration = df.loc[
                current_index,
                "growth_acceleration"
            ]

            if pd.isna(current_cases):
                continue

            if pd.isna(previous_cases):
                continue

            if pd.isna(current_growth):
                continue

            if pd.isna(previous_growth):
                continue

            if pd.isna(acceleration):
                continue

            # -------------------------------------------------------
            # Prevent tiny-count percentage jumps.
            # -------------------------------------------------------

            if previous_cases < MIN_PREVIOUS_CASES:
                continue

            if current_cases < MIN_CURRENT_CASES:
                continue

            # -------------------------------------------------------
            # Growth jump.
            # -------------------------------------------------------

            growth_jump = (
                current_growth
                - previous_growth
            )

            # -------------------------------------------------------
            # Change point.
            # -------------------------------------------------------

            if (
                current_growth
                >= POSITIVE_GROWTH_THRESHOLD
                and growth_jump
                >= CHANGE_POINT_GROWTH_JUMP
                and acceleration
                >= CHANGE_POINT_ACCELERATION
            ):

                df.loc[
                    current_index,
                    "change_point"
                ] = True

                strength = min(
                    100.0,
                    max(
                        0.0,
                        growth_jump
                        + acceleration
                    )
                )

                df.loc[
                    current_index,
                    "change_point_strength"
                ] = round(
                    strength,
                    2
                )

    return df


# -------------------------------------------------------------------
# Exponential growth fitting
# -------------------------------------------------------------------

def fit_exponential_growth(df):

    df = df.copy()

    df[
        "exponential_growth_rate"
    ] = np.nan

    df[
        "doubling_time_weeks"
    ] = np.nan

    df[
        "growth_fit_r2"
    ] = np.nan

    df[
        "exponential_growth_detected"
    ] = False

    grouped_indices = (
        df.groupby(
            [
                "hospital_id",
                "symptom_id",
            ]
        ).groups
    )

    for (
        hospital_id,
        symptom_id
    ), indices in grouped_indices.items():

        indices = list(indices)

        indices = sorted(
            indices,
            key=lambda idx: df.loc[idx, "week"]
        )

        recent_indices = indices[
            -RECENT_FIT_WEEKS:
        ]

        if len(recent_indices) < MIN_FIT_WEEKS:
            continue

        cases = []
        valid_indices = []

        for index in recent_indices:

            value = df.loc[
                index,
                "case_count"
            ]

            if pd.isna(value):
                continue

            if value <= 0:
                continue

            cases.append(
                float(value)
            )

            valid_indices.append(
                index
            )

        if len(cases) < MIN_FIT_WEEKS:
            continue

        cases = np.asarray(
            cases,
            dtype=float
        )

        time_values = np.arange(
            len(cases),
            dtype=float
        )

        log_cases = np.log(
            cases
        )

        slope, intercept = np.polyfit(
            time_values,
            log_cases,
            1
        )

        predicted = (
            intercept
            + slope * time_values
        )

        ss_res = np.sum(
            (
                log_cases
                - predicted
            ) ** 2
        )

        ss_tot = np.sum(
            (
                log_cases
                - np.mean(log_cases)
            ) ** 2
        )

        if ss_tot == 0:

            r2 = 1.0

        else:

            r2 = (
                1
                - ss_res / ss_tot
            )

        if slope > 0:

            doubling_time = (
                np.log(2)
                / slope
            )

        else:

            doubling_time = np.nan

        latest_index = valid_indices[-1]

        latest_cases = cases[-1]

        detected = (
            slope > 0
            and r2 >= 0.70
            and latest_cases >= MIN_CURRENT_CASES
        )

        df.loc[
            latest_index,
            "exponential_growth_rate"
        ] = slope

        df.loc[
            latest_index,
            "doubling_time_weeks"
        ] = doubling_time

        df.loc[
            latest_index,
            "growth_fit_r2"
        ] = r2

        df.loc[
            latest_index,
            "exponential_growth_detected"
        ] = detected

    return df


# -------------------------------------------------------------------
# Aggregate temporal evidence
# -------------------------------------------------------------------

def aggregate_temporal_evidence(
    hospital_df
):

    result = (
        hospital_df.groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
            ],
            as_index=False
        )
        .agg(
            current_cases=(
                "case_count",
                "sum"
            ),

            # Current temporal state
            average_growth_rate=(
                "growth_rate",
                "mean"
            ),

            median_growth_rate=(
                "growth_rate",
                "median"
            ),

            average_growth_acceleration=(
                "growth_acceleration",
                "mean"
            ),

            maximum_growth_acceleration=(
                "growth_acceleration",
                "max"
            ),

            # Change-point evidence
            hospitals_with_change_point=(
                "change_point",
                "sum"
            ),

            maximum_change_point_strength=(
                "change_point_strength",
                "max"
            ),

            # Exponential evidence
            hospitals_with_exponential_growth=(
                "exponential_growth_detected",
                "sum"
            ),

            average_exponential_growth_rate=(
                "exponential_growth_rate",
                "mean"
            ),

            minimum_doubling_time_weeks=(
                "doubling_time_weeks",
                "min"
            ),

            average_growth_fit_r2=(
                "growth_fit_r2",
                "mean"
            ),
        )
    )

    return result


# -------------------------------------------------------------------
# Add recent change-point information
# -------------------------------------------------------------------

def add_recent_change_point_evidence(
    result,
    hospital_df
):

    latest_week = hospital_df[
        "week"
    ].max()

    # ---------------------------------------------------------------
    # Only change points occurring within the latest N weeks
    # contribute to the current acceleration signal.
    # ---------------------------------------------------------------

    cutoff_week = (
        latest_week
        - pd.Timedelta(
            weeks=RECENT_CHANGE_POINT_WEEKS
        )
    )

    recent = hospital_df[
        (
            hospital_df["week"]
            >= cutoff_week
        )
        &
        hospital_df["change_point"]
    ].copy()

    if recent.empty:

        result[
            "recent_change_point_hospitals"
        ] = 0

        result[
            "recent_change_point_strength"
        ] = 0.0

        return result

    recent_summary = (
        recent.groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
            ],
            as_index=False
        )
        .agg(
            recent_change_point_hospitals=(
                "hospital_id",
                "nunique"
            ),

            recent_change_point_strength=(
                "change_point_strength",
                "max"
            ),
        )
    )

    result = result.merge(
        recent_summary,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    result[
        "recent_change_point_hospitals"
    ] = (
        result[
            "recent_change_point_hospitals"
        ]
        .fillna(0)
        .astype(int)
    )

    result[
        "recent_change_point_strength"
    ] = (
        result[
            "recent_change_point_strength"
        ]
        .fillna(0)
    )

    return result


# -------------------------------------------------------------------
# Temporal acceleration score
# -------------------------------------------------------------------

def calculate_acceleration_score(row):

    # ---------------------------------------------------------------
    # COMPONENT 1 — Current growth
    #
    # Weight: 40%
    #
    # IMPORTANT:
    # Negative current growth contributes zero.
    # ---------------------------------------------------------------

    growth = row[
        "average_growth_rate"
    ]

    if pd.isna(growth):
        growth = 0

    positive_growth = max(
        0.0,
        growth
    )

    growth = min(
        positive_growth,
        100.0
    )

    growth_component = (
        growth / 100.0
    ) * 40.0

    # ---------------------------------------------------------------
    # COMPONENT 2 — Current growth acceleration
    #
    # Weight: 30%
    # ---------------------------------------------------------------

    acceleration = row[
        "average_growth_acceleration"
    ]

    if pd.isna(acceleration):
        acceleration = 0

    acceleration = max(
        0.0,
        min(
            acceleration,
            100.0
        )
    )

    acceleration_component = (
        acceleration / 100.0
    ) * 30.0

    # ---------------------------------------------------------------
    # COMPONENT 3 — Recent change point
    #
    # Weight: 20%
    # ---------------------------------------------------------------

    recent_change_points = row[
        "recent_change_point_hospitals"
    ]

    recent_change_strength = row[
        "recent_change_point_strength"
    ]

    if pd.isna(
        recent_change_points
    ):
        recent_change_points = 0

    if pd.isna(
        recent_change_strength
    ):
        recent_change_strength = 0

    # Number of hospitals contributes to the score.
    change_hospital_component = (
        min(
            recent_change_points / 3.0,
            1.0
        )
        * 10.0
    )

    # Strength contributes another 10%.
    change_strength_component = (
        min(
            recent_change_strength / 100.0,
            1.0
        )
        * 10.0
    )

    change_component = (
        change_hospital_component
        + change_strength_component
    )

    # ---------------------------------------------------------------
    # COMPONENT 4 — Exponential growth
    #
    # Weight: 10%
    # ---------------------------------------------------------------

    exponential_hospitals = row[
        "hospitals_with_exponential_growth"
    ]

    if pd.isna(exponential_hospitals):
        exponential_hospitals = 0

    exponential_component = (
        min(
            exponential_hospitals / 3.0,
            1.0
        )
        * 10.0
    )

    score = (
        growth_component
        + acceleration_component
        + change_component
        + exponential_component
    )

    # ---------------------------------------------------------------
    # Critical safeguard:
    #
    # If current average growth is negative, the temporal
    # acceleration score cannot exceed 20.
    #
    # This prevents an old acceleration event from producing
    # a current outbreak warning while the trajectory is declining.
    # ---------------------------------------------------------------

    if growth <= 0:

        score = min(
            score,
            20.0
        )

    return round(
        min(
            max(score, 0.0),
            100.0
        ),
        2
    )


# -------------------------------------------------------------------
# Temporal alert
# -------------------------------------------------------------------

def classify_temporal_alert(row):

    score = row[
        "temporal_acceleration_score"
    ]

    growth = row[
        "average_growth_rate"
    ]

    recent_change_points = row[
        "recent_change_point_hospitals"
    ]

    exponential_hospitals = row[
        "hospitals_with_exponential_growth"
    ]

    if pd.isna(growth):
        growth = 0

    if pd.isna(recent_change_points):
        recent_change_points = 0

    if pd.isna(exponential_hospitals):
        exponential_hospitals = 0

    # ---------------------------------------------------------------
    # A declining trajectory cannot receive a temporal outbreak
    # alert.
    # ---------------------------------------------------------------

    if growth <= 0:
        return "GREEN"

    # ---------------------------------------------------------------
    # RED
    # ---------------------------------------------------------------

    if (
        score >= 75
        and recent_change_points >= 3
        and exponential_hospitals >= 2
    ):
        return "RED"

    # ---------------------------------------------------------------
    # ORANGE
    # ---------------------------------------------------------------

    if (
        score >= 55
        and (
            recent_change_points >= 2
            or exponential_hospitals >= 2
        )
    ):
        return "ORANGE"

    # ---------------------------------------------------------------
    # YELLOW
    # ---------------------------------------------------------------

    if (
        score >= 35
        and (
            recent_change_points >= 1
            or exponential_hospitals >= 1
            or growth >= 25
        )
    ):
        return "YELLOW"

    return "GREEN"


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def run_b5():

    print("=" * 80)
    print("B5 - TEMPORAL ACCELERATION")
    print("=" * 80)

    # ---------------------------------------------------------------
    # Load
    # ---------------------------------------------------------------

    b2 = load_b2()

    print(
        f"B2 input rows: {len(b2)}"
    )

    print(
        f"Time range: "
        f"{b2['week'].min().date()} "
        f"-> "
        f"{b2['week'].max().date()}"
    )

    # ---------------------------------------------------------------
    # Hospital trajectories
    # ---------------------------------------------------------------

    hospital_df = (
        build_hospital_trajectory(
            b2
        )
    )

    print(
        f"Hospital trajectory rows: "
        f"{len(hospital_df)}"
    )

    # ---------------------------------------------------------------
    # Change points
    # ---------------------------------------------------------------

    hospital_df = (
        detect_change_points(
            hospital_df
        )
    )

    # ---------------------------------------------------------------
    # Exponential growth
    # ---------------------------------------------------------------

    hospital_df = (
        fit_exponential_growth(
            hospital_df
        )
    )

    # ---------------------------------------------------------------
    # Aggregate
    # ---------------------------------------------------------------

    result = (
        aggregate_temporal_evidence(
            hospital_df
        )
    )

    # ---------------------------------------------------------------
    # Recent change-point evidence
    # ---------------------------------------------------------------

    result = (
        add_recent_change_point_evidence(
            result,
            hospital_df
        )
    )

    # ---------------------------------------------------------------
    # Score
    # ---------------------------------------------------------------

    result[
        "temporal_acceleration_score"
    ] = result.apply(
        calculate_acceleration_score,
        axis=1
    )

    # ---------------------------------------------------------------
    # Alert
    # ---------------------------------------------------------------

    result[
        "temporal_alert"
    ] = result.apply(
        classify_temporal_alert,
        axis=1
    )

    result[
        "temporal_acceleration_signal"
    ] = (
        result[
            "temporal_alert"
        ].isin(
            [
                "YELLOW",
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
            "temporal_acceleration_score",
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
        "Temporal alert summary:"
    )

    print(
        result[
            "temporal_alert"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print(
        "Temporal acceleration signals:",
        int(
            result[
                "temporal_acceleration_signal"
            ].sum()
        )
    )

    print()
    print(
        "Total hospital change-point detections:",
        int(
            hospital_df[
                "change_point"
            ].sum()
        )
    )

    print(
        "Hospital exponential-growth detections:",
        int(
            hospital_df[
                "exponential_growth_detected"
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
        "temporal_acceleration_score",
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
                "current_cases",
                "average_growth_rate",
                "median_growth_rate",
                "average_growth_acceleration",
                "maximum_growth_acceleration",
                "hospitals_with_change_point",
                "recent_change_point_hospitals",
                "recent_change_point_strength",
                "hospitals_with_exponential_growth",
                "average_exponential_growth_rate",
                "minimum_doubling_time_weeks",
                "average_growth_fit_r2",
                "temporal_acceleration_score",
                "temporal_alert",
                "temporal_acceleration_signal",
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
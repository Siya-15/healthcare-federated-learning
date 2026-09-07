from pathlib import Path

import numpy as np
import pandas as pd


# ====================================================================
# CONFIGURATION
# ====================================================================

CURRENT_DIR = Path(__file__).resolve().parent

B2_FILE = CURRENT_DIR / "symptom_weekly_surveillance.csv"
B3_FILE = CURRENT_DIR / "symptom_historical_baseline.csv"
B4_FILE = CURRENT_DIR / "symptom_anomaly_detection.csv"
B5_FILE = CURRENT_DIR / "temporal_acceleration.csv"

OUTPUT_FILE = CURRENT_DIR / "symptom_persistence_detection.csv"


# Minimum consecutive abnormal weeks
MIN_PERSISTENT_WEEKS = 2

# Minimum hospitals showing persistent abnormality
MIN_PERSISTENT_HOSPITALS = 2

# Score thresholds
RED_PERSISTENCE_SCORE = 75
ORANGE_PERSISTENCE_SCORE = 55
YELLOW_PERSISTENCE_SCORE = 35


# ====================================================================
# GENERAL HELPERS
# ====================================================================

def load_csv(path, name):

    if not path.exists():
        raise FileNotFoundError(
            f"{name} output not found:\n{path}"
        )

    df = pd.read_csv(path)

    print(f"{name} rows: {len(df)}")

    return df


def normalize_week(df):

    df = df.copy()

    if "week" not in df.columns:
        raise ValueError(
            "Required column 'week' not found."
        )

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["week"]
    )

    return df


# ====================================================================
# LOAD B2
# ====================================================================

def load_b2():

    df = load_csv(
        B2_FILE,
        "B2"
    )

    required = [
        "week",
        "hospital_id",
        "symptom_id",
        "symptom_name",
        "case_count",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"B2 missing columns: {missing}"
        )

    df = normalize_week(df)

    df["case_count"] = pd.to_numeric(
        df["case_count"],
        errors="coerce"
    ).fillna(0)

    return df


# ====================================================================
# LOAD B3
# ====================================================================

def load_b3():

    df = load_csv(
        B3_FILE,
        "B3"
    )

    df = normalize_week(df)

    numeric_columns = [
        "current_cases",
        "historical_mean",
        "historical_std",
        "deviation_from_baseline",
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


# ====================================================================
# LOAD B4
# ====================================================================

def load_b4():

    df = load_csv(
        B4_FILE,
        "B4"
    )

    df = normalize_week(df)

    numeric_columns = [
        "anomaly_score",
        "z_score",
        "deviation_percent",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


# ====================================================================
# LOAD B5
# ====================================================================

def load_b5():

    df = load_csv(
        B5_FILE,
        "B5"
    )

    df = normalize_week(df)

    numeric_columns = [
        "temporal_acceleration_score",
        "average_growth_rate",
        "average_growth_acceleration",
        "recent_change_point_hospitals",
        "hospitals_with_exponential_growth",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


# ====================================================================
# B3 — LOCAL BASELINE SIGNAL
# ====================================================================

def prepare_b3_signal(b3):

    required = [
        "week",
        "hospital_id",
        "symptom_id",
    ]

    missing = [
        c for c in required
        if c not in b3.columns
    ]

    if missing:
        raise ValueError(
            f"B3 missing columns: {missing}"
        )

    df = b3.copy()

    # ---------------------------------------------------------------
    # Current baseline elevation
    #
    # This is the most important correction.
    #
    # A symptom that is below its historical baseline should NOT
    # count as a persistent elevated signal.
    # ---------------------------------------------------------------

    if "deviation_percent" in df.columns:

        deviation = pd.to_numeric(
            df["deviation_percent"],
            errors="coerce"
        ).fillna(0)

    else:

        deviation = pd.Series(
            0.0,
            index=df.index
        )

    if "z_score" in df.columns:

        z_score = pd.to_numeric(
            df["z_score"],
            errors="coerce"
        ).fillna(0)

    else:

        z_score = pd.Series(
            0.0,
            index=df.index
        )

    # ---------------------------------------------------------------
    # Baseline elevation requires POSITIVE deviation.
    #
    # This prevents:
    #
    # current < historical mean
    #        ↓
    # false persistence
    # ---------------------------------------------------------------

    df["b3_elevated"] = (
        (deviation > 0)
        &
        (z_score >= 1.0)
    )

    # ---------------------------------------------------------------
    # Keep the original baseline alert as secondary evidence.
    # ---------------------------------------------------------------

    if "baseline_alert" in df.columns:

        df["b3_alert"] = (
            df["baseline_alert"]
            .astype(str)
            .str.upper()
            .isin(
                [
                    "YELLOW",
                    "ORANGE",
                    "RED",
                ]
            )
        )

    else:

        df["b3_alert"] = False

    # ---------------------------------------------------------------
    # Final B3 abnormal signal.
    #
    # Either:
    #   1. genuinely elevated relative to baseline
    # OR
    #   2. baseline alert AND positive deviation
    #
    # The positive deviation requirement is intentional.
    # ---------------------------------------------------------------

    df["b3_abnormal"] = (
        df["b3_elevated"]
        |
        (
            df["b3_alert"]
            &
            (deviation > 0)
        )
    )

    df["b3_z_score"] = z_score

    df["b3_deviation_percent"] = deviation

    return df[
        [
            "week",
            "hospital_id",
            "symptom_id",
            "b3_abnormal",
            "b3_z_score",
            "b3_deviation_percent",
        ]
    ]


# ====================================================================
# B4 — STATISTICAL ANOMALY SIGNAL
# ====================================================================

def prepare_b4_signal(b4):

    required = [
        "week",
        "symptom_id",
    ]

    missing = [
        c for c in required
        if c not in b4.columns
    ]

    if missing:
        raise ValueError(
            f"B4 missing columns: {missing}"
        )

    df = b4.copy()

    # B4 is symptom/week-level, not hospital-level.

    if "anomaly_alert" in df.columns:

        df["b4_abnormal"] = (
            df["anomaly_alert"]
            .astype(str)
            .str.upper()
            .isin(
                [
                    "YELLOW",
                    "ORANGE",
                    "RED",
                ]
            )
        )

    elif "anomaly_signal" in df.columns:

        df["b4_abnormal"] = (
            df["anomaly_signal"]
            .astype(str)
            .str.lower()
            .isin(
                [
                    "true",
                    "1",
                    "yes",
                ]
            )
        )

    elif "potential_outbreak" in df.columns:

        df["b4_abnormal"] = (
            df["potential_outbreak"]
            .astype(str)
            .str.lower()
            .isin(
                [
                    "true",
                    "1",
                    "yes",
                ]
            )
        )

    elif "anomaly_score" in df.columns:

        score = pd.to_numeric(
            df["anomaly_score"],
            errors="coerce"
        ).fillna(0)

        df["b4_abnormal"] = (
            score >= 35
        )

    else:

        df["b4_abnormal"] = False

    return df[
        [
            "week",
            "symptom_id",
            "b4_abnormal",
        ]
    ]


# ====================================================================
# B5 — TEMPORAL SIGNAL
# ====================================================================

def prepare_b5_signal(b5):

    required = [
        "week",
        "symptom_id",
    ]

    missing = [
        c for c in required
        if c not in b5.columns
    ]

    if missing:
        raise ValueError(
            f"B5 missing columns: {missing}"
        )

    df = b5.copy()

    if "temporal_acceleration_signal" in df.columns:

        df["b5_signal"] = (
            df[
                "temporal_acceleration_signal"
            ]
            .astype(str)
            .str.lower()
            .isin(
                [
                    "true",
                    "1",
                    "yes",
                ]
            )
        )

    elif "temporal_alert" in df.columns:

        df["b5_signal"] = (
            df["temporal_alert"]
            .astype(str)
            .str.upper()
            .isin(
                [
                    "YELLOW",
                    "ORANGE",
                    "RED",
                ]
            )
        )

    else:

        df["b5_signal"] = False

    if "temporal_acceleration_score" in df.columns:

        df[
            "temporal_acceleration_score"
        ] = pd.to_numeric(
            df[
                "temporal_acceleration_score"
            ],
            errors="coerce"
        ).fillna(0)

    else:

        df[
            "temporal_acceleration_score"
        ] = 0.0

    return df[
        [
            "week",
            "symptom_id",
            "b5_signal",
            "temporal_acceleration_score",
        ]
    ]


# ====================================================================
# BUILD HOSPITAL STATE
# ====================================================================

def build_hospital_state(
    b2,
    b3,
    b4
):

    state = b2[
        [
            "week",
            "hospital_id",
            "symptom_id",
            "symptom_name",
            "case_count",
        ]
    ].copy()

    # ---------------------------------------------------------------
    # B3
    # ---------------------------------------------------------------

    b3_signal = prepare_b3_signal(
        b3
    )

    state = state.merge(
        b3_signal,
        on=[
            "week",
            "hospital_id",
            "symptom_id",
        ],
        how="left"
    )

    # ---------------------------------------------------------------
    # B4
    #
    # B4 is symptom/week-level.
    # ---------------------------------------------------------------

    b4_signal = prepare_b4_signal(
        b4
    )

    state = state.merge(
        b4_signal,
        on=[
            "week",
            "symptom_id",
        ],
        how="left"
    )

    state["b3_abnormal"] = (
        state["b3_abnormal"]
        .fillna(False)
    )

    state["b4_abnormal"] = (
        state["b4_abnormal"]
        .fillna(False)
    )

    state["b3_z_score"] = (
        state["b3_z_score"]
        .fillna(0)
    )

    state["b3_deviation_percent"] = (
        state["b3_deviation_percent"]
        .fillna(0)
    )

    # ---------------------------------------------------------------
    # Final hospital-level abnormal week.
    #
    # B3 is required to be genuinely elevated.
    # B4 can provide an additional statistical anomaly signal.
    #
    # This avoids declaring persistence simply because the symptom
    # has existed for many weeks.
    # ---------------------------------------------------------------

    state["abnormal_week"] = (
        state["b3_abnormal"]
        |
        state["b4_abnormal"]
    )

    # ---------------------------------------------------------------
    # Current elevation safeguard.
    #
    # If B3 says the hospital is below baseline, a B4 aggregate
    # anomaly can still exist, but we mark this separately so
    # explainability can distinguish the two.
    # ---------------------------------------------------------------

    state["current_baseline_elevated"] = (
        state["b3_deviation_percent"] > 0
    )

    return state


# ====================================================================
# CONSECUTIVE PERSISTENCE
# ====================================================================

def calculate_consecutive_persistence(
    state
):

    df = state.copy()

    df = df.sort_values(
        [
            "hospital_id",
            "symptom_id",
            "week",
        ]
    ).reset_index(drop=True)

    df[
        "consecutive_abnormal_weeks"
    ] = 0

    df[
        "total_abnormal_weeks"
    ] = 0

    # ---------------------------------------------------------------
    # Track consecutive abnormal periods.
    # ---------------------------------------------------------------

    for (
        hospital_id,
        symptom_id
    ), group in df.groupby(
        [
            "hospital_id",
            "symptom_id",
        ],
        sort=False
    ):

        group = group.sort_values(
            "week"
        )

        consecutive = 0
        total = 0

        for index in group.index:

            abnormal = bool(
                df.loc[
                    index,
                    "abnormal_week"
                ]
            )

            if abnormal:

                consecutive += 1
                total += 1

            else:

                consecutive = 0

            df.loc[
                index,
                "consecutive_abnormal_weeks"
            ] = consecutive

            df.loc[
                index,
                "total_abnormal_weeks"
            ] = total

    df[
        "hospital_persistent"
    ] = (
        df[
            "consecutive_abnormal_weeks"
        ]
        >= MIN_PERSISTENT_WEEKS
    )

    return df


# ====================================================================
# CROSS-HOSPITAL PERSISTENCE
# ====================================================================

def calculate_cross_hospital_persistence(
    hospital_state,
    b5
):

    df = hospital_state.copy()

    # ---------------------------------------------------------------
    # Attach B5 symptom/week-level temporal evidence.
    # ---------------------------------------------------------------

    b5_signal = prepare_b5_signal(
        b5
    )

    df = df.merge(
        b5_signal,
        on=[
            "week",
            "symptom_id",
        ],
        how="left"
    )

    df["b5_signal"] = (
        df["b5_signal"]
        .fillna(False)
    )

    df[
        "temporal_acceleration_score"
    ] = (
        df[
            "temporal_acceleration_score"
        ]
        .fillna(0)
    )

    # ---------------------------------------------------------------
    # Aggregate to symptom/week.
    # ---------------------------------------------------------------

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
            current_cases=(
                "case_count",
                "sum"
            ),

            hospitals_observed=(
                "hospital_id",
                "nunique"
            ),

            persistent_hospitals=(
                "hospital_persistent",
                "sum"
            ),

            maximum_consecutive_abnormal_weeks=(
                "consecutive_abnormal_weeks",
                "max"
            ),

            maximum_total_abnormal_weeks=(
                "total_abnormal_weeks",
                "max"
            ),

            average_z_score=(
                "b3_z_score",
                "mean"
            ),

            maximum_z_score=(
                "b3_z_score",
                "max"
            ),

            average_deviation_percent=(
                "b3_deviation_percent",
                "mean"
            ),

            elevated_hospitals=(
                "current_baseline_elevated",
                "sum"
            ),

            b5_signal=(
                "b5_signal",
                "max"
            ),

            temporal_acceleration_score=(
                "temporal_acceleration_score",
                "max"
            ),
        )
    )

    # ---------------------------------------------------------------
    # Cross-hospital persistence.
    # ---------------------------------------------------------------

    result[
        "cross_hospital_persistent"
    ] = (
        result[
            "persistent_hospitals"
        ]
        >= MIN_PERSISTENT_HOSPITALS
    )

    # ---------------------------------------------------------------
    # Track consecutive weeks where multiple hospitals remain
    # persistently abnormal.
    # ---------------------------------------------------------------

    result = result.sort_values(
        [
            "symptom_id",
            "week",
        ]
    ).reset_index(drop=True)

    result[
        "cross_hospital_consecutive_weeks"
    ] = 0

    for symptom_id, group in result.groupby(
        "symptom_id",
        sort=False
    ):

        group = group.sort_values(
            "week"
        )

        consecutive = 0

        for index in group.index:

            persistent = bool(
                result.loc[
                    index,
                    "cross_hospital_persistent"
                ]
            )

            if persistent:

                consecutive += 1

            else:

                consecutive = 0

            result.loc[
                index,
                "cross_hospital_consecutive_weeks"
            ] = consecutive

    return result


# ====================================================================
# PERSISTENCE SCORE
# ====================================================================

def calculate_persistence_score(
    row
):

    # ---------------------------------------------------------------
    # COMPONENT 1 — Duration
    #
    # Maximum 30 points.
    # ---------------------------------------------------------------

    consecutive = row[
        "maximum_consecutive_abnormal_weeks"
    ]

    duration_component = (
        min(
            consecutive / 6.0,
            1.0
        )
        * 30.0
    )

    # ---------------------------------------------------------------
    # COMPONENT 2 — Cross-hospital persistence
    #
    # Maximum 25 points.
    # ---------------------------------------------------------------

    persistent_hospitals = row[
        "persistent_hospitals"
    ]

    hospitals_observed = row[
        "hospitals_observed"
    ]

    if hospitals_observed > 0:

        hospital_proportion = (
            persistent_hospitals
            / hospitals_observed
        )

    else:

        hospital_proportion = 0

    hospital_component = (
        min(
            hospital_proportion,
            1.0
        )
        * 25.0
    )

    # ---------------------------------------------------------------
    # COMPONENT 3 — CURRENT baseline elevation
    #
    # Maximum 25 points.
    #
    # This replaces the previous use of maximum historical z-score.
    # ---------------------------------------------------------------

    average_deviation = row[
        "average_deviation_percent"
    ]

    if pd.isna(
        average_deviation
    ):
        average_deviation = 0

    positive_deviation = max(
        0.0,
        average_deviation
    )

    baseline_component = (
        min(
            positive_deviation / 100.0,
            1.0
        )
        * 25.0
    )

    # ---------------------------------------------------------------
    # COMPONENT 4 — B5 temporal support
    #
    # Maximum 20 points.
    # ---------------------------------------------------------------

    temporal_score = row[
        "temporal_acceleration_score"
    ]

    if pd.isna(
        temporal_score
    ):
        temporal_score = 0

    temporal_component = (
        min(
            max(
                temporal_score,
                0
            ) / 75.0,
            1.0
        )
        * 20.0
    )

    score = (
        duration_component
        + hospital_component
        + baseline_component
        + temporal_component
    )

    # ---------------------------------------------------------------
    # Critical safeguard:
    #
    # If current average deviation is negative AND there is no
    # meaningful current temporal acceleration, the persistence
    # score cannot become an outbreak-level score.
    # ---------------------------------------------------------------

    if (
        average_deviation <= 0
        and temporal_score < 35
    ):

        score = min(
            score,
            30.0
        )

    return round(
        min(
            max(score, 0),
            100
        ),
        2
    )


# ====================================================================
# ALERT CLASSIFICATION
# ====================================================================

def classify_persistence_alert(
    row
):

    score = row[
        "persistence_score"
    ]

    consecutive = row[
        "maximum_consecutive_abnormal_weeks"
    ]

    persistent_hospitals = row[
        "persistent_hospitals"
    ]

    cross_hospital_weeks = row[
        "cross_hospital_consecutive_weeks"
    ]

    average_deviation = row[
        "average_deviation_percent"
    ]

    if pd.isna(
        average_deviation
    ):
        average_deviation = 0

    temporal_score = row[
        "temporal_acceleration_score"
    ]

    if pd.isna(
        temporal_score
    ):
        temporal_score = 0

    # ---------------------------------------------------------------
    # No positive current elevation:
    #
    # Do not issue a persistence outbreak alert unless there is
    # strong current temporal evidence.
    # ---------------------------------------------------------------

    if (
        average_deviation <= 0
        and temporal_score < 35
    ):

        return "GREEN"

    # ---------------------------------------------------------------
    # RED
    # ---------------------------------------------------------------

    if (
        score >= RED_PERSISTENCE_SCORE
        and consecutive >= 4
        and persistent_hospitals >= 3
        and cross_hospital_weeks >= 2
        and average_deviation > 25
    ):

        return "RED"

    # ---------------------------------------------------------------
    # ORANGE
    # ---------------------------------------------------------------

    if (
        score >= ORANGE_PERSISTENCE_SCORE
        and consecutive >= 3
        and average_deviation > 15
        and (
            persistent_hospitals >= 2
            or cross_hospital_weeks >= 2
        )
    ):

        return "ORANGE"

    # ---------------------------------------------------------------
    # YELLOW
    # ---------------------------------------------------------------

    if (
        score >= YELLOW_PERSISTENCE_SCORE
        and consecutive >= MIN_PERSISTENT_WEEKS
        and average_deviation > 0
        and (
            persistent_hospitals >= 1
            or cross_hospital_weeks >= 1
        )
    ):

        return "YELLOW"

    return "GREEN"


# ====================================================================
# MAIN B6 PIPELINE
# ====================================================================

def run_b6():

    print("=" * 80)
    print("B6 - PERSISTENCE DETECTION")
    print("=" * 80)

    # ---------------------------------------------------------------
    # Load inputs
    # ---------------------------------------------------------------

    b2 = load_b2()

    b3 = load_b3()

    b4 = load_b4()

    b5 = load_b5()

    # ---------------------------------------------------------------
    # Hospital-level state
    # ---------------------------------------------------------------

    hospital_state = (
        build_hospital_state(
            b2,
            b3,
            b4
        )
    )

    print(
        f"Hospital-level state rows: "
        f"{len(hospital_state)}"
    )

    # ---------------------------------------------------------------
    # Consecutive persistence
    # ---------------------------------------------------------------

    hospital_state = (
        calculate_consecutive_persistence(
            hospital_state
        )
    )

    # ---------------------------------------------------------------
    # Cross-hospital persistence
    # ---------------------------------------------------------------

    result = (
        calculate_cross_hospital_persistence(
            hospital_state,
            b5
        )
    )

    # ---------------------------------------------------------------
    # Score
    # ---------------------------------------------------------------

    result[
        "persistence_score"
    ] = result.apply(
        calculate_persistence_score,
        axis=1
    )

    # ---------------------------------------------------------------
    # Alert
    # ---------------------------------------------------------------

    result[
        "persistence_alert"
    ] = result.apply(
        classify_persistence_alert,
        axis=1
    )

    result[
        "persistent_outbreak_signal"
    ] = (
        result[
            "persistence_alert"
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
            "persistence_score",
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
        "Persistence alert summary:"
    )

    print(
        result[
            "persistence_alert"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print(
        "Persistent outbreak signals:",
        int(
            result[
                "persistent_outbreak_signal"
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
        "persistence_score",
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
                "hospitals_observed",
                "persistent_hospitals",
                "elevated_hospitals",
                "maximum_consecutive_abnormal_weeks",
                "maximum_total_abnormal_weeks",
                "cross_hospital_consecutive_weeks",
                "average_z_score",
                "maximum_z_score",
                "average_deviation_percent",
                "b5_signal",
                "temporal_acceleration_score",
                "persistence_score",
                "persistence_alert",
                "persistent_outbreak_signal",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print()
    print("=" * 80)
    print("B6 COMPLETE")
    print("=" * 80)

    return result


# ====================================================================
# ENTRY POINT
# ====================================================================

if __name__ == "__main__":

    run_b6()
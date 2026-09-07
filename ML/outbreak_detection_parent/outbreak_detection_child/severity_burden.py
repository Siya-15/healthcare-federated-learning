"""
B9 - SEVERITY BURDEN
====================

Measures whether disease/symptom surveillance is associated
with increasing clinical severity.

B9 focuses on:

    1. Total cases
    2. Severe cases
    3. Severe-case proportion
    4. Severe-case growth
    5. Severe-case acceleration
    6. Hospital-level severe burden
    7. Composite severity burden score

B9 is NOT the final outbreak-risk engine.

B10 will later combine B9 with:

    B3 - Historical baseline
    B4 - Statistical anomaly detection
    B5 - Temporal acceleration
    B6 - Persistence
    B7 - Spatial propagation
    B8 - Objective A integration
    B9 - Severity burden


INPUT:

    PostgreSQL
        patient_encounter

    Existing:
        disease_weekly_surveillance.csv


OUTPUT:

    severity_burden.csv
    severity_burden_latest.csv
    disease_severity_burden.csv
    hospital_severity_burden.csv
"""


from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import text


# ============================================================
# PATHS
# ============================================================

CURRENT_DIR = Path(__file__).resolve().parent


DISEASE_SURVEILLANCE_FILE = (
    CURRENT_DIR / "disease_weekly_surveillance.csv"
)

OUTPUT_FILE = (
    CURRENT_DIR / "severity_burden.csv"
)

LATEST_OUTPUT_FILE = (
    CURRENT_DIR / "severity_burden_latest.csv"
)

DISEASE_OUTPUT_FILE = (
    CURRENT_DIR / "disease_severity_burden.csv"
)

HOSPITAL_OUTPUT_FILE = (
    CURRENT_DIR / "hospital_severity_burden.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

# Existing severity IDs in the project:
#
# SV001 = mild
# SV002 = moderate
# SV003 = severe
#
# We treat SV003 as the severe category.

SEVERE_SEVERITY_IDS = {
    "SV003",
}


# Score thresholds.

YELLOW_THRESHOLD = 35.0
ORANGE_THRESHOLD = 55.0
RED_THRESHOLD = 75.0


# Minimum number of cases before calculating a meaningful
# severe-case proportion.

MIN_CASES_FOR_SEVERITY_RATE = 5


# ============================================================
# DATABASE
# ============================================================

def get_database_engine():

    """
    Import the existing project database engine.

    The project already has database.py at the repository root.
    """

    import sys

    ROOT_DIR = (
        CURRENT_DIR
        / "../.."
        / ".."
    ).resolve()

    ROOT_DIR = ROOT_DIR.resolve()

    if str(ROOT_DIR) not in sys.path:

        sys.path.insert(
            0,
            str(ROOT_DIR),
        )

    from database import get_engine

    return get_engine()


# ============================================================
# HELPERS
# ============================================================

def safe_float(
    value,
    default=0.0,
):

    try:

        if pd.isna(value):

            return default

        return float(value)

    except (
        ValueError,
        TypeError,
    ):

        return default


def clip_score(
    value,
):

    return max(
        0.0,
        min(
            100.0,
            safe_float(value),
        ),
    )


def normalize_growth(
    value,
):

    value = safe_float(
        value
    )

    # Existing project files may store growth either as:
    #
    # 0.25
    #
    # or:
    #
    # 25.0
    #
    if abs(value) <= 5:

        return value * 100.0

    return value


def alert_from_score(
    score,
):

    score = clip_score(
        score
    )

    if score >= RED_THRESHOLD:

        return "RED"

    if score >= ORANGE_THRESHOLD:

        return "ORANGE"

    if score >= YELLOW_THRESHOLD:

        return "YELLOW"

    return "GREEN"


# ============================================================
# LOAD DISEASE SURVEILLANCE
# ============================================================

def load_disease_surveillance():

    if not DISEASE_SURVEILLANCE_FILE.exists():

        raise FileNotFoundError(
            "\nDisease surveillance file not found:\n"
            f"{DISEASE_SURVEILLANCE_FILE}"
        )

    df = pd.read_csv(
        DISEASE_SURVEILLANCE_FILE,
        keep_default_na=False,
    )

    print(
        "Disease surveillance rows:",
        len(df),
    )

    required = [
        "week",
        "hospital_id",
        "disease_id",
        "case_count",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            "\nMissing columns in "
            "disease_weekly_surveillance.csv:\n"
            + ", ".join(missing)
        )

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce",
    )

    df["case_count"] = pd.to_numeric(
        df["case_count"],
        errors="coerce",
    ).fillna(0)

    return df


# ============================================================
# LOAD RAW ENCOUNTER DATA
# ============================================================

def load_encounters():

    engine = get_database_engine()

    query = text(
        """
        SELECT
            encounter_id,
            hospital_id,
            visit_timestamp,
            disease_id,
            severity_id
        FROM patient_encounter
        WHERE disease_id IS NOT NULL
          AND severity_id IS NOT NULL
        ORDER BY visit_timestamp
        """
    )

    with engine.connect() as connection:

        df = pd.read_sql(
            query,
            connection,
        )

    print(
        "Encounter records loaded:",
        len(df),
    )

    if df.empty:

        raise ValueError(
            "No encounter records were loaded."
        )

    df["visit_timestamp"] = pd.to_datetime(
        df["visit_timestamp"],
        errors="coerce",
    )

    df["week"] = (
        df["visit_timestamp"]
        .dt.to_period("W")
        .dt.start_time
    )

    df["is_severe"] = (
        df["severity_id"]
        .astype(str)
        .isin(
            SEVERE_SEVERITY_IDS
        )
        .astype(int)
    )

    return df


# ============================================================
# B9 HOSPITAL × DISEASE × WEEK
# ============================================================

def build_hospital_severity(
    encounters,
):

    """
    Build the fundamental B9 surveillance table:

        week
        hospital
        disease
        total cases
        severe cases
        severe proportion
    """

    grouped = (
        encounters
        .groupby(
            [
                "week",
                "hospital_id",
                "disease_id",
            ],
            as_index=False,
        )
        .agg(
            total_cases=(
                "encounter_id",
                "nunique",
            ),

            severe_cases=(
                "is_severe",
                "sum",
            ),
        )
    )

    # --------------------------------------------------------
    # Severe proportion
    # --------------------------------------------------------

    grouped[
        "severe_case_proportion"
    ] = np.where(

        grouped[
            "total_cases"
        ] > 0,

        grouped[
            "severe_cases"
        ]
        /
        grouped[
            "total_cases"
        ],

        0.0,
    )

    grouped[
        "severe_case_proportion"
    ] = (
        grouped[
            "severe_case_proportion"
        ]
        .clip(
            0,
            1,
        )
    )

    # --------------------------------------------------------
    # Previous week
    # --------------------------------------------------------

    grouped = grouped.sort_values(
        [
            "hospital_id",
            "disease_id",
            "week",
        ]
    )

    grouped[
        "previous_total_cases"
    ] = (
        grouped
        .groupby(
            [
                "hospital_id",
                "disease_id",
            ]
        )[
            "total_cases"
        ]
        .shift(1)
        .fillna(0)
    )

    grouped[
        "previous_severe_cases"
    ] = (
        grouped
        .groupby(
            [
                "hospital_id",
                "disease_id",
            ]
        )[
            "severe_cases"
        ]
        .shift(1)
        .fillna(0)
    )

    grouped[
        "previous_severe_proportion"
    ] = (
        grouped
        .groupby(
            [
                "hospital_id",
                "disease_id",
            ]
        )[
            "severe_case_proportion"
        ]
        .shift(1)
        .fillna(0)
    )

    # --------------------------------------------------------
    # Severe-case growth
    # --------------------------------------------------------

    grouped[
        "severe_case_growth"
    ] = np.where(

        grouped[
            "previous_severe_cases"
        ] > 0,

        (
            grouped[
                "severe_cases"
            ]
            -
            grouped[
                "previous_severe_cases"
            ]
        )
        /
        grouped[
            "previous_severe_cases"
        ],

        np.where(

            grouped[
                "severe_cases"
            ] > 0,

            1.0,

            0.0,
        ),
    )

    # --------------------------------------------------------
    # Severe proportion change
    # --------------------------------------------------------

    grouped[
        "severe_proportion_change"
    ] = (
        grouped[
            "severe_case_proportion"
        ]
        -
        grouped[
            "previous_severe_proportion"
        ]
    )

    # --------------------------------------------------------
    # Severe acceleration
    # --------------------------------------------------------

    grouped[
        "previous_severe_growth"
    ] = (
        grouped
        .groupby(
            [
                "hospital_id",
                "disease_id",
            ]
        )[
            "severe_case_growth"
        ]
        .shift(1)
        .fillna(0)
    )

    grouped[
        "severe_growth_acceleration"
    ] = (
        grouped[
            "severe_case_growth"
        ]
        -
        grouped[
            "previous_severe_growth"
        ]
    )

    return grouped


# ============================================================
# SEVERITY COMPONENT SCORES
# ============================================================

def calculate_burden_score(
    total_cases,
    severe_cases,
    severe_proportion,
    severe_growth,
    severe_acceleration,
    previous_severe_proportion,
):

    """
    Calculate a 0-100 severity burden score.

    Components:

        20% total burden
        35% severe-case proportion
        25% severe-case growth
        20% severe-case acceleration

    This deliberately prioritizes severity over raw volume.
    """

    total_cases = safe_float(
        total_cases
    )

    severe_cases = safe_float(
        severe_cases
    )

    severe_proportion = safe_float(
        severe_proportion
    )

    severe_growth_pct = normalize_growth(
        severe_growth
    )

    acceleration_pct = normalize_growth(
        severe_acceleration
    )

    # --------------------------------------------------------
    # Total case burden
    #
    # Saturates gradually so very common diseases do not
    # automatically become RED.
    # --------------------------------------------------------

    volume_score = min(
        100.0,
        np.log1p(
            max(
                total_cases,
                0,
            )
        )
        /
        np.log1p(
            250
        )
        * 100.0,
    )

    # --------------------------------------------------------
    # Severe proportion
    #
    # 20% severe -> approximately 100.
    # --------------------------------------------------------

    proportion_score = min(
        100.0,
        severe_proportion
        /
        0.20
        * 100.0,
    )

    # --------------------------------------------------------
    # Severe growth
    #
    # 100% growth -> 100.
    # --------------------------------------------------------

    growth_score = min(
        100.0,
        max(
            0.0,
            severe_growth_pct,
        ),
    )

    # --------------------------------------------------------
    # Acceleration
    #
    # 50 percentage-point-equivalent acceleration -> 100.
    # --------------------------------------------------------

    acceleration_score = min(
        100.0,
        max(
            0.0,
            acceleration_pct * 2.0,
        ),
    )

    score = (

        0.20
        * volume_score

        +

        0.35
        * proportion_score

        +

        0.25
        * growth_score

        +

        0.20
        * acceleration_score
    )

    return clip_score(
        score
    )


# ============================================================
# BUILD HOSPITAL SEVERITY BURDEN
# ============================================================

def calculate_hospital_scores(
    df,
):

    result = df.copy()

    result[
        "severity_burden_score"
    ] = result.apply(

        lambda row:
        calculate_burden_score(

            total_cases=row[
                "total_cases"
            ],

            severe_cases=row[
                "severe_cases"
            ],

            severe_proportion=row[
                "severe_case_proportion"
            ],

            severe_growth=row[
                "severe_case_growth"
            ],

            severe_acceleration=row[
                "severe_growth_acceleration"
            ],

            previous_severe_proportion=row[
                "previous_severe_proportion"
            ],
        ),

        axis=1,
    )

    result[
        "severity_alert"
    ] = (
        result[
            "severity_burden_score"
        ]
        .apply(
            alert_from_score
        )
    )

    result[
        "severity_signal"
    ] = (
        result[
            "severity_alert"
        ]
        .isin(
            [
                "YELLOW",
                "ORANGE",
                "RED",
            ]
        )
    )

    return result


# ============================================================
# DISEASE × WEEK AGGREGATION
# ============================================================

def build_disease_severity(
    hospital_df,
    disease_surveillance,
):

    """
    Aggregate severity across hospitals.

    This produces:

        week × disease

    rather than treating every hospital independently.
    """

    grouped = (
        hospital_df
        .groupby(
            [
                "week",
                "disease_id",
            ],
            as_index=False,
        )
        .agg(

            total_cases=(
                "total_cases",
                "sum",
            ),

            severe_cases=(
                "severe_cases",
                "sum",
            ),

            hospitals_observed=(
                "hospital_id",
                "nunique",
            ),

            severe_hospitals=(
                "severe_cases",
                lambda x: int(
                    (
                        x > 0
                    ).sum()
                ),
            ),

            average_severe_proportion=(
                "severe_case_proportion",
                "mean",
            ),

            maximum_severe_proportion=(
                "severe_case_proportion",
                "max",
            ),

            average_severity_score=(
                "severity_burden_score",
                "mean",
            ),

            maximum_severity_score=(
                "severity_burden_score",
                "max",
            ),
        )
    )

    

    

    # --------------------------------------------------------
    # Previous disease-level values
    # --------------------------------------------------------

    grouped = grouped.sort_values(
        [
            "disease_id",
            "week",
        ]
    )

    grouped[
        "previous_severe_cases"
    ] = (
        grouped
        .groupby(
            "disease_id"
        )[
            "severe_cases"
        ]
        .shift(1)
        .fillna(0)
    )

    grouped[
        "previous_total_cases"
    ] = (
        grouped
        .groupby(
            "disease_id"
        )[
            "total_cases"
        ]
        .shift(1)
        .fillna(0)
    )

    grouped[
        "previous_severe_proportion"
    ] = (
        grouped
        .groupby(
            "disease_id"
        )[
            "average_severe_proportion"
        ]
        .shift(1)
        .fillna(0)
    )

    # --------------------------------------------------------
    # Disease-level severe growth
    # --------------------------------------------------------

    grouped[
        "severe_case_growth"
    ] = np.where(

        grouped[
            "previous_severe_cases"
        ] > 0,

        (
            grouped[
                "severe_cases"
            ]
            -
            grouped[
                "previous_severe_cases"
            ]
        )
        /
        grouped[
            "previous_severe_cases"
        ],

        np.where(

            grouped[
                "severe_cases"
            ] > 0,

            1.0,

            0.0,
        ),
    )

    # --------------------------------------------------------
    # Severe proportion change
    # --------------------------------------------------------

    grouped[
        "severe_proportion_change"
    ] = (
        grouped[
            "average_severe_proportion"
        ]
        -
        grouped[
            "previous_severe_proportion"
        ]
    )

    # --------------------------------------------------------
    # Previous growth
    # --------------------------------------------------------

    grouped[
        "previous_severe_growth"
    ] = (
        grouped
        .groupby(
            "disease_id"
        )[
            "severe_case_growth"
        ]
        .shift(1)
        .fillna(0)
    )

    grouped[
        "severe_growth_acceleration"
    ] = (
        grouped[
            "severe_case_growth"
        ]
        -
        grouped[
            "previous_severe_growth"
        ]
    )

    # --------------------------------------------------------
    # Disease-level score
    # --------------------------------------------------------

    grouped[
        "severity_burden_score"
    ] = grouped.apply(

        lambda row:
        calculate_burden_score(

            total_cases=row[
                "total_cases"
            ],

            severe_cases=row[
                "severe_cases"
            ],

            severe_proportion=row[
                "average_severe_proportion"
            ],

            severe_growth=row[
                "severe_case_growth"
            ],

            severe_acceleration=row[
                "severe_growth_acceleration"
            ],

            previous_severe_proportion=row[
                "previous_severe_proportion"
            ],
        ),

        axis=1,
    )

    grouped[
        "severity_alert"
    ] = (
        grouped[
            "severity_burden_score"
        ]
        .apply(
            alert_from_score
        )
    )

    grouped[
        "severity_signal"
    ] = (
        grouped[
            "severity_alert"
        ]
        .isin(
            [
                "YELLOW",
                "ORANGE",
                "RED",
            ]
        )
    )

    return grouped


# ============================================================
# HOSPITAL-LEVEL CURRENT SEVERITY
# ============================================================

def build_hospital_summary(
    hospital_df,
):

    latest_week = (
        hospital_df[
            "week"
        ].max()
    )

    latest = hospital_df[
        hospital_df[
            "week"
        ]
        == latest_week
    ].copy()

    summary = (
        latest
        .groupby(
            "hospital_id",
            as_index=False,
        )
        .agg(

            total_cases=(
                "total_cases",
                "sum",
            ),

            severe_cases=(
                "severe_cases",
                "sum",
            ),

            diseases_observed=(
                "disease_id",
                "nunique",
            ),

            severe_diseases=(
                "severe_cases",
                lambda x: int(
                    (
                        x > 0
                    ).sum()
                ),
            ),

            average_severity_score=(
                "severity_burden_score",
                "mean",
            ),

            maximum_severity_score=(
                "severity_burden_score",
                "max",
            ),
        )
    )

    summary[
        "severe_case_proportion"
    ] = np.where(

        summary[
            "total_cases"
        ] > 0,

        summary[
            "severe_cases"
        ]
        /
        summary[
            "total_cases"
        ],

        0,
    )

    summary[
        "hospital_severity_score"
    ] = summary.apply(

        lambda row:
        calculate_burden_score(

            total_cases=row[
                "total_cases"
            ],

            severe_cases=row[
                "severe_cases"
            ],

            severe_proportion=row[
                "severe_case_proportion"
            ],

            severe_growth=0,

            severe_acceleration=0,

            previous_severe_proportion=0,
        ),

        axis=1,
    )

    summary[
        "hospital_severity_alert"
    ] = (
        summary[
            "hospital_severity_score"
        ]
        .apply(
            alert_from_score
        )
    )

    summary[
        "week"
    ] = latest_week

    return summary


# ============================================================
# EXPLANATION
# ============================================================

def build_explanation(
    row,
):

    parts = []

    total_cases = safe_float(
        row.get(
            "total_cases",
            0,
        )
    )

    severe_cases = safe_float(
        row.get(
            "severe_cases",
            0,
        )
    )

    severe_prop = safe_float(
        row.get(
            "average_severe_proportion",
            row.get(
                "severe_case_proportion",
                0,
            ),
        )
    )

    severe_growth = normalize_growth(
        row.get(
            "severe_case_growth",
            0,
        )
    )

    acceleration = normalize_growth(
        row.get(
            "severe_growth_acceleration",
            0,
        )
    )

    if total_cases > 0:

        parts.append(
            f"{total_cases:.0f} total cases"
        )

    if severe_cases > 0:

        parts.append(
            f"{severe_cases:.0f} severe cases"
        )

    if severe_prop > 0:

        parts.append(
            f"{severe_prop * 100:.1f}% severe-case proportion"
        )

    if abs(severe_growth) >= 5:

        parts.append(
            f"{severe_growth:.1f}% severe-case growth"
        )

    if abs(acceleration) >= 5:

        parts.append(
            f"{acceleration:.1f} percentage-point "
            f"growth acceleration"
        )

    if not parts:

        return (
            "No meaningful severity burden evidence "
            "is currently present."
        )

    score = safe_float(
        row.get(
            "severity_burden_score",
            0,
        )
    )

    alert = str(
        row.get(
            "severity_alert",
            "GREEN",
        )
    )

    explanation = (
        "Current severity burden is based on "
        + ", ".join(parts)
        + f". Composite severity burden score is "
        f"{score:.1f}, producing a {alert} alert."
    )

    return explanation


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("B9 - SEVERITY BURDEN")
    print("=" * 80)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    print()
    print(
        "Loading disease surveillance..."
    )

    disease_surveillance = (
        load_disease_surveillance()
    )

    print()
    print(
        "Loading encounter severity data..."
    )

    encounters = (
        load_encounters()
    )

    # --------------------------------------------------------
    # Build hospital-level surveillance
    # --------------------------------------------------------

    print()
    print(
        "Building hospital × disease × week "
        "severity surveillance..."
    )

    hospital_df = (
        build_hospital_severity(
            encounters
        )
    )

    print(
        "Hospital severity rows:",
        len(hospital_df),
    )

    # --------------------------------------------------------
    # Calculate hospital scores
    # --------------------------------------------------------

    hospital_df = (
        calculate_hospital_scores(
            hospital_df
        )
    )

    # --------------------------------------------------------
    # Disease-level aggregation
    # --------------------------------------------------------

    print()
    print(
        "Building disease-level severity burden..."
    )

    disease_df = (
        build_disease_severity(
            hospital_df,
            disease_surveillance,
        )
    )

    print(
        "Disease severity rows:",
        len(disease_df),
    )

    # --------------------------------------------------------
    # Hospital summary
    # --------------------------------------------------------

    hospital_summary = (
        build_hospital_summary(
            hospital_df
        )
    )

    # --------------------------------------------------------
    # Save detailed hospital surveillance
    # --------------------------------------------------------

    hospital_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Save disease-level surveillance
    # --------------------------------------------------------

    disease_df.to_csv(
        DISEASE_OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Save hospital summary
    # --------------------------------------------------------

    hospital_summary.to_csv(
        HOSPITAL_OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Latest disease-level output
    # --------------------------------------------------------

    latest_week = (
        disease_df[
            "week"
        ].max()
    )

    latest = disease_df[
        disease_df[
            "week"
        ]
        == latest_week
    ].copy()

    latest = latest.sort_values(
        "severity_burden_score",
        ascending=False,
    )

    latest.to_csv(
        LATEST_OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("B9 COMPLETE")
    print("=" * 80)

    print(
        f"Time range: "
        f"{hospital_df['week'].min().date()} "
        f"→ "
        f"{hospital_df['week'].max().date()}"
    )

    print(
        f"Hospital-level rows: "
        f"{len(hospital_df)}"
    )

    print(
        f"Disease-level rows: "
        f"{len(disease_df)}"
    )

    print()

    print(
        "Latest disease severity alerts:"
    )

    print(
        latest[
            "severity_alert"
        ]
        .value_counts()
        .to_string()
    )

    print()

    print(
        "Latest severity signals:",
        int(
            latest[
                "severity_signal"
            ].sum()
        ),
    )

    # --------------------------------------------------------
    # Strongest disease signals
    # --------------------------------------------------------

    print()
    print(
        "Strongest current disease severity signals:"
    )

    display_columns = [

        "disease_id",

        "disease_name",

        "total_cases",

        "severe_cases",

        "average_severe_proportion",

        "severe_case_growth",

        "severe_growth_acceleration",

        "hospitals_observed",

        "severe_hospitals",

        "severity_burden_score",

        "severity_alert",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in latest.columns
    ]

    print(
        latest[
            display_columns
        ]
        .head(15)
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    if not latest.empty:

        print()
        print(
            "Top severity explanation:"
        )

        print(
            build_explanation(
                latest.iloc[0]
            )
        )

    # --------------------------------------------------------
    # Severe case totals
    # --------------------------------------------------------

    latest_total_cases = safe_float(
        latest[
            "total_cases"
        ].sum()
    )

    latest_severe_cases = safe_float(
        latest[
            "severe_cases"
        ].sum()
    )

    latest_severe_rate = (
        latest_severe_cases
        /
        latest_total_cases
        if latest_total_cases > 0
        else 0
    )

    print()
    print(
        f"Latest total cases: "
        f"{latest_total_cases:.0f}"
    )

    print(
        f"Latest severe cases: "
        f"{latest_severe_cases:.0f}"
    )

    print(
        f"Latest severe-case proportion: "
        f"{latest_severe_rate * 100:.2f}%"
    )

    print()

    print(
        f"Main output: "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Latest output: "
        f"{LATEST_OUTPUT_FILE}"
    )

    print(
        f"Disease output: "
        f"{DISEASE_OUTPUT_FILE}"
    )

    print(
        f"Hospital output: "
        f"{HOSPITAL_OUTPUT_FILE}"
    )

    print()
    print("=" * 80)
    print("B9 READY FOR REVIEW")
    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
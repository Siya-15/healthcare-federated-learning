from pathlib import Path

import json
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

ML_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ML_DIR.parent

EMERGING_DIR = (
    ML_DIR
    / "emerging_symptoms"
)

DATA_DIR = ML_DIR


# ============================================================
# KNOWLEDGE TABLES
# ============================================================

KNOWLEDGE_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "knowledge_tables"
)

SYMPTOM_MASTER = (
    KNOWLEDGE_DIR
    / "symptom_master.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_FILE = (
    EMERGING_DIR
    / "continuous_baseline_signals.csv"
)

STATE_FILE = (
    EMERGING_DIR
    / "baseline_state.json"
)

# ============================================================
# CONFIGURATION
# ============================================================

# Historical period used to establish the initial baseline.
BASELINE_WEEKS = 8

# Recent period used to measure current activity.
RECENT_WEEKS = 2

# Minimum observations required before calculating
# a reliable hospital-level baseline.
MIN_BASELINE_DAYS = 14

# Minimum prevalence change considered meaningful.
MODERATE_CHANGE = 0.25
HIGH_CHANGE = 0.50


# ============================================================
# HELPERS
# ============================================================

def normalize_date(series):

    return pd.to_datetime(
        series,
        errors="coerce"
    )


def classify_change(change):

    if pd.isna(change):
        return "INSUFFICIENT_DATA"

    if change >= HIGH_CHANGE:
        return "HIGH_INCREASE"

    if change >= MODERATE_CHANGE:
        return "MODERATE_INCREASE"

    if change <= -MODERATE_CHANGE:
        return "DECREASE"

    return "STABLE"


# ============================================================
# LOAD HOSPITAL DATA
# ============================================================

def load_hospital_data():

    files = sorted(
        DATA_DIR.glob(
            "ml_data_H*.csv"
        )
    )

    if not files:

        raise FileNotFoundError(
            f"No hospital ML files found in:\n{DATA_DIR}"
        )

    frames = []

    for file in files:

        df = pd.read_csv(
            file,
            keep_default_na=False
        )

        required = [
            "encounter_id",
            "hospital_id",
            "visit_timestamp",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:

            raise ValueError(
                f"{file.name} missing columns:\n"
                + "\n".join(missing)
            )

        df["visit_timestamp"] = normalize_date(
            df["visit_timestamp"]
        )

        frames.append(
            df
        )

    combined = pd.concat(
        frames,
        ignore_index=True
    )

    combined = combined.dropna(
        subset=[
            "visit_timestamp"
        ]
    )

    return combined


# ============================================================
# IDENTIFY SYMPTOMS
# ============================================================

# ============================================================
# IDENTIFY CANONICAL SYMPTOMS
# ============================================================

def get_symptom_columns(
    df
):

    if not SYMPTOM_MASTER.exists():

        raise FileNotFoundError(
            f"Symptom master not found:\n"
            f"{SYMPTOM_MASTER}"
        )

    symptom_master = pd.read_csv(
        SYMPTOM_MASTER,
        keep_default_na=False
    )

    if "symptom_name" not in symptom_master.columns:

        raise ValueError(
            "symptom_master.csv is missing "
            "'symptom_name'."
        )

    known_symptoms = (
        symptom_master[
            "symptom_name"
        ]
        .astype(str)
        .str.strip()
        .tolist()
    )

    symptom_columns = [
        symptom
        for symptom in known_symptoms
        if symptom in df.columns
    ]

    if not symptom_columns:

        raise ValueError(
            "No canonical symptom columns "
            "were found in hospital ML data."
        )

    return symptom_columns


# ============================================================
# BUILD DAILY SYMPTOM PREVALENCE
# ============================================================

def build_daily_prevalence(
    df,
    symptom_columns
):

    df = df.copy()

    df["date"] = (
        df["visit_timestamp"]
        .dt.date
    )

    records = []

    for (
        hospital_id,
        date
    ), group in df.groupby(
        [
            "hospital_id",
            "date"
        ]
    ):

        encounter_count = len(
            group
        )

        for symptom in symptom_columns:

            symptom_count = (
                pd.to_numeric(
                    group[symptom],
                    errors="coerce"
                )
                .fillna(0)
                .sum()
            )

            prevalence = (
                symptom_count
                /
                encounter_count
            )

            records.append({

                "hospital_id":
                    hospital_id,

                "date":
                    date,

                "symptom":
                    symptom,

                "encounter_count":
                    encounter_count,

                "symptom_count":
                    int(symptom_count),

                "prevalence":
                    float(prevalence),
            })

    return pd.DataFrame(
        records
    )


# ============================================================
# BUILD BASELINE
# ============================================================

def build_baseline(
    daily
):

    daily["date"] = pd.to_datetime(
        daily["date"]
    )

    latest_date = daily[
        "date"
    ].max()

    baseline_start = (
        latest_date
        -
        pd.Timedelta(
            weeks=BASELINE_WEEKS
        )
    )

    recent_start = (
        latest_date
        -
        pd.Timedelta(
            weeks=RECENT_WEEKS
        )
    )

    baseline_data = daily[
        (
            daily["date"]
            >=
            baseline_start
        )
        &
        (
            daily["date"]
            <
            recent_start
        )
    ].copy()

    recent_data = daily[
        daily["date"]
        >=
        recent_start
    ].copy()

    # --------------------------------------------------------
    # Historical baseline statistics
    # --------------------------------------------------------

    baseline_stats = (
        baseline_data
        .groupby(
            [
                "hospital_id",
                "symptom"
            ]
        )[
            "prevalence"
        ]
        .agg(
            baseline_mean="mean",
            baseline_std="std",
            baseline_min="min",
            baseline_max="max",
            baseline_days="count"
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # Recent activity
    # --------------------------------------------------------

    recent_stats = (
        recent_data
        .groupby(
            [
                "hospital_id",
                "symptom"
            ]
        )[
            "prevalence"
        ]
        .mean()
        .reset_index(
            name="recent_mean"
        )
    )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    result = baseline_stats.merge(
        recent_stats,
        on=[
            "hospital_id",
            "symptom"
        ],
        how="outer"
    )

    result[
        "baseline_std"
    ] = result[
        "baseline_std"
    ].fillna(0)

    result[
        "baseline_days"
    ] = result[
        "baseline_days"
    ].fillna(0)

    # --------------------------------------------------------
    # Change relative to baseline
    # --------------------------------------------------------

    result[
        "absolute_change"
    ] = (
        result[
            "recent_mean"
        ]
        -
        result[
            "baseline_mean"
        ]
    )

    result[
        "relative_change"
    ] = np.where(
        result[
            "baseline_mean"
        ] > 0,

        (
            result[
                "recent_mean"
            ]
            -
            result[
                "baseline_mean"
            ]
        )
        /
        result[
            "baseline_mean"
        ],

        np.nan
    )

    result[
        "change_status"
    ] = result[
        "relative_change"
    ].apply(
        classify_change
    )

    # --------------------------------------------------------
    # Baseline quality
    # --------------------------------------------------------

    result[
        "baseline_quality"
    ] = np.where(
        result[
            "baseline_days"
        ]
        >= MIN_BASELINE_DAYS,

        "ADEQUATE",

        "LIMITED"
    )

    # --------------------------------------------------------
    # Baseline version
    # --------------------------------------------------------

    result[
        "baseline_end_date"
    ] = recent_start - pd.Timedelta(
        days=1
    )

    result[
        "baseline_start_date"
    ] = baseline_start

    result[
        "recent_start_date"
    ] = recent_start

    result[
        "latest_observation_date"
    ] = latest_date

    return result


# ============================================================
# BUILD VERSIONED STATE
# ============================================================

def build_state(
    baseline
):

    latest_date = pd.to_datetime(
        baseline[
            "latest_observation_date"
        ].iloc[0]
    )

    state = {

        "baseline_version":
            f"A8-{latest_date.strftime('%Y%m%d')}",

        "generated_at":
            pd.Timestamp.utcnow()
            .isoformat(),

        "latest_observation_date":
            latest_date.strftime(
                "%Y-%m-%d"
            ),

        "baseline_window_weeks":
            BASELINE_WEEKS,

        "recent_window_weeks":
            RECENT_WEEKS,

        "hospitals":
            sorted(
                baseline[
                    "hospital_id"
                ]
                .dropna()
                .unique()
                .tolist()
            ),

        "symptoms":
            sorted(
                baseline[
                    "symptom"
                ]
                .dropna()
                .unique()
                .tolist()
            ),

        "records":
            int(
                len(baseline)
            ),
    }

    return state


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print(
        "A8 - CONTINUOUS BASELINE & REFINEMENT STATE"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    print(
        "\nLoading hospital ML data..."
    )

    data = load_hospital_data()

    print(
        f"Encounter records: "
        f"{len(data):,}"
    )

    # --------------------------------------------------------
    # Symptoms
    # --------------------------------------------------------

    symptom_columns = get_symptom_columns(
        data
    )

    print(
        f"Symptom features: "
        f"{len(symptom_columns)}"
    )

    # --------------------------------------------------------
    # Daily prevalence
    # --------------------------------------------------------

    print(
        "\nBuilding daily symptom prevalence..."
    )

    daily = build_daily_prevalence(
        data,
        symptom_columns
    )

    print(
        f"Daily prevalence records: "
        f"{len(daily):,}"
    )

    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------

    print(
        "\nBuilding historical baseline..."
    )

    baseline = build_baseline(
        daily
    )

    print(
        f"Baseline records: "
        f"{len(baseline):,}"
    )

    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    state = build_state(
        baseline
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    baseline.to_csv(
        OUTPUT_FILE,
        index=False
    )

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            state,
            file,
            indent=2
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        "\n" + "=" * 80
    )

    print(
        "A8 BASELINE COMPLETE"
    )

    print(
        "=" * 80
    )

    print(
        f"Baseline version : "
        f"{state['baseline_version']}"
    )

    print(
        f"Latest date      : "
        f"{state['latest_observation_date']}"
    )

    print(
        f"Baseline window  : "
        f"{BASELINE_WEEKS} weeks"
    )

    print(
        f"Recent window    : "
        f"{RECENT_WEEKS} weeks"
    )

    print(
        "\nChange status:"
    )

    print(
        baseline[
            "change_status"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nBaseline quality:"
    )

    print(
        baseline[
            "baseline_quality"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nTop increasing symptoms:"
    )

    display_columns = [
        "hospital_id",
        "symptom",
        "baseline_mean",
        "recent_mean",
        "relative_change",
        "change_status",
        "baseline_quality",
    ]

    print(
        baseline.sort_values(
            "relative_change",
            ascending=False
        )[
            display_columns
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    print(
        "\nOutput:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        STATE_FILE
    )


if __name__ == "__main__":
    main()
from pathlib import Path
from datetime import datetime, timezone
import json

import pandas as pd


# ============================================================
# PATHS
# ============================================================

ML_DIR = Path(__file__).resolve().parents[1]
EMERGING_DIR = ML_DIR / "emerging_symptoms"

BASELINE_FILE = (
    EMERGING_DIR
    / "continuous_baseline_signals.csv"
)

STATE_FILE = (
    EMERGING_DIR
    / "baseline_state.json"
)

VERSION_DIR = (
    EMERGING_DIR
    / "baseline_versions"
)

VERSION_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# CONFIGURATION
# ============================================================

BASELINE_WEEKS = 8
RECENT_WEEKS = 2


# ============================================================
# LOAD CURRENT STATE
# ============================================================

def load_current_state():

    if not STATE_FILE.exists():

        raise FileNotFoundError(
            f"Baseline state not found:\n"
            f"{STATE_FILE}"
        )

    with open(
        STATE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# CREATE VERSIONED SNAPSHOT
# ============================================================

def save_version_snapshot(
    baseline,
    previous_state,
    new_version
):

    version_file = (
        VERSION_DIR
        / f"{new_version}.csv"
    )

    baseline.to_csv(
        version_file,
        index=False
    )

    state_file = (
        VERSION_DIR
        / f"{new_version}.json"
    )

    new_state = previous_state.copy()

    new_state.update({

        "baseline_version":
            new_version,

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "previous_version":
            previous_state.get(
                "baseline_version"
            ),

        "record_count":
            int(
                len(baseline)
            ),
    })

    with open(
        state_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            new_state,
            file,
            indent=2
        )

    return (
        version_file,
        state_file
    )


# ============================================================
# UPDATE BASELINE
# ============================================================

def update_baseline(
    new_data
):

    if not isinstance(
        new_data,
        pd.DataFrame
    ):

        raise TypeError(
            "new_data must be a pandas DataFrame."
        )

    required = {
        "hospital_id",
        "visit_timestamp",
    }

    missing = (
        required
        -
        set(new_data.columns)
    )

    if missing:

        raise ValueError(
            "New data is missing:\n"
            + "\n".join(
                sorted(missing)
            )
        )

    new_data = new_data.copy()

    new_data[
        "visit_timestamp"
    ] = pd.to_datetime(
        new_data[
            "visit_timestamp"
        ],
        errors="coerce"
    )

    new_data = new_data.dropna(
        subset=[
            "visit_timestamp"
        ]
    )

    if new_data.empty:

        raise ValueError(
            "No valid timestamped encounters "
            "were found in new_data."
        )

    # --------------------------------------------------------
    # Load current baseline
    # --------------------------------------------------------

    if not BASELINE_FILE.exists():

        raise FileNotFoundError(
            f"Current baseline not found:\n"
            f"{BASELINE_FILE}"
        )

    baseline = pd.read_csv(
        BASELINE_FILE,
        keep_default_na=False
    )

    previous_state = (
        load_current_state()
    )

    # --------------------------------------------------------
    # Determine new observation period
    # --------------------------------------------------------

    latest_new_date = (
        new_data[
            "visit_timestamp"
        ]
        .max()
        .date()
    )

    previous_latest = (
        previous_state[
            "latest_observation_date"
        ]
    )

    print(
        f"Previous latest date: "
        f"{previous_latest}"
    )

    print(
        f"New latest date     : "
        f"{latest_new_date}"
    )

    # --------------------------------------------------------
    # Determine symptom columns from current baseline
    # --------------------------------------------------------

    symptoms = sorted(
        baseline[
            "symptom"
        ]
        .unique()
        .tolist()
    )

    missing_symptoms = [
        symptom
        for symptom in symptoms
        if symptom not in new_data.columns
    ]

    if missing_symptoms:

        raise ValueError(
            "New data is missing canonical "
            "symptom columns:\n"
            +
            "\n".join(
                missing_symptoms
            )
        )

    # --------------------------------------------------------
    # Build daily prevalence for new batch
    # --------------------------------------------------------

    new_data["date"] = (
        new_data[
            "visit_timestamp"
        ].dt.date
    )

    daily_records = []

    for (
        hospital_id,
        date
    ), group in new_data.groupby(
        [
            "hospital_id",
            "date"
        ]
    ):

        encounter_count = len(
            group
        )

        if encounter_count == 0:
            continue

        for symptom in symptoms:

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

            daily_records.append({

                "hospital_id":
                    hospital_id,

                "date":
                    pd.Timestamp(date),

                "symptom":
                    symptom,

                "prevalence":
                    float(prevalence),
            })

    new_daily = pd.DataFrame(
        daily_records
    )

    if new_daily.empty:

        raise ValueError(
            "No daily prevalence records "
            "could be generated."
        )

    # --------------------------------------------------------
    # Update recent mean
    # --------------------------------------------------------

    recent_stats = (
        new_daily
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
            name="new_recent_mean"
        )
    )

    updated = baseline.merge(
        recent_stats,
        on=[
            "hospital_id",
            "symptom"
        ],
        how="left"
    )

    # --------------------------------------------------------
    # Preserve previous baseline while incorporating
    # new observations.
    # --------------------------------------------------------

    updated[
        "new_recent_mean"
    ] = updated[
        "new_recent_mean"
    ].fillna(
        updated[
            "recent_mean"
        ]
    )

    updated[
        "previous_recent_mean"
    ] = updated[
        "recent_mean"
    ]

    updated[
        "recent_mean"
    ] = updated[
        "new_recent_mean"
    ]

    # --------------------------------------------------------
    # Recalculate relative change
    # --------------------------------------------------------

    updated[
        "absolute_change"
    ] = (
        updated[
            "recent_mean"
        ]
        -
        updated[
            "baseline_mean"
        ]
    )

    updated[
        "relative_change"
    ] = (
        updated[
            "absolute_change"
        ]
        /
        updated[
            "baseline_mean"
        ].replace(
            0,
            pd.NA
        )
    )

    # --------------------------------------------------------
    # Change classification
    # --------------------------------------------------------

    def classify_change(
        value
    ):

        if pd.isna(value):
            return "INSUFFICIENT_DATA"

        if value >= 0.50:
            return "HIGH_INCREASE"

        if value >= 0.25:
            return "MODERATE_INCREASE"

        if value <= -0.25:
            return "DECREASE"

        return "STABLE"

    updated[
        "change_status"
    ] = updated[
        "relative_change"
    ].apply(
        classify_change
    )

    # --------------------------------------------------------
    # Version
    # --------------------------------------------------------

    new_version = (
        "A8-"
        +
        latest_new_date.strftime(
            "%Y%m%d"
        )
    )

    updated[
        "baseline_version"
    ] = new_version

    updated[
        "latest_observation_date"
    ] = latest_new_date

    # --------------------------------------------------------
    # Save versioned snapshot
    # --------------------------------------------------------

    version_file, version_state = (
        save_version_snapshot(
            updated,
            previous_state,
            new_version
        )
    )

    # --------------------------------------------------------
    # Update active baseline
    # --------------------------------------------------------

    updated.to_csv(
        BASELINE_FILE,
        index=False
    )

    new_state = previous_state.copy()

    new_state.update({

        "baseline_version":
            new_version,

        "latest_observation_date":
            latest_new_date.strftime(
                "%Y-%m-%d"
            ),

        "previous_version":
            previous_state.get(
                "baseline_version"
            ),

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "record_count":
            int(
                len(updated)
            ),
    })

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            new_state,
            file,
            indent=2
        )

    return (
        updated,
        new_state,
        version_file,
        version_state
    )


# ============================================================
# DEMONSTRATION MODE
# ============================================================

def main():

    print("=" * 80)
    print(
        "A8.1 - VERSIONED BASELINE UPDATE"
    )
    print("=" * 80)

    print(
        "\nCurrent A8 state:"
    )

    state = load_current_state()

    print(
        f"Version      : "
        f"{state['baseline_version']}"
    )

    print(
        f"Latest date  : "
        f"{state['latest_observation_date']}"
    )

    print(
        "\nA8.1 update engine is ready."
    )

    print(
        "\nIt expects a new encounter DataFrame "
        "with the same canonical 27 symptom features."
    )

    print(
        "\nNo production update was performed."
    )


if __name__ == "__main__":
    main()
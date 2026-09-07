"""
A9 - Controlled Emerging-Symptom Validation

Purpose:
    Create a controlled synthetic future validation dataset for
    Objective A without modifying the real ML datasets or database.

Scenarios:

    A - NORMAL
        Existing symptom distributions are preserved.

    B - ATYPICAL KNOWN DISEASE
        A known disease pattern is deliberately increased across
        multiple hospitals and multiple days.

    C - UNEXPLAINED EMERGING PATTERN
        A symptom combination is created that does not correspond
        to an established disease profile.

The generated data is written only to:
    ML/emerging_symptoms/a9_validation/

No production A1-A8 files are modified.
"""

from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ML_DATA_DIR = PROJECT_ROOT / "ML"

VALIDATION_DIR = (
    PROJECT_ROOT
    / "ML"
    / "emerging_symptoms"
    / "a9_validation"
)

OUTPUT_DIR = VALIDATION_DIR / "scenarios"

METADATA_FILE = (
    VALIDATION_DIR
    / "a9_validation_metadata.json"
)


# ============================================================================
# CONFIGURATION
# ============================================================================

RANDOM_STATE = 42

# Current real observation period ends on 2026-08-29.
VALIDATION_START = pd.Timestamp(
    "2026-08-30"
)

VALIDATION_DAYS = 14

# Hospitals deliberately selected to test spread.
SELECTED_HOSPITALS = [
    "H001",
    "H003",
    "H005",
    "H007",
    "H009",
]

# Records generated per hospital per day.
RECORDS_PER_HOSPITAL_PER_DAY = 20


# ============================================================================
# SCENARIOS
# ============================================================================

SCENARIO_NORMAL = "normal"

SCENARIO_ATYPICAL = "atypical_known_disease"

SCENARIO_UNEXPLAINED = "unexplained_emerging_pattern"


# ============================================================================
# ACTIVE SYMPTOMS
# ============================================================================

def load_active_symptoms():

    symptom_master = pd.read_csv(
        PROJECT_ROOT
        / "datasets"
        / "knowledge_tables"
        / "symptom_master.csv",
        keep_default_na=False
    )

    # Load one ML dataset to determine the actual
    # 27 active symptom features.
    sample_file = (
        ML_DATA_DIR
        / "ml_data_H001.csv"
    )

    if not sample_file.exists():

        raise FileNotFoundError(
            f"Missing ML dataset: {sample_file}"
        )

    sample = pd.read_csv(
        sample_file,
        keep_default_na=False
    )

    symptoms = [
        symptom
        for symptom
        in symptom_master["symptom_name"]
        .dropna()
        .tolist()
        if symptom in sample.columns
    ]

    if len(symptoms) != 27:

        raise ValueError(
            f"Expected 27 active symptoms, "
            f"found {len(symptoms)}"
        )

    return symptoms


# ============================================================================
# LOAD SOURCE DATA
# ============================================================================

def load_source_data():

    files = sorted(
        ML_DATA_DIR.glob("ml_data_H*.csv")
    )

    if not files:

        raise FileNotFoundError(
            "No ML hospital datasets found."
        )

    frames = []

    for file in files:

        df = pd.read_csv(
            file,
            keep_default_na=False
        )

        frames.append(df)

    data = pd.concat(
        frames,
        ignore_index=True
    )

    data["visit_timestamp"] = pd.to_datetime(
        data["visit_timestamp"],
        errors="coerce"
    )

    data = data.dropna(
        subset=[
            "hospital_id",
            "visit_timestamp"
        ]
    )

    return data


# ============================================================================
# GENERATE NORMAL FUTURE DATA
# ============================================================================

def generate_normal_scenario(
    source_data,
    symptoms,
    rng
):

    records = []

    # ------------------------------------------------------------------------
    # Use recent observations as the empirical source distribution.
    # ------------------------------------------------------------------------

    latest_date = source_data[
        "visit_timestamp"
    ].max()

    recent_cutoff = (
        latest_date
        - pd.Timedelta(days=14)
    )

    recent = source_data[
        source_data["visit_timestamp"] >= recent_cutoff
    ].copy()

    if recent.empty:

        raise ValueError(
            "No recent source data available."
        )

    for hospital_id in SELECTED_HOSPITALS:

        hospital_data = recent[
            recent["hospital_id"] == hospital_id
        ]

        if hospital_data.empty:
            continue

        for day_offset in range(
            VALIDATION_DAYS
        ):

            date = (
                VALIDATION_START
                + pd.Timedelta(days=day_offset)
            )

            sample = hospital_data.sample(
                n=RECORDS_PER_HOSPITAL_PER_DAY,
                replace=True,
                random_state=(
                    RANDOM_STATE
                    + day_offset
                )
            ).copy()

            sample["visit_timestamp"] = date

            records.append(
                sample
            )

    return pd.concat(
        records,
        ignore_index=True
    )


# ============================================================================
# APPLY ATYPICAL KNOWN-DISEASE PATTERN
# ============================================================================

def apply_atypical_pattern(
    normal_data,
    symptoms,
    rng
):

    data = normal_data.copy()

    target_symptoms = [
        "Fever",
        "Headache",
        "Muscle Pain",
        "Nausea",
        "Rash",
        "Vomiting",
    ]

    missing = [
        symptom
        for symptom in target_symptoms
        if symptom not in symptoms
    ]

    if missing:

        raise ValueError(
            "Atypical pattern symptoms missing: "
            + ", ".join(missing)
        )

    # ------------------------------------------------------------------------
    # Progressive injection:
    #
    # Days 1-3 : 25%
    # Days 4-7 : 40%
    # Days 8-10: 60%
    # Days 11-14: 75%
    #
    # This creates growth + persistence.
    # ------------------------------------------------------------------------

    for day_offset in range(
        VALIDATION_DAYS
    ):

        date = (
            VALIDATION_START
            + pd.Timedelta(days=day_offset)
        )

        mask = (
            data["visit_timestamp"]
            == date
        )

        indices = data.index[mask]

        if len(indices) == 0:
            continue

        if day_offset < 3:
            proportion = 0.25

        elif day_offset < 7:
            proportion = 0.40

        elif day_offset < 10:
            proportion = 0.60

        else:
            proportion = 0.75

        count = max(
            1,
            int(
                len(indices)
                * proportion
            )
        )

        selected = rng.choice(
            indices,
            size=count,
            replace=False
        )

        data.loc[
            selected,
            target_symptoms
        ] = 1

    return data


# ============================================================================
# APPLY UNEXPLAINED EMERGING PATTERN
# ============================================================================

def apply_unexplained_pattern(
    normal_data,
    symptoms,
    rng
):

    data = normal_data.copy()

    # ------------------------------------------------------------------------
    # Deliberately choose a combination that is not simply the known
    # Dengue pattern already used in the A4/A7 pipeline.
    #
    # The goal is to create a representation that should have weaker
    # disease-profile compatibility.
    # ------------------------------------------------------------------------

    target_symptoms = [
        "Breathlessness",
        "Chest Pain",
        "Diarrhoea",
        "Loss of Appetite",
        "Night Sweats",
        "Runny Nose",
    ]

    missing = [
        symptom
        for symptom in target_symptoms
        if symptom not in symptoms
    ]

    if missing:

        raise ValueError(
            "Unexplained pattern symptoms missing: "
            + ", ".join(missing)
        )

    # ------------------------------------------------------------------------
    # Inject progressively over time and across selected hospitals.
    # ------------------------------------------------------------------------

    for day_offset in range(
        VALIDATION_DAYS
    ):

        date = (
            VALIDATION_START
            + pd.Timedelta(days=day_offset)
        )

        mask = (
            data["visit_timestamp"]
            == date
        )

        indices = data.index[mask]

        if len(indices) == 0:
            continue

        if day_offset < 3:
            proportion = 0.15

        elif day_offset < 7:
            proportion = 0.30

        elif day_offset < 10:
            proportion = 0.50

        else:
            proportion = 0.70

        count = max(
            1,
            int(
                len(indices)
                * proportion
            )
        )

        selected = rng.choice(
            indices,
            size=count,
            replace=False
        )

        data.loc[
            selected,
            target_symptoms
        ] = 1

    return data


# ============================================================================
# SAVE SCENARIO
# ============================================================================

def save_scenario(
    data,
    scenario_name
):

    scenario_dir = (
        OUTPUT_DIR
        / scenario_name
    )

    scenario_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    for hospital_id in SELECTED_HOSPITALS:

        hospital_data = data[
            data["hospital_id"] == hospital_id
        ].copy()

        if hospital_data.empty:
            continue

        output_file = (
            scenario_dir
            / f"validation_{hospital_id}.csv"
        )

        hospital_data.to_csv(
            output_file,
            index=False
        )

    combined_file = (
        scenario_dir
        / "combined_validation.csv"
    )

    data.to_csv(
        combined_file,
        index=False
    )

    return scenario_dir


# ============================================================================
# SUMMARY
# ============================================================================

def create_scenario_summary(
    data,
    symptoms,
    scenario_name
):

    rows = []

    for hospital_id in SELECTED_HOSPITALS:

        hospital_data = data[
            data["hospital_id"] == hospital_id
        ]

        for symptom in symptoms:

            prevalence = (
                hospital_data[symptom]
                .astype(float)
                .mean()
            )

            rows.append({
                "scenario": scenario_name,
                "hospital_id": hospital_id,
                "symptom": symptom,
                "records": len(hospital_data),
                "prevalence": prevalence,
            })

    summary = pd.DataFrame(
        rows
    )

    output_file = (
        OUTPUT_DIR
        / scenario_name
        / "symptom_summary.csv"
    )

    summary.to_csv(
        output_file,
        index=False
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)
    print(
        "A9 - CONTROLLED EMERGING-SYMPTOM VALIDATION"
    )
    print("=" * 80)

    # ------------------------------------------------------------------------
    # Clean only the A9 validation workspace.
    # ------------------------------------------------------------------------

    if VALIDATION_DIR.exists():

        shutil.rmtree(
            VALIDATION_DIR
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    rng = np.random.default_rng(
        RANDOM_STATE
    )

    # ------------------------------------------------------------------------
    # Load inputs.
    # ------------------------------------------------------------------------

    print("\nLoading active symptoms...")

    symptoms = load_active_symptoms()

    print(
        f"Active ML symptoms: "
        f"{len(symptoms)}"
    )

    print(
        "  " + ", ".join(symptoms)
    )

    print("\nLoading source data...")

    source_data = load_source_data()

    print(
        f"Source records: "
        f"{len(source_data):,}"
    )

    print(
        f"Source latest date: "
        f"{source_data['visit_timestamp'].max()}"
    )

    # ------------------------------------------------------------------------
    # Generate NORMAL scenario.
    # ------------------------------------------------------------------------

    print("\nGenerating NORMAL scenario...")

    normal = generate_normal_scenario(
        source_data,
        symptoms,
        rng
    )

    normal_dir = save_scenario(
        normal,
        SCENARIO_NORMAL
    )

    create_scenario_summary(
        normal,
        symptoms,
        SCENARIO_NORMAL
    )

    print(
        f"  Records: {len(normal):,}"
    )

    # ------------------------------------------------------------------------
    # Generate ATYPICAL KNOWN DISEASE scenario.
    # ------------------------------------------------------------------------

    print(
        "\nGenerating ATYPICAL KNOWN DISEASE scenario..."
    )

    atypical = apply_atypical_pattern(
        normal,
        symptoms,
        rng
    )

    atypical_dir = save_scenario(
        atypical,
        SCENARIO_ATYPICAL
    )

    create_scenario_summary(
        atypical,
        symptoms,
        SCENARIO_ATYPICAL
    )

    print(
        f"  Records: {len(atypical):,}"
    )

    # ------------------------------------------------------------------------
    # Generate UNEXPLAINED scenario.
    # ------------------------------------------------------------------------

    print(
        "\nGenerating UNEXPLAINED EMERGING PATTERN scenario..."
    )

    unexplained = apply_unexplained_pattern(
        normal,
        symptoms,
        rng
    )

    unexplained_dir = save_scenario(
        unexplained,
        SCENARIO_UNEXPLAINED
    )

    create_scenario_summary(
        unexplained,
        symptoms,
        SCENARIO_UNEXPLAINED
    )

    print(
        f"  Records: {len(unexplained):,}"
    )

    # ------------------------------------------------------------------------
    # Save metadata.
    # ------------------------------------------------------------------------

    metadata = {
        "validation": "A9",
        "random_state": RANDOM_STATE,
        "validation_start": str(
            VALIDATION_START.date()
        ),
        "validation_days": VALIDATION_DAYS,
        "selected_hospitals": SELECTED_HOSPITALS,
        "records_per_hospital_per_day":
            RECORDS_PER_HOSPITAL_PER_DAY,
        "active_ml_symptom_count":
            len(symptoms),
        "active_ml_symptoms": symptoms,
        "scenarios": {
            SCENARIO_NORMAL: {
                "description":
                    "Future data preserving recent empirical distribution."
            },
            SCENARIO_ATYPICAL: {
                "description":
                    "Progressively increasing known Dengue-like symptom pattern.",
                "symptoms": [
                    "Fever",
                    "Headache",
                    "Muscle Pain",
                    "Nausea",
                    "Rash",
                    "Vomiting",
                ],
            },
            SCENARIO_UNEXPLAINED: {
                "description":
                    "Progressively increasing symptom combination "
                    "designed to have weaker established disease compatibility.",
                "symptoms": [
                    "Breathlessness",
                    "Chest Pain",
                    "Diarrhoea",
                    "Loss of Appetite",
                    "Night Sweats",
                    "Runny Nose",
                ],
            },
        },
    }

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2
        )

    # ------------------------------------------------------------------------
    # Final output.
    # ------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "A9 VALIDATION DATASET CREATED"
    )
    print("=" * 80)

    validation_end = (
        VALIDATION_START
        + pd.Timedelta(days=VALIDATION_DAYS - 1)
    )

    print(
        f"\nValidation period: "
        f"{VALIDATION_START.date()} "
        f"→ "
        f"{validation_end.date()}"
    )

    print(
        f"Hospitals: "
        f"{len(SELECTED_HOSPITALS)}"
    )

    print(
        f"Days: "
        f"{VALIDATION_DAYS}"
    )

    print(
        "\nScenarios:"
    )

    print(
        f"  [1] {SCENARIO_NORMAL}"
    )

    print(
        f"  [2] {SCENARIO_ATYPICAL}"
    )

    print(
        f"  [3] {SCENARIO_UNEXPLAINED}"
    )

    print(
        "\nOutput directory:"
    )

    print(
        f"  {VALIDATION_DIR}"
    )

    print(
        "\nNo production A1-A8 files were modified."
    )


if __name__ == "__main__":
    main()
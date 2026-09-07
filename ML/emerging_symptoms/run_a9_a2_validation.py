"""
A9 -> A2 Controlled Validation

Tests Objective A2 against the three controlled A9 scenarios:

    1. normal
    2. atypical_known_disease
    3. unexplained_emerging_pattern

A2 internally runs A1.

The real ML datasets and A1-A8 outputs are never modified.
"""

from pathlib import Path
import os
import shutil
import sys

import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ML_DIR = PROJECT_ROOT / "ML"

A9_DIR = (
    ML_DIR
    / "emerging_symptoms"
    / "a9_validation"
    / "scenarios"
)

TEMP_ROOT = (
    ML_DIR
    / "emerging_symptoms"
    / "a9_a2_temp"
)

REAL_HOSPITALS = [
    "H001",
    "H002",
    "H003",
    "H004",
    "H005",
    "H006",
    "H007",
    "H008",
    "H009",
    "H010",
]

VALIDATION_HOSPITALS = [
    "H001",
    "H003",
    "H005",
    "H007",
    "H009",
]

SCENARIOS = [
    "normal",
    "atypical_known_disease",
    "unexplained_emerging_pattern",
]

BASELINE_END = "2026-07-31"

TARGET_PATTERNS = {
    "normal": [
        "Breathlessness",
        "Chest Pain",
        "Diarrhoea",
        "Loss of Appetite",
        "Night Sweats",
        "Runny Nose",
    ],
    "atypical_known_disease": [
        "Fever",
        "Headache",
        "Muscle Pain",
        "Nausea",
        "Rash",
        "Vomiting",
    ],
    "unexplained_emerging_pattern": [
        "Breathlessness",
        "Chest Pain",
        "Diarrhoea",
        "Loss of Appetite",
        "Night Sweats",
        "Runny Nose",
    ],
}


# ============================================================================
# LOAD A2
# ============================================================================

def load_a2():

    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )

    from ML.emerging_symptoms import (
        emerging_symptom_patterns as a2
    )

    return a2


# ============================================================================
# PREPARE ISOLATED SCENARIO
# ============================================================================

def prepare_temp_scenario(
    scenario
):

    scenario_dir = (
        A9_DIR / scenario
    )

    if not scenario_dir.exists():

        raise FileNotFoundError(
            f"Missing A9 scenario directory: "
            f"{scenario_dir}"
        )

    temp_dir = (
        TEMP_ROOT / scenario
    )

    if temp_dir.exists():

        shutil.rmtree(
            temp_dir
        )

    temp_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # ------------------------------------------------------------------------
    # Copy all real hospital data.
    # ------------------------------------------------------------------------

    for hospital_id in REAL_HOSPITALS:

        source_file = (
            ML_DIR
            / f"ml_data_{hospital_id}.csv"
        )

        if not source_file.exists():

            raise FileNotFoundError(
                f"Missing source dataset: "
                f"{source_file}"
            )

        df = pd.read_csv(
            source_file,
            keep_default_na=False
        )

        # --------------------------------------------------------------------
        # Add the A9 future validation batch where available.
        # --------------------------------------------------------------------

        validation_file = (
            scenario_dir
            / f"validation_{hospital_id}.csv"
        )

        if validation_file.exists():

            future_df = pd.read_csv(
                validation_file,
                keep_default_na=False
            )

            df = pd.concat(
                [
                    df,
                    future_df
                ],
                ignore_index=True
            )

        output_file = (
            temp_dir
            / f"ml_data_{hospital_id}.csv"
        )

        df.to_csv(
            output_file,
            index=False
        )

    return temp_dir



def print_compact_hospital_summary(
    scenario,
    hospital_id,
    result,
):
    """Print only the target-pattern evidence for one hospital."""

    target_symptoms = set(
        TARGET_PATTERNS[scenario]
    )

    target_matches = find_pattern(
        result,
        TARGET_PATTERNS[scenario]
    )

    if target_matches.empty:
        print(
            f"{hospital_id}: "
            f"patterns={len(result)} | "
            f"target=NOT FOUND"
        )
        return

    # Prefer an exact target match; otherwise use the strongest
    # pattern containing all target symptoms.
    exact_matches = target_matches[
        target_matches["symptom_pattern"].apply(
            lambda x: set(
                s.strip() for s in str(x).split(" + ")
            ) == target_symptoms
        )
    ]

    candidates = (
        exact_matches
        if not exact_matches.empty
        else target_matches
    )

    best = candidates.sort_values(
        "emergence_score",
        ascending=False
    ).iloc[0]

    current_occ = int(
        best.get(
            "current_pattern_occurrences",
            0
        )
    )

    anomaly_occ = int(
        best.get(
            "current_anomalous_occurrences",
            0
        )
    )

    growth = float(
        best.get(
            "prevalence_growth",
            0
        )
    )

    persistence = int(
        best.get(
            "persistence_weeks",
            0
        )
    )

    score = float(
        best.get(
            "emergence_score",
            0
        )
    )

    alert = str(
        best.get(
            "alert_level",
            "UNKNOWN"
        )
    )

    pattern_type = str(
        best.get(
            "pattern_type",
            "UNKNOWN"
        )
    )

    print(
        f"{hospital_id}: "
        f"patterns={len(result)} | "
        f"target=FOUND | "
        f"type={pattern_type} | "
        f"occ={current_occ} | "
        f"anomalies={anomaly_occ} | "
        f"growth={growth:.3f} | "
        f"persist={persistence}w | "
        f"score={score:.2f} | "
        f"alert={alert}"
    )


# ============================================================================
# RUN ONE SCENARIO
# ============================================================================

def run_scenario(
    a2,
    scenario
):

    print("\n" + "=" * 80)

    print(
        f"A2 VALIDATION - {scenario.upper()}"
    )

    print("=" * 80)

    temp_dir = prepare_temp_scenario(
        scenario
    )

    # ------------------------------------------------------------------------
    # Redirect A2's data directory.
    # ------------------------------------------------------------------------

    original_a2_ml_dir = a2.ML_DIR
    original_a2_data_dir = a2.DATA_DIR

    a2.ML_DIR = temp_dir
    a2.DATA_DIR = temp_dir

    # ------------------------------------------------------------------------
    # Redirect A1's data directory.
    #
    # A2 imported detect_anomalies directly:
    #
    #     from emerging_symptom_model import detect_anomalies
    #
    # Therefore we need to modify the A1 module's data-loading behaviour.
    # ------------------------------------------------------------------------

    import ML.emerging_symptoms.emerging_symptom_model as a1

    original_a1_load = a1.load_symptom_data

    def temporary_load_symptom_data(
        hospital_id
    ):

        filename = (
            temp_dir
            / f"ml_data_{hospital_id}.csv"
        )

        if not filename.exists():

            raise FileNotFoundError(
                f"Temporary A9 dataset missing: "
                f"{filename}"
            )

        df = pd.read_csv(
            filename,
            keep_default_na=False
        )

        missing = [
            symptom
            for symptom in a1.SYMPTOM_COLUMNS
            if symptom not in df.columns
        ]

        if missing:

            raise ValueError(
                f"{hospital_id}: Missing symptom columns: "
                f"{missing}"
            )

        X = (
            df[a1.SYMPTOM_COLUMNS]
            .fillna(0)
            .astype(float)
            .values
        )

        return df, X

    a1.load_symptom_data = (
        temporary_load_symptom_data
    )

    results = []

    try:

        for hospital_id in VALIDATION_HOSPITALS:

            print(
                f"\nRunning A2 for {hospital_id}..."
            )

            result = (
                a2.analyze_temporal_patterns(
                    hospital_id,
                    baseline_end=BASELINE_END
                )
            )

            if isinstance(result, list):
                result = pd.DataFrame(result)

            if result.empty:

                print(
                    "  No recurring anomalous patterns."
                )

                continue

            results.append(
                result
            )

            # --------------------------------------------------------------
            # Save the COMPLETE result for this hospital.
            # The terminal only prints a compact target summary.
            # --------------------------------------------------------------

            hospital_output_file = (
                TEMP_ROOT
                / f"{scenario}_{hospital_id}_a2_full.csv"
            )

            result.to_csv(
                hospital_output_file,
                index=False
            )

            print_compact_hospital_summary(
                scenario,
                hospital_id,
                result,
            )

    finally:

        # --------------------------------------------------------------------
        # Restore original module state.
        # --------------------------------------------------------------------

        a2.ML_DIR = (
            original_a2_ml_dir
        )

        a2.DATA_DIR = (
            original_a2_data_dir
        )

        a1.load_symptom_data = (
            original_a1_load
        )

    # ------------------------------------------------------------------------
    # Combine hospital results.
    # ------------------------------------------------------------------------

    if results:

        combined = pd.concat(
            results,
            ignore_index=True
        )

    else:

        combined = pd.DataFrame()

    output_file = (
        TEMP_ROOT
        / f"a2_results_{scenario}.csv"
    )

    combined.to_csv(
        output_file,
        index=False
    )

    return combined


# ============================================================================
# FIND TARGET PATTERN
# ============================================================================

def find_pattern(
    results,
    required_symptoms
):

    if results.empty:

        return pd.DataFrame()

    target = set(
        required_symptoms
    )

    matches = []

    for _, row in results.iterrows():

        pattern = str(
            row["symptom_pattern"]
        )

        pattern_symptoms = set(
            symptom.strip()
            for symptom in pattern.split(" + ")
        )

        if target.issubset(
            pattern_symptoms
        ):

            matches.append(
                row
            )

    if not matches:

        return pd.DataFrame()

    return pd.DataFrame(
        matches
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)
    print(
        "A9 -> A2 CONTROLLED VALIDATION"
    )
    print("=" * 80)

    # ------------------------------------------------------------------------
    # Clean only the A9-A2 temporary workspace.
    # ------------------------------------------------------------------------

    if TEMP_ROOT.exists():

        shutil.rmtree(
            TEMP_ROOT
        )

    TEMP_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    a2 = load_a2()

    scenario_results = {}

    # ------------------------------------------------------------------------
    # Run all scenarios.
    # ------------------------------------------------------------------------

    for scenario in SCENARIOS:

        result = run_scenario(
            a2,
            scenario
        )

        scenario_results[
            scenario
        ] = result

    # ------------------------------------------------------------------------
    # Extract target pattern results.
    # ------------------------------------------------------------------------

    summary_rows = []

    for scenario, result in scenario_results.items():

        if result.empty:

            summary_rows.append({
                "scenario": scenario,
                "target_pattern":
                    " + ".join(
                        TARGET_PATTERNS[scenario]
                    ),
                "hospitals_detected": 0,
                "total_anomalous_occurrences": 0,
                "max_emergence_score": 0,
                "max_persistence_weeks": 0,
                "max_alert_level": "NONE",
            })

            continue

        target = TARGET_PATTERNS[scenario]

        matches = find_pattern(
            result,
            target
        )

        if matches.empty:

            summary_rows.append({
                "scenario": scenario,
                "target_pattern":
                    " + ".join(target),
                "hospitals_detected": 0,
                "total_anomalous_occurrences": 0,
                "max_emergence_score": 0,
                "max_persistence_weeks": 0,
                "max_alert_level": "NOT DETECTED",
            })

            continue

        # --------------------------------------------------------------------
        # Alert ordering.
        # --------------------------------------------------------------------

        alert_rank = {
            "LOW": 1,
            "MODERATE": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }

        max_alert = max(
            matches["alert_level"],
            key=lambda x:
            alert_rank.get(
                x,
                0
            )
        )

        summary_rows.append({
            "scenario": scenario,
            "target_pattern":
                " + ".join(target),
            "hospitals_detected":
                matches[
                    "hospital_id"
                ].nunique(),
            "total_anomalous_occurrences":
                int(
                    matches[
                        "current_anomalous_occurrences"
                    ].sum()
                ),
            "max_emergence_score":
                float(
                    matches[
                        "emergence_score"
                    ].max()
                ),
            "max_persistence_weeks":
                int(
                    matches[
                        "persistence_weeks"
                    ].max()
                ),
            "max_alert_level":
                max_alert,
        })

    summary = pd.DataFrame(
        summary_rows
    )

    summary_file = (
        TEMP_ROOT
        / "a2_validation_summary.csv"
    )

    summary.to_csv(
        summary_file,
        index=False
    )

    # ------------------------------------------------------------------------
    # Final summary.
    # ------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "A2 VALIDATION SUMMARY"
    )
    print("=" * 80)

    print(
        summary.to_string(
            index=False
        )
    )

    print("\nOutput:")
    print(
        f"  {TEMP_ROOT}"
    )

    print(
        "\nReal ML datasets and A1-A8 outputs "
        "were not modified."
    )


if __name__ == "__main__":

    main()
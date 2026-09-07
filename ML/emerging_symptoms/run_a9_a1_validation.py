"""
A9 -> A1 Controlled Validation

Runs the existing A1 anomaly detector against three controlled
future scenarios:

    1. normal
    2. atypical_known_disease
    3. unexplained_emerging_pattern

The real ML datasets are NEVER modified.

A temporary working directory is created for each scenario.
"""

from pathlib import Path
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
    / "a9_a1_temp"
)


SCENARIOS = [
    "normal",
    "atypical_known_disease",
    "unexplained_emerging_pattern",
]


HOSPITALS = [
    "H001",
    "H003",
    "H005",
    "H007",
    "H009",
]


# ============================================================================
# LOAD A1
# ============================================================================

def load_a1():

    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )

    from ML.emerging_symptoms.emerging_symptom_model import (
        detect_anomalies
    )

    return detect_anomalies


# ============================================================================
# PREPARE TEMPORARY SCENARIO
# ============================================================================

def prepare_temp_scenario(
    scenario
):

    scenario_dir = (
        A9_DIR / scenario
    )

    if not scenario_dir.exists():

        raise FileNotFoundError(
            f"Missing scenario directory: "
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
    # Copy original historical hospital datasets.
    # ------------------------------------------------------------------------

    for hospital_id in [
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
    ]:

        original = (
            ML_DIR
            / f"ml_data_{hospital_id}.csv"
        )

        if not original.exists():

            raise FileNotFoundError(
                f"Missing source dataset: "
                f"{original}"
            )

        df = pd.read_csv(
            original,
            keep_default_na=False
        )

        # --------------------------------------------------------------------
        # Add the A9 future validation data for selected hospitals.
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


# ============================================================================
# RUN ONE SCENARIO
# ============================================================================

def run_scenario(
    scenario,
    detect_anomalies
):

    print("\n" + "=" * 80)

    print(
        f"A1 VALIDATION - {scenario.upper()}"
    )

    print("=" * 80)

    temp_dir = prepare_temp_scenario(
        scenario
    )

    # ------------------------------------------------------------------------
    # A1 reads ml_data_H*.csv from the current working directory.
    #
    # Temporarily change working directory to the scenario workspace.
    # ------------------------------------------------------------------------

    original_cwd = Path.cwd()

    results = []

    try:

        import os

        os.chdir(
            temp_dir
        )

        for hospital_id in HOSPITALS:

            print(
                f"\nRunning A1 for {hospital_id}..."
            )

            hospital_results, model = (
                detect_anomalies(
                    hospital_id,
                    baseline_end="2026-07-31"
                )
            )

            results.append(
                hospital_results
            )

            anomaly_count = int(
                hospital_results[
                    "is_anomalous"
                ].sum()
            )

            total_count = len(
                hospital_results
            )

            anomaly_rate = (
                anomaly_count / total_count
                if total_count
                else 0
            )

            print(
                f"  Records scored : "
                f"{total_count:,}"
            )

            print(
                f"  Anomalies      : "
                f"{anomaly_count:,}"
            )

            print(
                f"  Anomaly rate   : "
                f"{anomaly_rate * 100:.2f}%"
            )

        combined = pd.concat(
            results,
            ignore_index=True
        )

    finally:

        os.chdir(
            original_cwd
        )

    # ------------------------------------------------------------------------
    # Save results.
    # ------------------------------------------------------------------------

    output_file = (
        TEMP_ROOT
        / f"a1_results_{scenario}.csv"
    )

    combined.to_csv(
        output_file,
        index=False
    )

    return combined


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)
    print(
        "A9 -> A1 CONTROLLED VALIDATION"
    )
    print("=" * 80)

    detect_anomalies = load_a1()

    all_summaries = []

    for scenario in SCENARIOS:

        results = run_scenario(
            scenario,
            detect_anomalies
        )

        anomaly_count = int(
            results["is_anomalous"].sum()
        )

        total_count = len(
            results
        )

        anomaly_rate = (
            anomaly_count / total_count
            if total_count
            else 0
        )

        all_summaries.append({
            "scenario": scenario,
            "records": total_count,
            "anomalies": anomaly_count,
            "anomaly_rate": anomaly_rate,
            "mean_anomaly_score":
                results[
                    "anomaly_score"
                ].mean(),
            "mean_threshold":
                results[
                    "anomaly_threshold"
                ].mean(),
        })

    # ------------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------------

    summary = pd.DataFrame(
        all_summaries
    )

    summary_file = (
        TEMP_ROOT
        / "a1_validation_summary.csv"
    )

    summary.to_csv(
        summary_file,
        index=False
    )

    print("\n" + "=" * 80)
    print(
        "A1 VALIDATION SUMMARY"
    )
    print("=" * 80)

    display_summary = summary.copy()

    display_summary[
        "anomaly_rate"
    ] *= 100

    display_summary[
        "anomaly_rate"
    ] = display_summary[
        "anomaly_rate"
    ].round(2)

    display_summary[
        "mean_anomaly_score"
    ] = display_summary[
        "mean_anomaly_score"
    ].round(6)

    display_summary[
        "mean_threshold"
    ] = display_summary[
        "mean_threshold"
    ].round(6)

    print(
        display_summary.to_string(
            index=False
        )
    )

    print("\nOutput:")
    print(
        f"  {TEMP_ROOT}"
    )

    print(
        "\nReal ML datasets were not modified."
    )


if __name__ == "__main__":
    main()
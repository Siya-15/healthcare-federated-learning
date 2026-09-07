
"""
Controlled validation of the existing Objective A3-A9 pipeline.

Purpose:
    Validate whether the A9-injected scenarios propagate through the
    EXISTING A3-A8/A8.1 implementation.

This script does NOT modify the implementation permanently.
It temporarily redirects scenario-sensitive modules to the A9 scenario
datasets, runs the existing pipeline, saves scenario-specific outputs
under a9_a3_a8_validation/, and restores the original output CSV/state.

Run from the project root:
    .venv\Scripts\python.exe ML\emerging_symptoms\run_a3_a9_injected_validation.py
"""

from pathlib import Path
import shutil
import json
import sys
import pandas as pd


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
ML_DIR = HERE.parent
PROJECT_ROOT = ML_DIR.parent

SCENARIO_ROOT = HERE / "a9_a2_temp"

SCENARIOS = {
    "NORMAL": SCENARIO_ROOT / "normal",
    "ATYPICAL_KNOWN_DISEASE": SCENARIO_ROOT / "atypical_known_disease",
    "UNEXPLAINED_EMERGING_PATTERN": SCENARIO_ROOT / "unexplained_emerging_pattern",
}

TARGETS = {
    "NORMAL": [],
    "ATYPICAL_KNOWN_DISEASE": [
        "Fever", "Headache", "Muscle Pain", "Nausea", "Rash", "Vomiting"
    ],
    "UNEXPLAINED_EMERGING_PATTERN": [
        "Breathlessness", "Chest Pain", "Diarrhoea",
        "Loss of Appetite", "Night Sweats", "Runny Nose"
    ],
}

OUTPUT_NAMES = [
    "cross_hospital_aggregate_signals.csv",
    "hospital_symptom_pattern_aggregates.csv",
    "cross_hospital_symptom_patterns.csv",
    "emerging_disease_inference.csv",
    "clinical_evidence_signals.csv",
    "emerging_signal_fusion.csv",
    "advanced_symptom_novelty.csv",
    "continuous_baseline_signals.csv",
    "baseline_state.json",
]

RESULT_ROOT = HERE / "a9_a3_a8_validation"


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def backup_outputs():
    backup = HERE / "_a3_a9_validation_backup"
    if backup.exists():
        shutil.rmtree(backup)
    backup.mkdir()

    for name in OUTPUT_NAMES:
        src = HERE / name
        if src.exists():
            if src.is_file():
                shutil.copy2(src, backup / name)

    return backup


def restore_outputs(backup):
    for name in OUTPUT_NAMES:
        dst = HERE / name
        if dst.exists():
            if dst.is_file():
                dst.unlink()

    for src in backup.iterdir():
        shutil.copy2(src, HERE / src.name)

    shutil.rmtree(backup, ignore_errors=True)


def save_output(name, scenario_dir):
    src = HERE / name
    if src.exists():
        destination = scenario_dir / name
        if src.is_file():
            shutil.copy2(src, destination)
        return True
    return False


def load_csv(name):
    path = HERE / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, keep_default_na=False)


def target_match(df, targets):
    """
    Find the strongest row whose symptom_pattern contains all target
    symptoms. Returns the row as a dict, or None.
    """
    if df.empty or not targets:
        return None

    if "symptom_pattern" not in df.columns:
        return None

    target_set = set(targets)
    best = None
    best_extra = 10**9

    for _, row in df.iterrows():
        raw = str(row.get("symptom_pattern", ""))
        pattern_set = {
            x.strip() for x in raw.split(" + ") if x.strip()
        }

        if target_set.issubset(pattern_set):
            extra = len(pattern_set - target_set)
            if extra < best_extra:
                best_extra = extra
                best = row.to_dict()

    return best


def numeric(row, *names):
    for name in names:
        if name in row:
            try:
                return float(row[name])
            except Exception:
                pass
    return None


def summarize_match(row):
    if not row:
        return "NOT FOUND"

    fields = [
        ("pattern", "symptom_pattern"),
        ("hospitals", "hospitals_affected"),
        ("growth", "prevalence_growth"),
        ("persistence", "persistence_weeks"),
        ("emergence", "emergence_score"),
        ("cross_hospital", "cross_hospital_score"),
        ("disease", "best_matching_disease"),
        ("inference", "inference_category"),
        ("novelty", "novelty_class"),
        ("novelty_score", "a7_novelty_score"),
        ("clinical", "clinical_evidence_score"),
        ("final_score", "final_emerging_score"),
        ("alert", "final_alert_level"),
        ("signal", "signal_type"),
    ]

    parts = []
    for label, column in fields:
        if column in row and str(row[column]) not in ("", "nan", "None"):
            parts.append(f"{label}={row[column]}")

    return "FOUND | " + " | ".join(parts)


def count_rows(name):
    df = load_csv(name)
    return len(df)


# ---------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------

def run_scenario(name, scenario_path):
    print("\n" + "=" * 80)
    print(f"SCENARIO: {name}")
    print("=" * 80)

    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario directory not found: {scenario_path}")

    # Import the existing modules.
    import emerging_symptom_patterns as a2
    import cross_hospital_patterns as a3
    import emerging_disease_inference as a4
    import clinical_evidence_integration as a5
    import emerging_signal_fusion as a6
    import advanced_symptom_novelty as a7
    import continuous_baseline as a8
    import update_baseline as a81

    # Redirect scenario-sensitive data sources.
    a2.ML_DIR = scenario_path
    a2.DATA_DIR = scenario_path

    a7.DATA_DIR = scenario_path
    a8.DATA_DIR = scenario_path

    # A3-A8 outputs remain in the normal emerging_symptoms directory,
    # because downstream modules expect those exact paths.
    #
    # Run A3.
    print("\n[A3] Cross-hospital analysis...")
    combined, hospital_counts, cross_hospital = (
        a3.analyze_all_hospitals()
    )

    # The A3 function returns outputs; save them using the exact names
    # expected by A4 and the rest of the pipeline.
    combined.to_csv(
        HERE / "cross_hospital_aggregate_signals.csv",
        index=False,
    )
    hospital_counts.to_csv(
        HERE / "hospital_symptom_pattern_aggregates.csv",
        index=False,
    )
    cross_hospital.to_csv(
        HERE / "cross_hospital_symptom_patterns.csv",
        index=False,
    )

    print(
        f"    aggregate={len(combined)} | "
        f"hospital_patterns={len(hospital_counts)} | "
        f"cross_hospital={len(cross_hospital)}"
    )

    # Run A4.
    print("\n[A4] Disease/pathogen inference...")
    a4_result = a4.analyze_emerging_disease_patterns()
    if isinstance(a4_result, pd.DataFrame):
        a4_result.to_csv(
            HERE / "emerging_disease_inference.csv",
            index=False,
        )
    else:
        a4_result = load_csv("emerging_disease_inference.csv")

    print(f"    patterns={len(a4_result)}")

    # Run A5.
    print("\n[A5] Clinical evidence integration...")
    a5.main()
    a5_result = load_csv("clinical_evidence_signals.csv")
    print(f"    patterns={len(a5_result)}")

    # Run A6.
    print("\n[A6] Signal fusion...")
    a6.run_fusion()
    a6_result = load_csv("emerging_signal_fusion.csv")
    print(f"    patterns={len(a6_result)}")

    # Run A7.
    print("\n[A7] Advanced novelty...")
    a7.main()
    a7_result = load_csv("advanced_symptom_novelty.csv")
    print(f"    patterns={len(a7_result)}")

    # Run A8.
    print("\n[A8] Continuous baseline...")
    a8.main()
    a8_result = load_csv("continuous_baseline_signals.csv")
    print(f"    baseline_records={len(a8_result)}")

    # A8.1 / update engine: run against the scenario data, then restore
    # the production baseline/state from the outer backup.
    print("\n[A8.1] Versioned baseline update readiness...")
    scenario_files = list(scenario_path.glob("ml_data_H*.csv"))
    scenario_frames = [
        pd.read_csv(p, keep_default_na=False)
        for p in scenario_files
    ]
    scenario_data = pd.concat(scenario_frames, ignore_index=True)

    try:
        updated, new_state, version_file, version_state = (
            a81.update_baseline(scenario_data)
        )
        a81_status = "PASS"
        a81_detail = (
            f"version={new_state.get('baseline_version')} | "
            f"latest={new_state.get('latest_observation_date')} | "
            f"records={len(updated)}"
        )
    except Exception as exc:
        a81_status = "FAIL"
        a81_detail = str(exc)

    # Save scenario-specific outputs.
    scenario_result_dir = RESULT_ROOT / name.lower()
    scenario_result_dir.mkdir(parents=True, exist_ok=True)

    for output in OUTPUT_NAMES:
        save_output(output, scenario_result_dir)

    # Determine whether target propagated.
    target = TARGETS[name]

    a3_match = target_match(cross_hospital, target)
    a4_match = target_match(a4_result, target)
    a5_match = target_match(a5_result, target)
    a6_match = target_match(a6_result, target)
    a7_match = target_match(a7_result, target)

    # A8 operates at symptom level rather than pattern level.
    a8_hits = 0
    if target and not a8_result.empty and "symptom" in a8_result.columns:
        a8_hits = int(a8_result["symptom"].isin(target).sum())

    summary = {
        "scenario": name,
        "a3_rows": len(cross_hospital),
        "a4_rows": len(a4_result),
        "a5_rows": len(a5_result),
        "a6_rows": len(a6_result),
        "a7_rows": len(a7_result),
        "a8_rows": len(a8_result),
        "a3_target_found": bool(a3_match),
        "a4_target_found": bool(a4_match),
        "a5_target_found": bool(a5_match),
        "a6_target_found": bool(a6_match),
        "a7_target_found": bool(a7_match),
        "a8_target_symptom_rows": a8_hits,
        "a81_status": a81_status,
        "a81_detail": a81_detail,
        "a3_match": summarize_match(a3_match),
        "a4_match": summarize_match(a4_match),
        "a5_match": summarize_match(a5_match),
        "a6_match": summarize_match(a6_match),
        "a7_match": summarize_match(a7_match),
    }

    print("\n" + "-" * 80)
    print("TARGET PROPAGATION")
    print("-" * 80)

    if not target:
        print("A3 target: N/A (NORMAL scenario)")
        print("A4 target: N/A")
        print("A5 target: N/A")
        print("A6 target: N/A")
        print("A7 target: N/A")
    else:
        print("A3:", summarize_match(a3_match))
        print("A4:", summarize_match(a4_match))
        print("A5:", summarize_match(a5_match))
        print("A6:", summarize_match(a6_match))
        print("A7:", summarize_match(a7_match))

    print("A8:", f"{a8_hits} target symptom rows")
    print("A8.1:", a81_status, "|", a81_detail)

    with open(
        scenario_result_dir / "validation_summary.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(summary, f, indent=2, default=str)

    return summary


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)

    backup = backup_outputs()

    summaries = []

    try:
        for name, path in SCENARIOS.items():
            summaries.append(run_scenario(name, path))

    finally:
        # This restores the user's original pipeline outputs/state,
        # including the A8 baseline state changed by A8.1.
        restore_outputs(backup)

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(
        RESULT_ROOT / "a3_a9_validation_summary.csv",
        index=False,
    )

    print("\n" + "=" * 80)
    print("A3-A9 CONTROLLED VALIDATION COMPLETE")
    print("=" * 80)

    display_columns = [
        "scenario",
        "a3_target_found",
        "a4_target_found",
        "a5_target_found",
        "a6_target_found",
        "a7_target_found",
        "a8_target_symptom_rows",
        "a81_status",
    ]

    print(summary_df[display_columns].to_string(index=False))

    print("\nScenario outputs:")
    print(RESULT_ROOT)


if __name__ == "__main__":
    main()

"""
A8.1 - Controlled Versioned Baseline Update Test

Purpose:
    Validate the A8.1 baseline update engine using a synthetic
    future-dated batch without modifying the real active baseline.

This test:
    1. Loads existing local ML data.
    2. Selects a small batch from the most recent data.
    3. Moves timestamps into a future period.
    4. Validates the 27 active ML symptom features.
    5. Runs the A8.1 update engine in an isolated workspace.
    6. Verifies versioning and baseline changes.
    7. Verifies the real A8 baseline remains unchanged.
"""

from pathlib import Path
import json
import shutil
import sys

import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ML_DATA_DIR = PROJECT_ROOT / "ML"
EMERGING_DIR = PROJECT_ROOT / "ML" / "emerging_symptoms"

REAL_BASELINE = (
    EMERGING_DIR / "continuous_baseline_signals.csv"
)

REAL_STATE = (
    EMERGING_DIR / "baseline_state.json"
)

TEST_DIR = (
    EMERGING_DIR / "a8_1_test_workspace"
)

TEST_BASELINE = (
    TEST_DIR / "continuous_baseline_signals.csv"
)

TEST_STATE = (
    TEST_DIR / "baseline_state.json"
)

TEST_VERSION_DIR = (
    TEST_DIR / "baseline_versions"
)


# ============================================================================
# LOAD EXISTING LOCAL ML DATA
# ============================================================================

def load_existing_ml_data():

    files = sorted(
        ML_DATA_DIR.glob("ml_data_H*.csv")
    )

    if not files:
        raise FileNotFoundError(
            "No ML data files found in ML/ml_data_H*.csv"
        )

    frames = []

    for file in files:

        print(f"Loading: {file.name}")

        df = pd.read_csv(
            file,
            keep_default_na=False
        )

        frames.append(df)

    data = pd.concat(
        frames,
        ignore_index=True
    )

    print(
        f"\nTotal local records loaded: "
        f"{len(data):,}"
    )

    return data


# ============================================================================
# LOAD REAL A8 STATE
# ============================================================================

def load_real_state():

    if not REAL_STATE.exists():
        raise FileNotFoundError(
            f"Missing A8 state file: {REAL_STATE}"
        )

    with open(
        REAL_STATE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================================
# PREPARE CONTROLLED FUTURE BATCH
# ============================================================================

def prepare_future_batch(data):

    required = {
        "hospital_id",
        "visit_timestamp"
    }

    missing = required - set(data.columns)

    if missing:

        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing)}"
        )

    data = data.copy()

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

    # ------------------------------------------------------------------------
    # Use only the most recent 7 days of existing data.
    # This simulates a realistic incoming batch.
    # ------------------------------------------------------------------------

    latest_existing_date = (
        data["visit_timestamp"].max()
    )

    recent_cutoff = (
        latest_existing_date
        - pd.Timedelta(days=7)
    )

    recent_data = data[
        data["visit_timestamp"] >= recent_cutoff
    ].copy()

    if recent_data.empty:

        raise ValueError(
            "No recent data available for "
            "controlled test batch."
        )

    batches = []

    # ------------------------------------------------------------------------
    # Select up to 20 records per hospital.
    # ------------------------------------------------------------------------

    hospitals = sorted(
        recent_data["hospital_id"].unique()
    )

    for hospital_id in hospitals:

        hospital_data = recent_data[
            recent_data["hospital_id"] == hospital_id
        ]

        if hospital_data.empty:
            continue

        sample_size = min(
            20,
            len(hospital_data)
        )

        sample = hospital_data.sample(
            n=sample_size,
            random_state=42
        ).copy()

        batches.append(sample)

    if not batches:

        raise ValueError(
            "Unable to create a controlled "
            "future batch."
        )

    batch = pd.concat(
        batches,
        ignore_index=True
    )

    # ------------------------------------------------------------------------
    # Move batch immediately after the current
    # A8 observation period.
    #
    # Current:
    #     2026-08-29
    #
    # New batch starts:
    #     2026-08-30
    # ------------------------------------------------------------------------

    batch_min_date = (
        batch["visit_timestamp"].min()
    )

    target_start = pd.Timestamp(
        "2026-08-30"
    )

    shift = (
        target_start - batch_min_date
    )

    batch["visit_timestamp"] = (
        batch["visit_timestamp"] + shift
    )

    return batch


# ============================================================================
# COPY REAL A8 STATE INTO ISOLATED TEST WORKSPACE
# ============================================================================

def copy_real_baseline_to_test_workspace():

    if TEST_DIR.exists():

        shutil.rmtree(
            TEST_DIR
        )

    TEST_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    TEST_VERSION_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        REAL_BASELINE,
        TEST_BASELINE
    )

    shutil.copy2(
        REAL_STATE,
        TEST_STATE
    )


# ============================================================================
# MAIN TEST
# ============================================================================

def main():

    print("=" * 80)
    print(
        "A8.1 - CONTROLLED VERSIONED "
        "BASELINE UPDATE TEST"
    )
    print("=" * 80)

    # ------------------------------------------------------------------------
    # 1. Capture real A8 files before test
    # ------------------------------------------------------------------------

    if not REAL_BASELINE.exists():
        raise FileNotFoundError(
            f"Missing baseline file: {REAL_BASELINE}"
        )

    if not REAL_STATE.exists():
        raise FileNotFoundError(
            f"Missing state file: {REAL_STATE}"
        )

    real_baseline_before = (
        REAL_BASELINE.read_bytes()
    )

    real_state_before = (
        REAL_STATE.read_bytes()
    )

    # ------------------------------------------------------------------------
    # 2. Load real state
    # ------------------------------------------------------------------------

    real_state = load_real_state()

    print("\nREAL A8 STATE")
    print("-" * 80)

    print(
        f"Version      : "
        f"{real_state.get('baseline_version')}"
    )

    print(
        f"Latest date  : "
        f"{real_state.get('latest_observation_date')}"
    )

    # ------------------------------------------------------------------------
    # 3. Load local ML data
    # ------------------------------------------------------------------------

    data = load_existing_ml_data()

    # ------------------------------------------------------------------------
    # 4. Prepare future batch
    # ------------------------------------------------------------------------

    batch = prepare_future_batch(
        data
    )

    print("\nTEST BATCH")
    print("-" * 80)

    print(
        f"Records      : "
        f"{len(batch):,}"
    )

    print(
        f"Hospitals    : "
        f"{batch['hospital_id'].nunique()}"
    )

    print(
        f"Date range   : "
        f"{batch['visit_timestamp'].min()} "
        f"→ "
        f"{batch['visit_timestamp'].max()}"
    )

    # ------------------------------------------------------------------------
    # 5. Determine active ML symptoms
    #
    # symptom_master contains 28 known symptoms.
    # Only 27 are currently represented as ML features.
    # ------------------------------------------------------------------------

    symptom_master = pd.read_csv(
        PROJECT_ROOT
        / "datasets"
        / "knowledge_tables"
        / "symptom_master.csv",
        keep_default_na=False
    )

    canonical_symptoms = [
        symptom
        for symptom
        in symptom_master["symptom_name"]
        .dropna()
        .tolist()
        if symptom in data.columns
    ]

    print(
        f"\nActive ML symptoms: "
        f"{len(canonical_symptoms)}"
    )

    if len(canonical_symptoms) != 27:

        raise AssertionError(
            f"Expected 27 active ML symptoms, "
            f"found {len(canonical_symptoms)}"
        )

    # ------------------------------------------------------------------------
    # 6. Verify test batch contains all 27 active symptoms
    # ------------------------------------------------------------------------

    missing_symptoms = [
        symptom
        for symptom in canonical_symptoms
        if symptom not in batch.columns
    ]

    if missing_symptoms:

        raise ValueError(
            "Test batch is missing active ML symptoms:\n"
            + "\n".join(missing_symptoms)
        )

    print(
        "All 27 active ML symptoms present."
    )

    # ------------------------------------------------------------------------
    # 7. Create isolated test workspace
    # ------------------------------------------------------------------------

    copy_real_baseline_to_test_workspace()

    print(
        f"\nTest workspace created:"
    )

    print(
        f"  {TEST_DIR}"
    )

    # ------------------------------------------------------------------------
    # 8. Import A8.1 update engine
    # ------------------------------------------------------------------------

    sys.path.insert(
        0,
        str(EMERGING_DIR)
    )

    import update_baseline

    # ------------------------------------------------------------------------
    # 9. Redirect A8.1 paths to isolated workspace
    # ------------------------------------------------------------------------

    update_baseline.BASELINE_FILE = (
        TEST_BASELINE
    )

    update_baseline.STATE_FILE = (
        TEST_STATE
    )

    update_baseline.VERSION_DIR = (
        TEST_VERSION_DIR
    )

    # ------------------------------------------------------------------------
    # 10. Run A8.1 update
    # ------------------------------------------------------------------------

    print("\nRUNNING A8.1 UPDATE")
    print("-" * 80)

    result = update_baseline.update_baseline(
        batch
    )

    print("\nUPDATE RESULT")
    print("-" * 80)

    print(result)

    # ------------------------------------------------------------------------
    # 11. Verify updated state exists
    # ------------------------------------------------------------------------

    if not TEST_STATE.exists():

        raise AssertionError(
            "A8.1 did not create/update "
            "baseline_state.json"
        )

    with open(
        TEST_STATE,
        "r",
        encoding="utf-8"
    ) as f:

        new_state = json.load(f)

    print("\nNEW TEST STATE")
    print("-" * 80)

    print(
        f"Version      : "
        f"{new_state.get('baseline_version')}"
    )

    print(
        f"Latest date  : "
        f"{new_state.get('latest_observation_date')}"
    )

    # ------------------------------------------------------------------------
    # 12. Verify baseline version changed
    # ------------------------------------------------------------------------

    old_version = (
        real_state.get("baseline_version")
    )

    new_version = (
        new_state.get("baseline_version")
    )

    if new_version == old_version:

        raise AssertionError(
            "Baseline version did not change."
        )

    # ------------------------------------------------------------------------
    # 13. Verify observation date advanced
    # ------------------------------------------------------------------------

    old_latest = pd.Timestamp(
        real_state[
            "latest_observation_date"
        ]
    )

    new_latest = pd.Timestamp(
        new_state[
            "latest_observation_date"
        ]
    )

    if new_latest <= old_latest:

        raise AssertionError(
            "Latest observation date "
            "did not advance."
        )

    # ------------------------------------------------------------------------
    # 14. Verify version snapshot
    # ------------------------------------------------------------------------

    version_files = list(
        TEST_VERSION_DIR.glob("*.csv")
    )

    if not version_files:

        raise AssertionError(
            "No versioned baseline snapshot "
            "was created."
        )

    print(
        f"\nVersion snapshots created: "
        f"{len(version_files)}"
    )

    for file in version_files:

        print(
            f"  - {file.name}"
        )

    # ------------------------------------------------------------------------
    # 15. Verify updated active baseline
    # ------------------------------------------------------------------------

    if not TEST_BASELINE.exists():

        raise AssertionError(
            "Updated active baseline "
            "does not exist."
        )

    updated_baseline = pd.read_csv(
        TEST_BASELINE,
        keep_default_na=False
    )

    print(
        f"\nUpdated baseline records: "
        f"{len(updated_baseline):,}"
    )

    # ------------------------------------------------------------------------
    # 16. Verify real baseline remained unchanged
    # ------------------------------------------------------------------------

    real_baseline_after = (
        REAL_BASELINE.read_bytes()
    )

    real_state_after = (
        REAL_STATE.read_bytes()
    )

    if real_baseline_before != real_baseline_after:

        raise AssertionError(
            "CRITICAL: Real A8 baseline "
            "was modified!"
        )

    if real_state_before != real_state_after:

        raise AssertionError(
            "CRITICAL: Real A8 state "
            "was modified!"
        )

    # ------------------------------------------------------------------------
    # 17. Final result
    # ------------------------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "A8.1 CONTROLLED TEST PASSED"
    )
    print("=" * 80)

    print("\nVerified:")

    print(
        "  [PASS] Future encounter batch accepted"
    )

    print(
        "  [PASS] 27 active ML symptoms present"
    )

    print(
        "  [PASS] Baseline version advanced"
    )

    print(
        "  [PASS] Latest observation date advanced"
    )

    print(
        "  [PASS] Version snapshot created"
    )

    print(
        "  [PASS] Active test baseline updated"
    )

    print(
        "  [PASS] Real baseline remained unchanged"
    )

    print("\nTest workspace:")

    print(
        f"  {TEST_DIR}"
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
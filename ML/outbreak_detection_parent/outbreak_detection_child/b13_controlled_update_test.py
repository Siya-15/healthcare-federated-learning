"""
B13 - Controlled Continuous Update Test

Purpose
-------
Validates that a new clinical encounter entering PostgreSQL
is detected by B13 and causes the complete surveillance
pipeline to refresh.

The test record is temporary and is removed after validation.

Test flow:

    Baseline database
          ↓
    Insert temporary encounter
          ↓
    B13 detects +1 record
          ↓
    B1 → B12 execute
          ↓
    Capture validation evidence
          ↓
    Remove temporary encounter
          ↓
    Restore normal surveillance outputs
"""

from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import sys
import os
import shutil

import pandas as pd
from sqlalchemy import text


# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = (
    Path(__file__).resolve().parents[3]
)

B13_SCRIPT = (
    BASE_DIR / "continuous_update_pipeline.py"
)

TEST_OUTPUT = (
    BASE_DIR / "b13_controlled_test_result.csv"
)

BACKUP_DIR = (
    BASE_DIR / "b13_test_backup"
)


# ============================================================================
# TEST IDENTIFIERS
# ============================================================================

TEST_ENCOUNTER_ID = "B13TEST-09060001"

TEST_PATIENT_ID = "B13PAT-09060001"

TEST_HOSPITAL_ID = "H001"

TEST_DISEASE_ID = "D006"

TEST_SEVERITY_ID = "SV002"

TEST_SYMPTOM_ID = "S011"


# ============================================================================
# DATABASE
# ============================================================================

def get_database_engine():

    project_root = (
        Path(__file__).resolve()
        .parents[3]
    )

    project_root_str = str(
        project_root
    )

    if project_root_str not in sys.path:

        sys.path.insert(
            0,
            project_root_str
        )

    from database import get_engine

    return get_engine()


# ============================================================================
# DATABASE STATE
# ============================================================================

def get_database_state():

    engine = get_database_engine()

    query = text(
        """
        SELECT
            COUNT(*) AS total_encounters,
            MIN(visit_timestamp) AS earliest_encounter,
            MAX(visit_timestamp) AS latest_encounter
        FROM patient_encounter
        """
    )

    with engine.connect() as connection:

        row = connection.execute(
            query
        ).fetchone()

    return {
        "total_encounters":
            int(row.total_encounters),

        "earliest_encounter":
            row.earliest_encounter,

        "latest_encounter":
            row.latest_encounter,
    }


# ============================================================================
# CHECK EXISTING TEST RECORD
# ============================================================================

def remove_existing_test_record():

    """
    Ensures a previous interrupted test does not leave
    the temporary encounter behind.
    """

    engine = get_database_engine()

    with engine.begin() as connection:

        connection.execute(
            text(
                """
                DELETE FROM encounter_symptoms
                WHERE encounter_id = :encounter_id
                """
            ),
            {
                "encounter_id":
                    TEST_ENCOUNTER_ID
            }
        )

        connection.execute(
            text(
                """
                DELETE FROM encounter_treatments
                WHERE encounter_id = :encounter_id
                """
            ),
            {
                "encounter_id":
                    TEST_ENCOUNTER_ID
            }
        )

        connection.execute(
            text(
                """
                DELETE FROM encounter_complications
                WHERE encounter_id = :encounter_id
                """
            ),
            {
                "encounter_id":
                    TEST_ENCOUNTER_ID
            }
        )

        connection.execute(
            text(
                """
                DELETE FROM patient_encounter
                WHERE encounter_id = :encounter_id
                """
            ),
            {
                "encounter_id":
                    TEST_ENCOUNTER_ID
            }
        )


# ============================================================================
# INSERT TEMPORARY ENCOUNTER
# ============================================================================

def insert_test_encounter():

    """
    Insert one valid temporary clinical encounter and
    one associated symptom.

    The record is intentionally placed in the latest
    surveillance week so B1/B2 can observe it.
    """

    engine = get_database_engine()

    # Use a timestamp inside the latest existing surveillance week.
    test_timestamp = (
        datetime(2026, 8, 29, 12, 0, 0)
    )

    with engine.begin() as connection:

        # --------------------------------------------------------------
        # Parent encounter
        # --------------------------------------------------------------

        connection.execute(
            text(
                """
                INSERT INTO patient_encounter (
                    encounter_id,
                    patient_id,
                    hospital_id,
                    parent_encounter_id,
                    visit_timestamp,
                    age,
                    gender,
                    occupation,
                    district,
                    state,
                    temperature,
                    heart_rate,
                    respiratory_rate,
                    systolic_bp,
                    diastolic_bp,
                    spo2,
                    disease_id,
                    severity_id,
                    admission_status,
                    visit_type,
                    symptom_onset_days,
                    travel_history,
                    vaccination_status,
                    discharge_status,
                    recovery_days,
                    treatment_duration_days,
                    readmitted_within_30_days,
                    follow_up_status,
                    complication_count,
                    admission_required,
                    referral_required
                )
                VALUES (
                    :encounter_id,
                    :patient_id,
                    :hospital_id,
                    :parent_encounter_id,
                    :visit_timestamp,
                    :age,
                    :gender,
                    :occupation,
                    :district,
                    :state,
                    :temperature,
                    :heart_rate,
                    :respiratory_rate,
                    :systolic_bp,
                    :diastolic_bp,
                    :spo2,
                    :disease_id,
                    :severity_id,
                    :admission_status,
                    :visit_type,
                    :symptom_onset_days,
                    :travel_history,
                    :vaccination_status,
                    :discharge_status,
                    :recovery_days,
                    :treatment_duration_days,
                    :readmitted_within_30_days,
                    :follow_up_status,
                    :complication_count,
                    :admission_required,
                    :referral_required
                )
                """
            ),
            {
                "encounter_id":
                    TEST_ENCOUNTER_ID,

                "patient_id":
                    TEST_PATIENT_ID,

                "hospital_id":
                    TEST_HOSPITAL_ID,

                "parent_encounter_id":
                    None,

                "visit_timestamp":
                    test_timestamp,

                "age":
                    42,

                "gender":
                    "Male",

                "occupation":
                    "Teacher",

                "district":
                    "D001",

                "state":
                    "S001",

                "temperature":
                    38.5,

                "heart_rate":
                    98,

                "respiratory_rate":
                    22,

                "systolic_bp":
                    110,

                "diastolic_bp":
                    70,

                "spo2":
                    96,

                "disease_id":
                    TEST_DISEASE_ID,

                "severity_id":
                    TEST_SEVERITY_ID,

                "admission_status":
                    "OPD",

                "visit_type":
                    "New",

                "symptom_onset_days":
                    3,

                "travel_history":
                    False,

                "vaccination_status":
                    "Vaccinated",

                "discharge_status":
                    "Recovered",

                "recovery_days":
                    7,

                "treatment_duration_days":
                    5,

                "readmitted_within_30_days":
                    False,

                "follow_up_status":
                    "Completed",

                "complication_count":
                    0,

                "admission_required":
                    False,

                "referral_required":
                    False,
            }
        )

        # --------------------------------------------------------------
        # Associated symptom
        # --------------------------------------------------------------

        connection.execute(
            text(
                """
                INSERT INTO encounter_symptoms (
                    encounter_id,
                    symptom_id,
                    symptom_text,
                    symptom_source,
                    is_primary,
                    onset_stage,
                    severity,
                    duration_days,
                    frequency,
                    progression,
                    onset_timestamp
                )
                VALUES (
                    :encounter_id,
                    :symptom_id,
                    :symptom_text,
                    :symptom_source,
                    :is_primary,
                    :onset_stage,
                    :severity,
                    :duration_days,
                    :frequency,
                    :progression,
                    :onset_timestamp
                )
                """
            ),
            {
                "encounter_id":
                    TEST_ENCOUNTER_ID,

                "symptom_id":
                    TEST_SYMPTOM_ID,

                "symptom_text":
                    "Chest Pain",

                "symptom_source":
                    "MASTER",

                "is_primary":
                    True,

                "onset_stage":
                    "Initial",

                "severity":
                    "Moderate",

                "duration_days":
                    2,

                "frequency":
                    "Occasional",

                "progression":
                    "Stable",

                "onset_timestamp":
                    test_timestamp - timedelta(days=2),
            }
        )


# ============================================================================
# RUN B13
# ============================================================================

def run_b13():

    print(
        "\n" + "=" * 80
    )

    print(
        "RUNNING B13 AFTER TEST DATA INSERTION"
    )

    print(
        "=" * 80
    )

    env = os.environ.copy()

    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(B13_SCRIPT),
        ],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    if result.stdout:

        print(
            result.stdout
        )

    if result.stderr:

        print(
            result.stderr
        )

    if result.returncode != 0:

        raise RuntimeError(
            "B13 failed during controlled "
            "update test."
        )

    return result.stdout


# ============================================================================
# VALIDATE B13 OUTPUT
# ============================================================================

def validate_b13_output(
    baseline_count,
    output
):

    current_state = (
        get_database_state()
    )

    expected_count = (
        baseline_count + 1
    )

    count_detected = (
        current_state[
            "total_encounters"
        ]
        ==
        expected_count
    )

    output_detected = (
        "New encounters detected: 1"
        in output
    )

    pipeline_success = (
        "Pipeline status: UPDATE_SUCCESS"
        in output
    )

    all_stages_completed = all(
        stage in output
        for stage in [
            "B1",
            "B2",
            "B3",
            "B4",
            "B5",
            "B6",
            "B7",
            "B8",
            "B9",
            "B10",
            "B11",
            "B12",
        ]
    )

    result = {

        "test_timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "baseline_encounters":
            baseline_count,

        "encounters_after_insertion":
            current_state[
                "total_encounters"
            ],

        "expected_encounters":
            expected_count,

        "new_record_detected":
            output_detected,

        "database_count_verified":
            count_detected,

        "pipeline_update_success":
            pipeline_success,

        "all_B1_to_B12_completed":
            all_stages_completed,

        "B13_TEST_PASS":
            (
                count_detected
                and output_detected
                and pipeline_success
                and all_stages_completed
            ),
    }

    pd.DataFrame(
        [result]
    ).to_csv(
        TEST_OUTPUT,
        index=False
    )

    return result


# ============================================================================
# CLEANUP TEST DATA
# ============================================================================

def cleanup_test_data():

    print(
        "\n" + "=" * 80
    )

    print(
        "REMOVING TEMPORARY TEST DATA"
    )

    print(
        "=" * 80
    )

    remove_existing_test_record()

    state = (
        get_database_state()
    )

    print(
        f"Database encounters after cleanup: "
        f"{state['total_encounters']}"
    )

    return state


# ============================================================================
# REFRESH NORMAL OUTPUTS
# ============================================================================

def refresh_normal_outputs():

    """
    After removing the temporary test record,
    regenerate B1-B12 so the analytical CSV files
    correspond to the real database again.

    B13 itself is not used here because the temporary
    state has already been removed.
    """

    print(
        "\n" + "=" * 80
    )

    print(
        "RESTORING NORMAL SURVEILLANCE OUTPUTS"
    )

    print(
        "=" * 80
    )

    env = os.environ.copy()

    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    modules = [

        "outbreak_detection.py",

        "symptom_surveillance.py",

        "historical_baseline.py",

        "anomaly_detection.py",

        "temporal_acceleration.py",

        "persistence_detection.py",

        "spatial_propagation.py",

        "objective_a_integration.py",

        "severity_burden.py",

        "outbreak_risk_engine.py",

        "alert_engine.py",

        "explainability_engine.py",
    ]

    for script_name in modules:

        script_path = (
            BASE_DIR / script_name
        )

        print(
            f"\nRestoring: {script_name}"
        )

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
            ],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        if result.stdout:

            print(
                result.stdout
            )

        if result.stderr:

            print(
                result.stderr
            )

        if result.returncode != 0:

            raise RuntimeError(
                f"Failed while restoring "
                f"{script_name}"
            )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)

    print(
        "B13 - CONTROLLED UPDATE VALIDATION"
    )

    print("=" * 80)

    # ------------------------------------------------------------------
    # Make sure no previous interrupted test record exists.
    # ------------------------------------------------------------------

    remove_existing_test_record()

    # ------------------------------------------------------------------
    # Baseline
    # ------------------------------------------------------------------

    baseline = (
        get_database_state()
    )

    baseline_count = (
        baseline[
            "total_encounters"
        ]
    )

    print(
        "\nBASELINE"
    )

    print(
        f"Total encounters: "
        f"{baseline_count}"
    )

    print(
        f"Latest encounter: "
        f"{baseline['latest_encounter']}"
    )

    # ------------------------------------------------------------------
    # Insert temporary record
    # ------------------------------------------------------------------

    print(
        "\n" + "=" * 80
    )

    print(
        "INSERTING TEMPORARY TEST ENCOUNTER"
    )

    print(
        "=" * 80
    )

    insert_test_encounter()

    after_insert = (
        get_database_state()
    )

    print(
        f"Encounters after insertion: "
        f"{after_insert['total_encounters']}"
    )

    print(
        f"Test encounter ID: "
        f"{TEST_ENCOUNTER_ID}"
    )

    print(
        f"Test symptom: "
        f"{TEST_SYMPTOM_ID}"
    )

    # ------------------------------------------------------------------
    # Run B13
    # ------------------------------------------------------------------

    try:

        b13_output = run_b13()

        # --------------------------------------------------------------
        # Validate
        # --------------------------------------------------------------

        validation = (
            validate_b13_output(
                baseline_count,
                b13_output,
            )
        )

        print(
            "\n" + "=" * 80
        )

        print(
            "B13 CONTROLLED TEST RESULT"
        )

        print(
            "=" * 80
        )

        print(
            f"Baseline encounters: "
            f"{validation['baseline_encounters']}"
        )

        print(
            f"Encounters after insertion: "
            f"{validation['encounters_after_insertion']}"
        )

        print(
            f"New record detected: "
            f"{validation['new_record_detected']}"
        )

        print(
            f"Database count verified: "
            f"{validation['database_count_verified']}"
        )

        print(
            f"Pipeline update successful: "
            f"{validation['pipeline_update_success']}"
        )

        print(
            f"B1-B12 completed: "
            f"{validation['all_B1_to_B12_completed']}"
        )

        print(
            "\nFINAL TEST STATUS:"
        )

        if validation[
            "B13_TEST_PASS"
        ]:

            print(
                "B13 CONTROLLED TEST: PASS"
            )

        else:

            print(
                "B13 CONTROLLED TEST: FAIL"
            )

    finally:

        # --------------------------------------------------------------
        # Always remove temporary record.
        # --------------------------------------------------------------

        cleanup_test_data()

        # --------------------------------------------------------------
        # Restore analytical outputs to the real dataset.
        # --------------------------------------------------------------

        refresh_normal_outputs()

    # ------------------------------------------------------------------
    # Final database verification
    # ------------------------------------------------------------------

    final_state = (
        get_database_state()
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "FINAL DATABASE VERIFICATION"
    )

    print(
        "=" * 80
    )

    print(
        f"Original encounters: "
        f"{baseline_count}"
    )

    print(
        f"Final encounters: "
        f"{final_state['total_encounters']}"
    )

    if (
        final_state[
            "total_encounters"
        ]
        ==
        baseline_count
    ):

        print(
            "Database successfully restored."
        )

    else:

        print(
            "WARNING: database count does "
            "not match the original baseline."
        )

    print(
        f"\nTest evidence saved to:"
    )

    print(
        TEST_OUTPUT
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "B13 CONTROLLED VALIDATION COMPLETE"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":

    main()
"""
B13 - Continuous Update Pipeline

Purpose
-------
Demonstrates the continuous-update architecture of the
healthcare surveillance system.

Pipeline:

    New clinical data
          ↓
    PostgreSQL
          ↓
    Detect new encounters
          ↓
    Refresh surveillance outputs
          ↓
    B1-B10
          ↓
    B11 Alert Engine
          ↓
    B12 Explainability

B13 is intentionally implemented as a pipeline/orchestration
layer rather than as a FastAPI service.

The backend/frontend will be connected later.

Outputs
-------
b13_update_log.csv
b13_system_state.csv
"""

from pathlib import Path
from datetime import datetime

import os
import subprocess
import sys

import pandas as pd
from sqlalchemy import text


# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

UPDATE_LOG_FILE = (
    BASE_DIR / "b13_update_log.csv"
)

SYSTEM_STATE_FILE = (
    BASE_DIR / "b13_system_state.csv"
)


# ============================================================================
# DATABASE
# ============================================================================

def get_database_engine():

    """
    Import the existing project database engine.

    The project database.py is located at the repository root,
    while this B13 script is several directories deeper.
    """

    # continuous_update_pipeline.py
    #   ↓
    # outbreak_detection_child
    #   ↓
    # outbreak_detection_parent
    #   ↓
    # ML
    #   ↓
    # synthetic_generator (project root)

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
# PIPELINE MODULES
# ============================================================================

# IMPORTANT:
# outbreak_detection.py is the disease surveillance module (B1).
#
# B2 must point to the actual symptom surveillance script.
# If your symptom surveillance file has a different name,
# change only the B2 filename below.

PIPELINE_MODULES = [

    (
        "B1",
        "outbreak_detection.py",
    ),

    (
        "B2",
        "symptom_surveillance.py",
    ),

    (
        "B3",
        "historical_baseline.py",
    ),

    (
        "B4",
        "anomaly_detection.py",
    ),

    (
        "B5",
        "temporal_acceleration.py",
    ),

    (
        "B6",
        "persistence_detection.py",
    ),

    (
        "B7",
        "spatial_propagation.py",
    ),

    (
        "B8",
        "objective_a_integration.py",
    ),

    (
        "B9",
        "severity_burden.py",
    ),

    (
        "B10",
        "outbreak_risk_engine.py",
    ),

    (
        "B11",
        "alert_engine.py",
    ),

    (
        "B12",
        "explainability_engine.py",
    ),
]


# ============================================================================
# DATABASE STATE
# ============================================================================

def get_database_state():

    """
    Read the current state of the encounter database.

    Returns:
        total_encounters
        earliest_encounter
        latest_encounter
    """

    print(
        "\nChecking current database state..."
    )

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

    if row is None:

        return {
            "total_encounters": 0,
            "earliest_encounter": None,
            "latest_encounter": None,
        }

    state = {
        "total_encounters": int(
            row.total_encounters
        ),
        "earliest_encounter":
            row.earliest_encounter,
        "latest_encounter":
            row.latest_encounter,
    }

    print(
        f"Total encounters: "
        f"{state['total_encounters']}"
    )

    print(
        f"Earliest encounter: "
        f"{state['earliest_encounter']}"
    )

    print(
        f"Latest encounter: "
        f"{state['latest_encounter']}"
    )

    return state


# ============================================================================
# PREVIOUS PIPELINE STATE
# ============================================================================

def load_previous_state():

    """
    Load the previous B13 system state if available.
    """

    if not SYSTEM_STATE_FILE.exists():

        return None

    try:

        df = pd.read_csv(
            SYSTEM_STATE_FILE
        )

        if df.empty:

            return None

        row = df.iloc[-1]

        return {
            "total_encounters":
                int(
                    row[
                        "total_encounters"
                    ]
                ),

            "latest_encounter":
                row[
                    "latest_encounter"
                ],
        }

    except Exception as exc:

        print(
            "Warning: could not load "
            f"previous state: {exc}"
        )

        return None


# ============================================================================
# DETECT NEW DATA
# ============================================================================

def detect_new_data(
    current_state,
    previous_state,
):

    """
    Determine whether new encounter data has appeared
    since the previous B13 execution.
    """

    if previous_state is None:

        print(
            "\nNo previous B13 state found."
        )

        print(
            "This will be treated as "
            "the initial pipeline run."
        )

        return True, (
            current_state[
                "total_encounters"
            ]
        )

    current_count = (
        current_state[
            "total_encounters"
        ]
    )

    previous_count = (
        previous_state[
            "total_encounters"
        ]
    )

    new_records = (
        current_count
        -
        previous_count
    )

    if new_records > 0:

        print(
            f"\nNew encounters detected: "
            f"{new_records}"
        )

        return True, new_records

    print(
        "\nNo new encounters detected."
    )

    return False, 0


# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

def run_module(
    module_name,
    script_name,
):

    """
    Execute one surveillance module as a subprocess.

    UTF-8 is explicitly configured because Windows may use
    CP1252 for the console. This prevents Unicode characters
    such as arrows from crashing child modules.
    """

    script_path = (
        BASE_DIR / script_name
    )

    print(
        "\n" + "-" * 70
    )

    print(
        f"Running {module_name}: "
        f"{script_name}"
    )

    print(
        "-" * 70
    )

    if not script_path.exists():

        raise FileNotFoundError(
            f"Pipeline module not found: "
            f"{script_path}"
        )

    # ------------------------------------------------------------------
    # Force UTF-8 for the child Python process.
    # ------------------------------------------------------------------

    env = os.environ.copy()

    env["PYTHONIOENCODING"] = "utf-8"

    env["PYTHONUTF8"] = "1"

    # ------------------------------------------------------------------
    # Execute child module.
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Print module output.
    # ------------------------------------------------------------------

    if result.stdout:

        print(
            result.stdout
        )

    if result.stderr:

        print(
            result.stderr
        )

    # ------------------------------------------------------------------
    # Check module status.
    # ------------------------------------------------------------------

    if result.returncode != 0:

        raise RuntimeError(
            f"{module_name} failed "
            f"with return code "
            f"{result.returncode}"
        )

    print(
        f"{module_name} completed successfully."
    )

    return True


# ============================================================================
# RUN FULL UPDATE
# ============================================================================

def run_surveillance_update():

    """
    Execute the complete surveillance pipeline
    in dependency order.
    """

    print(
        "\n" + "=" * 80
    )

    print(
        "RUNNING SURVEILLANCE UPDATE"
    )

    print(
        "=" * 80
    )

    completed = []

    for module_name, script_name in (
        PIPELINE_MODULES
    ):

        run_module(
            module_name,
            script_name,
        )

        completed.append(
            module_name
        )

    return completed


# ============================================================================
# READ CURRENT ALERT STATE
# ============================================================================

def read_alert_state():

    """
    Read the latest B11 alert state after the update.
    """

    alert_file = (
        BASE_DIR /
        "alert_engine_latest.csv"
    )

    state = {
        "latest_week": None,
        "green_alerts": 0,
        "yellow_alerts": 0,
        "orange_alerts": 0,
        "red_alerts": 0,
        "watch_alerts": 0,
        "active_alerts": 0,
        "strongest_symptom": None,
        "strongest_risk_score": 0.0,
    }

    # ------------------------------------------------------------------
    # B11
    # ------------------------------------------------------------------

    if alert_file.exists():

        alerts = pd.read_csv(
            alert_file
        )

        if not alerts.empty:

            if "week" in alerts.columns:

                state[
                    "latest_week"
                ] = str(
                    alerts[
                        "week"
                    ].max()
                )

            # ----------------------------------------------------------
            # Alert levels
            # ----------------------------------------------------------

            if "alert_level" in alerts.columns:

                counts = (
                    alerts[
                        "alert_level"
                    ]
                    .value_counts()
                )

                state[
                    "green_alerts"
                ] = int(
                    counts.get(
                        "GREEN",
                        0
                    )
                )

                state[
                    "yellow_alerts"
                ] = int(
                    counts.get(
                        "YELLOW",
                        0
                    )
                )

                state[
                    "orange_alerts"
                ] = int(
                    counts.get(
                        "ORANGE",
                        0
                    )
                )

                state[
                    "red_alerts"
                ] = int(
                    counts.get(
                        "RED",
                        0
                    )
                )

            # ----------------------------------------------------------
            # Alert status
            # ----------------------------------------------------------

            if "alert_status" in alerts.columns:

                status_counts = (
                    alerts[
                        "alert_status"
                    ]
                    .value_counts()
                )

                state[
                    "watch_alerts"
                ] = int(
                    status_counts.get(
                        "WATCH",
                        0
                    )
                )

                state[
                    "active_alerts"
                ] = int(
                    status_counts.get(
                        "ACTIVE",
                        0
                    )
                )

            # ----------------------------------------------------------
            # Strongest risk
            # ----------------------------------------------------------

            if "risk_score" in alerts.columns:

                alerts[
                    "risk_score"
                ] = pd.to_numeric(
                    alerts[
                        "risk_score"
                    ],
                    errors="coerce"
                ).fillna(0.0)

                if not alerts.empty:

                    strongest_index = (
                        alerts[
                            "risk_score"
                        ]
                        .idxmax()
                    )

                    strongest = (
                        alerts.loc[
                            strongest_index
                        ]
                    )

                    state[
                        "strongest_risk_score"
                    ] = float(
                        strongest[
                            "risk_score"
                        ]
                    )

                    if (
                        "symptom_name"
                        in alerts.columns
                    ):

                        state[
                            "strongest_symptom"
                        ] = str(
                            strongest[
                                "symptom_name"
                            ]
                        )

    return state


# ============================================================================
# SAVE STATE
# ============================================================================

def save_system_state(
    database_state,
    pipeline_status,
    new_records,
    alert_state,
):

    timestamp = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    row = {

        "update_timestamp":
            timestamp,

        "pipeline_status":
            pipeline_status,

        "new_records":
            new_records,

        "total_encounters":
            database_state[
                "total_encounters"
            ],

        "earliest_encounter":
            database_state[
                "earliest_encounter"
            ],

        "latest_encounter":
            database_state[
                "latest_encounter"
            ],

        "latest_surveillance_week":
            alert_state[
                "latest_week"
            ],

        "green_alerts":
            alert_state[
                "green_alerts"
            ],

        "yellow_alerts":
            alert_state[
                "yellow_alerts"
            ],

        "orange_alerts":
            alert_state[
                "orange_alerts"
            ],

        "red_alerts":
            alert_state[
                "red_alerts"
            ],

        "watch_alerts":
            alert_state[
                "watch_alerts"
            ],

        "active_alerts":
            alert_state[
                "active_alerts"
            ],

        "strongest_symptom":
            alert_state[
                "strongest_symptom"
            ],

        "strongest_risk_score":
            alert_state[
                "strongest_risk_score"
            ],
    }

    new_df = pd.DataFrame(
        [row]
    )

    # --------------------------------------------------------------
    # Append to historical state log.
    # --------------------------------------------------------------

    if SYSTEM_STATE_FILE.exists():

        existing = pd.read_csv(
            SYSTEM_STATE_FILE
        )

        combined = pd.concat(
            [
                existing,
                new_df,
            ],
            ignore_index=True,
        )

    else:

        combined = new_df

    combined.to_csv(
        SYSTEM_STATE_FILE,
        index=False
    )


# ============================================================================
# UPDATE LOG
# ============================================================================

def save_update_log(
    database_state,
    previous_state,
    new_records,
    pipeline_status,
    completed_modules,
):

    timestamp = (
        datetime.now()
        .isoformat(
            timespec="seconds"
        )
    )

    previous_count = (
        None
        if previous_state is None
        else previous_state[
            "total_encounters"
        ]
    )

    row = {

        "update_timestamp":
            timestamp,

        "pipeline_status":
            pipeline_status,

        "previous_encounters":
            previous_count,

        "current_encounters":
            database_state[
                "total_encounters"
            ],

        "new_records":
            new_records,

        "latest_encounter":
            database_state[
                "latest_encounter"
            ],

        "completed_modules":
            ", ".join(
                completed_modules
            ),
    }

    new_df = pd.DataFrame(
        [row]
    )

    if UPDATE_LOG_FILE.exists():

        existing = pd.read_csv(
            UPDATE_LOG_FILE
        )

        combined = pd.concat(
            [
                existing,
                new_df,
            ],
            ignore_index=True,
        )

    else:

        combined = new_df

    combined.to_csv(
        UPDATE_LOG_FILE,
        index=False
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)

    print(
        "B13 - CONTINUOUS UPDATE PIPELINE"
    )

    print("=" * 80)

    # ------------------------------------------------------------------
    # Current database state
    # ------------------------------------------------------------------

    current_state = (
        get_database_state()
    )

    # ------------------------------------------------------------------
    # Previous state
    # ------------------------------------------------------------------

    previous_state = (
        load_previous_state()
    )

    # ------------------------------------------------------------------
    # Detect changes
    # ------------------------------------------------------------------

    has_new_data, new_records = (
        detect_new_data(
            current_state,
            previous_state,
        )
    )

    # ------------------------------------------------------------------
    # No new data
    # ------------------------------------------------------------------

    if (
        not has_new_data
        and previous_state is not None
    ):

        print(
            "\nNo surveillance update required."
        )

        print(
            "Existing analytical outputs "
            "remain current."
        )

        alert_state = (
            read_alert_state()
        )

        save_update_log(
            current_state,
            previous_state,
            0,
            "NO_UPDATE_REQUIRED",
            [],
        )

        save_system_state(
            current_state,
            "NO_UPDATE_REQUIRED",
            0,
            alert_state,
        )

        print(
            "\n" + "=" * 80
        )

        print(
            "B13 COMPLETE - NO NEW DATA"
        )

        print(
            "=" * 80
        )

        return

    # ------------------------------------------------------------------
    # New data / initial run
    # ------------------------------------------------------------------

    try:

        completed_modules = (
            run_surveillance_update()
        )

        pipeline_status = (
            "UPDATE_SUCCESS"
        )

    except Exception as exc:

        print(
            "\n" + "=" * 80
        )

        print(
            "B13 UPDATE FAILED"
        )

        print(
            "=" * 80
        )

        print(
            f"Error: {exc}"
        )

        save_update_log(
            current_state,
            previous_state,
            new_records,
            "UPDATE_FAILED",
            [],
        )

        raise

    # ------------------------------------------------------------------
    # Read updated alert state
    # ------------------------------------------------------------------

    alert_state = (
        read_alert_state()
    )

    # ------------------------------------------------------------------
    # Save state
    # ------------------------------------------------------------------

    save_update_log(
        current_state,
        previous_state,
        new_records,
        pipeline_status,
        completed_modules,
    )

    save_system_state(
        current_state,
        pipeline_status,
        new_records,
        alert_state,
    )

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------

    print(
        "\n" + "=" * 80
    )

    print(
        "B13 COMPLETE"
    )

    print(
        "=" * 80
    )

    print(
        f"Pipeline status: "
        f"{pipeline_status}"
    )

    print(
        f"New records processed: "
        f"{new_records}"
    )

    print(
        f"Total encounters: "
        f"{current_state['total_encounters']}"
    )

    print(
        f"Latest encounter: "
        f"{current_state['latest_encounter']}"
    )

    print(
        f"Latest surveillance week: "
        f"{alert_state['latest_week']}"
    )

    print(
        "\nUpdated alert state:"
    )

    print(
        f"GREEN:   "
        f"{alert_state['green_alerts']}"
    )

    print(
        f"YELLOW:  "
        f"{alert_state['yellow_alerts']}"
    )

    print(
        f"ORANGE:  "
        f"{alert_state['orange_alerts']}"
    )

    print(
        f"RED:     "
        f"{alert_state['red_alerts']}"
    )

    print(
        f"WATCH:   "
        f"{alert_state['watch_alerts']}"
    )

    print(
        f"ACTIVE:  "
        f"{alert_state['active_alerts']}"
    )

    print(
        "\nStrongest current signal:"
    )

    print(
        f"Symptom: "
        f"{alert_state['strongest_symptom']}"
    )

    print(
        f"Risk score: "
        f"{alert_state['strongest_risk_score']:.2f}"
    )

    print(
        "\nPipeline stages completed:"
    )

    print(
        " -> ".join(
            completed_modules
        )
    )

    print(
        f"\nUpdate log: "
        f"{UPDATE_LOG_FILE}"
    )

    print(
        f"System state: "
        f"{SYSTEM_STATE_FILE}"
    )

    print(
        "\n" + "=" * 80
    )

    print(
        "B13 READY FOR REVIEW"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":
    main()
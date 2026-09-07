from pathlib import Path
import pandas as pd


# ============================================================
# OBJECTIVE C — FEDERATED LEARNING DATA MINIMIZATION
# ============================================================
#
# This module enforces the data-minimization boundary for
# the current federated-learning task.
#
# The local hospital dataset may contain additional clinical,
# administrative, temporal, treatment, and identifier fields.
#
# Only the fields required by the current FL task are passed
# into the federated training pipeline.
#
# IMPORTANT:
# Data minimization controls what enters FL training.
# Protection of model updates leaving the hospital is handled
# by later Objective C stages (C5 onward).
# ============================================================


# ============================================================
# CURRENT FL MODEL INPUT FEATURES
# ============================================================
#
# These MUST match FEATURE_COLUMNS in federated_learning/task.py
#
# Current FL model:
#   11 input features
#   27 symptom targets
#   38 total columns
# ============================================================

FEDERATED_FEATURE_COLUMNS = [
    "age",
    "temperature",
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "spo2",
    "symptom_onset_days",
    "travel_history",
    "vaccination_status",
]


# ============================================================
# CURRENT FL SYMPTOM TARGETS
# ============================================================
#
# These MUST match TARGET_COLUMNS in federated_learning/task.py
# ============================================================

FEDERATED_TARGET_COLUMNS = [
    "Abdominal Pain",
    "Anaemia",
    "Bleeding",
    "Breathlessness",
    "Chest Pain",
    "Chills",
    "Dehydration",
    "Diarrhoea",
    "Dry Cough",
    "Fatigue",
    "Fever",
    "Headache",
    "Joint Pain",
    "Loss of Appetite",
    "Loss of Smell",
    "Loss of Taste",
    "Muscle Pain",
    "Nausea",
    "Night Sweats",
    "Persistent Cough",
    "Rash",
    "Retro-orbital Pain",
    "Runny Nose",
    "Sore Throat",
    "Sweating",
    "Vomiting",
    "Weight Loss",
]


# ============================================================
# FIELDS THAT MUST NOT ENTER THE FL TRAINING VIEW
# ============================================================

FEDERATED_FORBIDDEN_FIELDS = [
    # Direct / linkable identifiers
    "patient_id",
    "encounter_id",

    # Hospital / administrative metadata
    "hospital_id",
    "visit_timestamp",
    "visit_type",
    "admission_status",
    "discharge_status",
    "occupation",
    "district",
    "state",

    # Fields not required by the current FL task
    "gender",
    "disease_id",
    "severity_id",
    "recovery_days",

    # Clinical temporal / contextual fields not used by
    # the current FL feature contract
    # NOTE: symptom_onset_days is ALLOWED above.
    # NOTE: travel_history is ALLOWED above.
    # NOTE: vaccination_status is ALLOWED above.

    # Treatment-related information
    "treatment_id",
    "treatment_notes",
    "recommended_by_ai",
    "accepted_by_doctor",
    "treatment_origin",
    "treatment_sequence",
    "administered",
    "is_primary",

    # Complication-related information
    "complication_id",
    "identified_timestamp",
    "notes",
    "resolved",
]


# ============================================================
# EXPECTED SCHEMA SIZE
# ============================================================

EXPECTED_FEATURE_COUNT = len(
    FEDERATED_FEATURE_COLUMNS
)

EXPECTED_TARGET_COUNT = len(
    FEDERATED_TARGET_COLUMNS
)

EXPECTED_FEDERATED_COLUMN_COUNT = (
    EXPECTED_FEATURE_COUNT
    + EXPECTED_TARGET_COUNT
)


# ============================================================
# SYMPTOM SCHEMA VALIDATION
# ============================================================

def identify_symptom_columns(df):
    """
    Return the exact 27 symptom target columns required
    by the current federated-learning model.

    Symptom columns are NOT inferred from their data type
    or binary values.

    The explicit project FL schema is the source of truth.
    """

    missing = [
        column
        for column in FEDERATED_TARGET_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Federated dataset is missing required "
            "symptom target columns:\n"
            + "\n".join(missing)
        )

    return FEDERATED_TARGET_COLUMNS.copy()


# ============================================================
# REQUIRED COLUMN VALIDATION
# ============================================================

def validate_federated_schema(df):
    """
    Validate that the incoming local dataset contains
    every field required by the current FL task.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "Expected pandas DataFrame."
        )

    required_columns = (
        FEDERATED_FEATURE_COLUMNS
        + FEDERATED_TARGET_COLUMNS
    )

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Federated dataset is missing required "
            "columns:\n"
            + "\n".join(missing)
        )

    return True


# ============================================================
# GET ALLOWED FEDERATED COLUMNS
# ============================================================

def get_allowed_federated_columns(df):
    """
    Return the exact columns allowed to enter the
    current federated-learning training pipeline.
    """

    validate_federated_schema(df)

    symptom_columns = (
        identify_symptom_columns(df)
    )

    if len(symptom_columns) != EXPECTED_TARGET_COUNT:
        raise ValueError(
            "Expected "
            f"{EXPECTED_TARGET_COUNT} symptom target "
            "columns, but detected "
            f"{len(symptom_columns)}."
        )

    allowed_columns = (
        FEDERATED_FEATURE_COLUMNS
        + symptom_columns
    )

    if len(allowed_columns) != (
        EXPECTED_FEDERATED_COLUMN_COUNT
    ):
        raise RuntimeError(
            "Federated schema definition is inconsistent."
        )

    return allowed_columns


# ============================================================
# DATA MINIMIZATION ENFORCEMENT
# ============================================================

def enforce_federated_minimization(df):
    """
    Apply the Objective C data-minimization policy.

    Returns a NEW dataframe containing ONLY the fields
    required by the current federated-learning task.

    The original dataframe is never modified.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "Expected pandas DataFrame."
        )

    allowed_columns = (
        get_allowed_federated_columns(df)
    )

    # --------------------------------------------------------
    # Create controlled local FL view
    # --------------------------------------------------------

    minimized = df[
        allowed_columns
    ].copy()

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    forbidden_remaining = [
        column
        for column in minimized.columns
        if column in FEDERATED_FORBIDDEN_FIELDS
    ]

    if forbidden_remaining:
        raise RuntimeError(
            "DATA MINIMIZATION FAILURE.\n"
            "Forbidden fields survived enforcement:\n"
            + "\n".join(forbidden_remaining)
        )

    # --------------------------------------------------------
    # Exact column-count check
    # --------------------------------------------------------

    if len(minimized.columns) != (
        EXPECTED_FEDERATED_COLUMN_COUNT
    ):
        raise RuntimeError(
            "DATA MINIMIZATION FAILURE.\n"
            f"Expected {EXPECTED_FEDERATED_COLUMN_COUNT} "
            "columns, but retained "
            f"{len(minimized.columns)}."
        )

    return minimized


# ============================================================
# AUDIT INFORMATION
# ============================================================

def audit_federated_dataframe(
    original_df,
    minimized_df,
):
    """
    Produce a machine-readable audit describing what
    the minimization layer retained and removed.
    """

    original_columns = set(
        original_df.columns
    )

    final_columns = set(
        minimized_df.columns
    )

    removed_columns = sorted(
        original_columns - final_columns
    )

    retained_columns = sorted(
        final_columns
    )

    forbidden_remaining = sorted(
        final_columns.intersection(
            FEDERATED_FORBIDDEN_FIELDS
        )
    )

    required_columns = set(
        FEDERATED_FEATURE_COLUMNS
        + FEDERATED_TARGET_COLUMNS
    )

    missing_required = sorted(
        required_columns - final_columns
    )

    passed = (
        len(retained_columns)
        == EXPECTED_FEDERATED_COLUMN_COUNT
        and not forbidden_remaining
        and not missing_required
    )

    return {
        "original_column_count":
            len(original_columns),

        "retained_column_count":
            len(retained_columns),

        "removed_column_count":
            len(removed_columns),

        "retained_columns":
            retained_columns,

        "removed_columns":
            removed_columns,

        "forbidden_fields_remaining":
            forbidden_remaining,

        "missing_required_fields":
            missing_required,

        "expected_feature_count":
            EXPECTED_FEATURE_COUNT,

        "expected_target_count":
            EXPECTED_TARGET_COUNT,

        "expected_federated_column_count":
            EXPECTED_FEDERATED_COLUMN_COUNT,

        "passed":
            passed,
    }


# ============================================================
# HOSPITAL DATA LOADER
# ============================================================

def load_and_minimize_hospital_data(
    file_path,
):
    """
    Load one hospital-local ML dataset and apply
    Objective C data minimization.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Hospital dataset not found: {file_path}"
        )

    original = pd.read_csv(
        file_path
    )

    minimized = (
        enforce_federated_minimization(
            original
        )
    )

    audit = audit_federated_dataframe(
        original,
        minimized
    )

    if not audit["passed"]:
        raise RuntimeError(
            "Federated data-minimization audit failed."
        )

    return minimized, audit


# ============================================================
# SELF TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print(
        "OBJECTIVE C — DATA MINIMIZATION POLICY"
    )
    print("=" * 70)

    print(
        "\nFL feature count:",
        EXPECTED_FEATURE_COUNT,
    )

    print(
        "FL target count:",
        EXPECTED_TARGET_COUNT,
    )

    print(
        "Total federated columns:",
        EXPECTED_FEDERATED_COLUMN_COUNT,
    )

    print("\nAllowed FL features:")

    for field in FEDERATED_FEATURE_COLUMNS:
        print(f"  [ALLOW] {field}")

    print("\nFL symptom targets:")

    for field in FEDERATED_TARGET_COLUMNS:
        print(f"  [TARGET] {field}")

    print("\nForbidden fields:")

    for field in FEDERATED_FORBIDDEN_FIELDS:
        print(f"  [BLOCK] {field}")

    print(
        "\nPolicy definition loaded successfully."
    )
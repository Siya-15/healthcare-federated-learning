import pandas as pd

from ML.privacy.data_minimization_enforcer import (
    FEDERATED_FEATURE_COLUMNS,
    FEDERATED_TARGET_COLUMNS,
    FEDERATED_FORBIDDEN_FIELDS,
    EXPECTED_FEDERATED_COLUMN_COUNT,
    enforce_federated_minimization,
    audit_federated_dataframe,
)


# ============================================================
# TEST DATA
# ============================================================

def create_test_dataframe():

    data = {

        # ----------------------------------------------------
        # Forbidden identifiers
        # ----------------------------------------------------

        "patient_id": [
            "PAT001",
            "PAT002",
        ],

        "encounter_id": [
            "ENC001",
            "ENC002",
        ],

        "hospital_id": [
            "H001",
            "H001",
        ],

        "visit_timestamp": [
            "2026-08-01",
            "2026-08-02",
        ],

        # ----------------------------------------------------
        # Additional forbidden / unrelated fields
        # ----------------------------------------------------

        "gender": [
            "Male",
            "Female",
        ],

        "disease_id": [
            "D001",
            "D002",
        ],

        "severity_id": [
            "SV001",
            "SV002",
        ],

        "occupation": [
            "Engineer",
            "Teacher",
        ],

        "visit_type": [
            "New",
            "New",
        ],

        "recovery_days": [
            7,
            8,
        ],

        # ----------------------------------------------------
        # Actual FL features
        # ----------------------------------------------------

        "age": [
            25,
            42,
        ],

        "temperature": [
            38.2,
            37.8,
        ],

        "heart_rate": [
            90,
            88,
        ],

        "respiratory_rate": [
            20,
            18,
        ],

        "systolic_bp": [
            110,
            115,
        ],

        "diastolic_bp": [
            70,
            75,
        ],

        "spo2": [
            97,
            98,
        ],

        "symptom_onset_days": [
            3,
            5,
        ],

        "travel_history": [
            True,
            False,
        ],

        "vaccination_status": [
            "Vaccinated",
            "Not Vaccinated",
        ],
    }

    # --------------------------------------------------------
    # Actual 27 FL symptom target columns
    # --------------------------------------------------------

    for index, symptom in enumerate(
        FEDERATED_TARGET_COLUMNS
    ):

        data[symptom] = [
            index % 2,
            (index + 1) % 2,
        ]

    return pd.DataFrame(data)


# ============================================================
# TEST
# ============================================================

def run_test():

    print("=" * 70)
    print(
        "C1 DATA MINIMIZATION TEST"
    )
    print("=" * 70)

    original = (
        create_test_dataframe()
    )

    minimized = (
        enforce_federated_minimization(
            original
        )
    )

    audit = (
        audit_federated_dataframe(
            original,
            minimized
        )
    )

    # --------------------------------------------------------
    # Check expected final size
    # --------------------------------------------------------

    assert (
        len(minimized.columns)
        == EXPECTED_FEDERATED_COLUMN_COUNT
    ), (
        "Expected "
        f"{EXPECTED_FEDERATED_COLUMN_COUNT} "
        "federated fields, got "
        f"{len(minimized.columns)}"
    )

    # --------------------------------------------------------
    # Check every FL feature survives
    # --------------------------------------------------------

    for field in FEDERATED_FEATURE_COLUMNS:

        assert field in minimized.columns, (
            f"Required FL feature missing: {field}"
        )

    # --------------------------------------------------------
    # Check every FL target survives
    # --------------------------------------------------------

    for field in FEDERATED_TARGET_COLUMNS:

        assert field in minimized.columns, (
            f"Required symptom target missing: {field}"
        )

    # --------------------------------------------------------
    # Check every forbidden field is removed
    # --------------------------------------------------------

    for field in FEDERATED_FORBIDDEN_FIELDS:

        assert field not in minimized.columns, (
            f"Forbidden field survived: {field}"
        )

    # --------------------------------------------------------
    # Check exact target count
    # --------------------------------------------------------

    retained_targets = [
        column
        for column in minimized.columns
        if column in FEDERATED_TARGET_COLUMNS
    ]

    assert (
        len(retained_targets)
        == len(FEDERATED_TARGET_COLUMNS)
    ), (
        "Expected "
        f"{len(FEDERATED_TARGET_COLUMNS)} "
        "symptom targets, got "
        f"{len(retained_targets)}"
    )

    # --------------------------------------------------------
    # Check original dataframe is unchanged
    # --------------------------------------------------------

    assert (
        "patient_id"
        in original.columns
    )

    assert (
        "encounter_id"
        in original.columns
    )

    assert (
        "hospital_id"
        in original.columns
    )

    assert (
        "gender"
        in original.columns
    )

    # --------------------------------------------------------
    # Check forbidden fields are actually removed
    # --------------------------------------------------------

    assert (
        "patient_id"
        not in minimized.columns
    )

    assert (
        "encounter_id"
        not in minimized.columns
    )

    assert (
        "hospital_id"
        not in minimized.columns
    )

    assert (
        "gender"
        not in minimized.columns
    )

    assert (
        "disease_id"
        not in minimized.columns
    )

    assert (
        "severity_id"
        not in minimized.columns
    )

    # --------------------------------------------------------
    # Check audit
    # --------------------------------------------------------

    assert audit["passed"]

    assert (
        audit["forbidden_fields_remaining"]
        == []
    )

    assert (
        audit["missing_required_fields"]
        == []
    )

    # --------------------------------------------------------
    # Print result
    # --------------------------------------------------------

    print(
        "\nOriginal columns:"
    )

    print(
        audit["original_column_count"]
    )

    print(
        "\nRetained federated columns:"
    )

    print(
        audit["retained_column_count"]
    )

    print(
        "\nRemoved columns:"
    )

    print(
        audit["removed_column_count"]
    )

    print(
        "\nExpected FL features:"
    )

    print(
        len(FEDERATED_FEATURE_COLUMNS)
    )

    print(
        "\nExpected symptom targets:"
    )

    print(
        len(FEDERATED_TARGET_COLUMNS)
    )

    print(
        "\nExpected federated columns:"
    )

    print(
        EXPECTED_FEDERATED_COLUMN_COUNT
    )

    print(
        "\nForbidden fields remaining:"
    )

    print(
        audit["forbidden_fields_remaining"]
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "C1 DATA MINIMIZATION: PASS"
    )

    print("=" * 70)


if __name__ == "__main__":
    run_test()
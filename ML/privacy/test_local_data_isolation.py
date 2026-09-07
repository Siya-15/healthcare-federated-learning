"""
C2 Controlled Validation
Local Data Isolation
"""

import numpy as np

from ML.privacy.local_data_isolation import (
    inspect_federated_payload,
    inspect_dataframe_for_leakage,
    validate_model_update,
)


def test_clean_payload():

    payload = {
        "arrays": [
            np.zeros((10, 10)),
            np.zeros((10,)),
        ],
        "metrics": {
            "num-examples": 100,
        },
    }

    result = inspect_federated_payload(
        payload
    )

    assert result["passed"] is True

    print(
        "PASS: Clean federated payload accepted."
    )


def test_forbidden_payload():

    payload = {
        "arrays": [
            np.zeros((10, 10)),
        ],
        "metrics": {
            "num-examples": 100,
        },
        "patient_id": "P001",
        "encounter_id": "E001",
        "clinical_data": "LEAKED DATA",
    }

    result = inspect_federated_payload(
        payload
    )

    assert result["passed"] is False

    assert (
        "patient_id"
        in result["forbidden_fields"]
    )

    assert (
        "encounter_id"
        in result["forbidden_fields"]
    )

    assert (
        "clinical_data"
        in result["forbidden_fields"]
    )

    print(
        "PASS: Forbidden payload rejected."
    )


def test_local_dataframe():

    columns = [
        "age",
        "temperature",
        "heart_rate",
        "spo2",
    ]

    result = inspect_dataframe_for_leakage(
        columns
    )

    assert result["passed"] is True

    print(
        "PASS: Local model dataframe "
        "contains no forbidden identifiers."
    )


def test_dataframe_leakage():

    columns = [
        "age",
        "temperature",
        "patient_id",
        "encounter_id",
    ]

    result = inspect_dataframe_for_leakage(
        columns
    )

    assert result["passed"] is False

    assert (
        "patient_id"
        in result["leaked_fields"]
    )

    assert (
        "encounter_id"
        in result["leaked_fields"]
    )

    print(
        "PASS: Dataframe leakage detected."
    )


def test_model_update():

    parameters = [
        np.zeros((10, 32)),
        np.zeros((32,)),
        np.zeros((32, 27)),
        np.zeros((27,)),
    ]

    result = validate_model_update(
        parameters
    )

    assert result["passed"] is True

    print(
        "PASS: Model update validated."
    )


def run_all_tests():

    print("=" * 70)
    print("C2 LOCAL DATA ISOLATION VALIDATION")
    print("=" * 70)

    test_clean_payload()
    test_forbidden_payload()
    test_local_dataframe()
    test_dataframe_leakage()
    test_model_update()

    print("\n" + "=" * 70)
    print("C2 VALIDATION: PASS")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
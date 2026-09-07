import numpy as np
import pandas as pd

from ML.federated_learning.federated_dataset import (
    FEDERATED_FEATURE_COLUMNS,
    FEDERATED_TARGET_COLUMNS,
    standardize_federated_dataset,
    audit_federated_dataset,
)


def create_test_dataframe():

    data = {}

    # Features
    for column in FEDERATED_FEATURE_COLUMNS:

        if column == "travel_history":
            data[column] = [True, False, True]

        elif column == "vaccination_status":
            data[column] = [
                "Vaccinated",
                "Not Vaccinated",
                "Vaccinated",
            ]

        else:
            data[column] = [1, 2, 3]

    # Targets
    for index, column in enumerate(
        FEDERATED_TARGET_COLUMNS
    ):

        data[column] = [
            index % 2,
            (index + 1) % 2,
            0,
        ]

    return pd.DataFrame(data)


def test_standardization():

    df = create_test_dataframe()

    X, y = standardize_federated_dataset(
        df
    )

    result = audit_federated_dataset(
        X,
        y,
        hospital_id="TEST",
    )

    assert result["passed"] is True

    assert X.shape == (
        3,
        10,
    )

    assert y.shape == (
        3,
        27,
    )

    assert (
        list(X.columns)
        == FEDERATED_FEATURE_COLUMNS
    )

    assert (
        list(y.columns)
        == FEDERATED_TARGET_COLUMNS
    )

    assert np.all(
        np.isin(
            y.to_numpy(),
            [0, 1],
        )
    )

    print(
        "PASS: Standardized dataset."
    )


def test_boolean_encoding():

    df = create_test_dataframe()

    X, _ = standardize_federated_dataset(
        df
    )

    assert X["travel_history"].tolist() == [
        1,
        0,
        1,
    ]

    assert X["vaccination_status"].tolist() == [
        1,
        0,
        1,
    ]

    print(
        "PASS: Boolean/categorical encoding."
    )


def test_wrong_schema():

    df = create_test_dataframe()

    df = df.drop(
        columns=["Fever"]
    )

    try:

        standardize_federated_dataset(
            df
        )

        assert False

    except ValueError:

        pass

    print(
        "PASS: Invalid schema rejected."
    )


def run_all_tests():

    print("=" * 70)
    print("C3 STANDARDIZED FEDERATED DATASET")
    print("=" * 70)

    test_standardization()
    test_boolean_encoding()
    test_wrong_schema()

    print()
    print("=" * 70)
    print("C3 VALIDATION: PASS")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
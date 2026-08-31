import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import pandas as pd

from .privacy_protection import pseudonymize_patient_id


# ==========================================================
# OBJECTIVE A - PRIVACY VERIFICATION
# ==========================================================

def verify_pseudonymization():

    secret_key = os.environ.get(
        "PRIVACY_SECRET"
    )

    if not secret_key:

        raise ValueError(
            "PRIVACY_SECRET environment variable "
            "is not set."
        )

    # Simulated local patient records
    patients = pd.DataFrame({
        "patient_id": [
            "PAT-000001",
            "PAT-000002",
            "PAT-000003",
            "PAT-000004",
            "PAT-000005",
        ],
        "age": [
            25,
            41,
            63,
            37,
            52,
        ],
        "disease_id": [
            "D001",
            "D002",
            "D003",
            "D004",
            "D005",
        ]
    })

    # ------------------------------------------------------
    # Generate pseudonyms
    # ------------------------------------------------------

    patients[
        "patient_token"
    ] = patients[
        "patient_id"
    ].apply(
        lambda x:
        pseudonymize_patient_id(
            x,
            secret_key
        )
    )

    # ------------------------------------------------------
    # Check that pseudonyms were generated
    # ------------------------------------------------------

    pseudonym_generation = (
        patients["patient_token"]
        .notna()
        .all()
    )

    # ------------------------------------------------------
    # Check that pseudonyms are unique
    # ------------------------------------------------------

    pseudonym_uniqueness = (
        patients["patient_token"]
        .is_unique
    )

    # ------------------------------------------------------
    # Create analytical view WITHOUT patient_id
    # ------------------------------------------------------

    analytical_data = patients[
        [
            "patient_token",
            "age",
            "disease_id"
        ]
    ].copy()

    identifier_removed = (
        "patient_id"
        not in analytical_data.columns
    )

    # ------------------------------------------------------
    # Check deterministic linkage
    # ------------------------------------------------------

    repeated_token = (
        pseudonymize_patient_id(
            "PAT-000001",
            secret_key
        )
        ==
        pseudonymize_patient_id(
            "PAT-000001",
            secret_key
        )
    )

    # ------------------------------------------------------
    # Overall result
    # ------------------------------------------------------

    verification_passed = all([
        pseudonym_generation,
        pseudonym_uniqueness,
        identifier_removed,
        repeated_token,
    ])

    # ------------------------------------------------------
    # Display
    # ------------------------------------------------------

    print("=" * 70)
    print("OBJECTIVE A - PRIVACY VERIFICATION")
    print("=" * 70)

    print(
        "\nPseudonym generation:",
        "PASS" if pseudonym_generation
        else "FAIL"
    )

    print(
        "Pseudonym uniqueness:",
        "PASS" if pseudonym_uniqueness
        else "FAIL"
    )

    print(
        "Original identifier removed "
        "from analytical view:",
        "PASS" if identifier_removed
        else "FAIL"
    )

    print(
        "Deterministic local linkage:",
        "PASS" if repeated_token
        else "FAIL"
    )

    print(
        "\nAnalytical dataset:"
    )

    print(
        analytical_data.to_string(
            index=False
        )
    )

    print(
        "\n" + "-" * 70
    )

    if verification_passed:

        print(
            "PRIVACY VERIFICATION: PASS"
        )

    else:

        print(
            "PRIVACY VERIFICATION: FAIL"
        )

    print("-" * 70)

    return verification_passed


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    verify_pseudonymization()
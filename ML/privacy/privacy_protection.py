import hashlib
import os


# ==========================================================
# OBJECTIVE A - PSEUDONYMIZATION
# ==========================================================

def pseudonymize_patient_id(
    patient_id,
    secret_key
):
    """
    Generate a deterministic pseudonym for a patient ID.

    The original patient ID is never returned.
    The same patient ID + secret key produces the
    same pseudonym, allowing local record linkage.
    """

    value = (
        str(secret_key)
        + ":"
        + str(patient_id)
    )

    digest = hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()

    return "PSEUDO-" + digest[:16]


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    # In a real deployment this should be stored securely
    # and NOT hard-coded into source code.

    secret_key = os.environ.get(
        "PRIVACY_SECRET"
    )

    if not secret_key:

        print(
            "PRIVACY_SECRET environment variable "
            "is not set."
        )

        print(
            "\nFor testing only, you can temporarily "
            "set one before running."
        )

        print(
            '\nPowerShell example:'
        )

        print(
            '$env:PRIVACY_SECRET="local-hospital-secret"'
        )

        raise SystemExit

    test_patient = "PAT-000123"

    pseudonym = pseudonymize_patient_id(
        test_patient,
        secret_key
    )

    print("=" * 60)
    print("OBJECTIVE A - PSEUDONYMIZATION")
    print("=" * 60)

    print(
        f"\nOriginal patient ID:"
        f" {test_patient}"
    )

    print(
        f"Pseudonym:"
        f" {pseudonym}"
    )

    print(
        "\nThe original identifier is not "
        "used by the analytical output."
    )
import sys
import os

# ==========================================================
# ALLOW IMPORT FROM PARENT DIRECTORY
# ==========================================================

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import pandas as pd

from sqlalchemy import text

from database import get_engine


# ==========================================================
# LOAD TREATMENT MAPPINGS
# ==========================================================

def load_treatment_mappings():

    engine = get_engine()

    query = """
    SELECT
        mapping_id,
        disease_id,
        severity_id,
        treatment_id,
        priority,
        first_line,
        referral_required,
        comments
    FROM disease_treatment_mapping
    ORDER BY
        disease_id,
        severity_id,
        priority
    """

    with engine.connect() as connection:

        mappings = pd.read_sql(
            text(query),
            connection
        )

    return mappings


# ==========================================================
# GET CANDIDATE TREATMENTS
# ==========================================================

def get_candidate_treatments(
    disease_id,
    severity_id
):

    mappings = load_treatment_mappings()

    candidates = mappings[
        (
            mappings["disease_id"]
            == disease_id
        )
        &
        (
            mappings["severity_id"]
            == severity_id
        )
    ].copy()

    candidates = candidates.sort_values(
        "priority"
    )

    return candidates


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    # Example patient
    disease_id = "D001"
    severity_id = "SV001"

    candidates = get_candidate_treatments(
        disease_id,
        severity_id
    )

    print("=" * 60)
    print("OBJECTIVE E - CANDIDATE TREATMENT SELECTION")
    print("=" * 60)

    print(
        f"\nDisease: {disease_id}"
    )

    print(
        f"Severity: {severity_id}"
    )

    print(
        f"\nCandidate treatments: "
        f"{len(candidates)}"
    )

    if candidates.empty:

        print(
            "\nNo treatment mapping found."
        )

    else:

        print(
            "\nRecommended candidates:"
        )

        print(
            candidates[
                [
                    "treatment_id",
                    "priority",
                    "first_line",
                    "referral_required",
                    "comments",
                ]
            ]
            .to_string(index=False)
        )
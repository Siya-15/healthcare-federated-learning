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

from .patient_context import build_patient_context


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
    """
    Generate treatment candidates using only
    disease + severity mapping.

    This function does NOT perform:
    - ML prediction
    - treatment ranking
    - guideline filtering
    - availability checking
    - cost analysis
    - risk prediction
    """

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
        by=[
            "priority",
            "treatment_id"
        ]
    ).reset_index(
        drop=True
    )

    return candidates


# ==========================================================
# GET CANDIDATES FROM PATIENT CONTEXT
# ==========================================================

def get_candidates_from_context(context):
    """
    Generate candidates directly from the
    canonical E1 patient context.
    """

    if not context.get("context_valid", False):

        raise ValueError(
            "Cannot generate treatment candidates "
            "from an invalid patient context."
        )

    disease_id = context.get(
        "disease_id"
    )

    severity_id = context.get(
        "severity_id"
    )

    if not disease_id:
        raise ValueError(
            "Patient context does not contain disease_id."
        )

    if not severity_id:
        raise ValueError(
            "Patient context does not contain severity_id."
        )

    return get_candidate_treatments(
        disease_id=disease_id,
        severity_id=severity_id
    )


# ==========================================================
# BUILD CANDIDATE RECORDS
# ==========================================================

def build_candidate_records(
    context,
    candidates
):
    """
    Convert database mapping rows into a clean
    E2 candidate representation.

    No ML scores or clinical decisions are added here.
    """

    records = []

    for _, row in candidates.iterrows():

        record = {
            "encounter_id": context[
                "encounter_id"
            ],

            "disease_id": context[
                "disease_id"
            ],

            "severity_id": context[
                "severity_id"
            ],

            "mapping_id": row[
                "mapping_id"
            ],

            "treatment_id": row[
                "treatment_id"
            ],

            "priority": row[
                "priority"
            ],

            "first_line": row[
                "first_line"
            ],

            "referral_required": row[
                "referral_required"
            ],

            "comments": row[
                "comments"
            ],
        }

        records.append(
            record
        )

    return records


# ==========================================================
# MAIN E2 PIPELINE
# ==========================================================

def generate_candidates_for_encounter(
    encounter_id
):
    """
    Complete E1 -> E2 flow.

    encounter_id
        ↓
    patient context
        ↓
    disease + severity
        ↓
    candidate treatments
    """

    context = build_patient_context(
        encounter_id
    )

    candidates = get_candidates_from_context(
        context
    )

    candidate_records = build_candidate_records(
        context,
        candidates
    )

    return context, candidates, candidate_records


# ==========================================================
# DISPLAY RESULTS
# ==========================================================

def display_candidates(
    context,
    candidates
):

    print("=" * 70)
    print(
        "OBJECTIVE E2 - CANDIDATE TREATMENT GENERATION"
    )
    print("=" * 70)

    print(
        f"\nEncounter ID : "
        f"{context['encounter_id']}"
    )

    print(
        f"Disease      : "
        f"{context['disease_id']}"
    )

    print(
        f"Severity     : "
        f"{context['severity_id']}"
    )

    print(
        f"\nCandidate treatments: "
        f"{len(candidates)}"
    )

    if candidates.empty:

        print(
            "\nNo treatment mapping found."
        )

        return

    print(
        "\nCandidate set:"
    )

    display_columns = [
        "treatment_id",
        "priority",
        "first_line",
        "referral_required",
        "comments",
    ]

    print(
        candidates[
            display_columns
        ].to_string(
            index=False
        )
    )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    engine = get_engine()

    query = """
    SELECT encounter_id
    FROM patient_encounter
    ORDER BY encounter_id
    LIMIT 1
    """

    with engine.connect() as connection:

        result = connection.execute(
            text(query)
        )

        row = result.fetchone()

    if row is None:

        raise ValueError(
            "No encounters found in patient_encounter."
        )

    encounter_id = row[0]

    print(
        f"Testing encounter: "
        f"{encounter_id}"
    )

    context, candidates, records = (
        generate_candidates_for_encounter(
            encounter_id
        )
    )

    display_candidates(
        context,
        candidates
    )
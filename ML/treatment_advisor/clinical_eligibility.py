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
from .candidate_treatments import (
    get_candidates_from_context
)


# ==========================================================
# LOAD TREATMENT MASTER
# ==========================================================

def load_treatment_master():

    engine = get_engine()

    query = """
    SELECT
        treatment_id,
        treatment_name,
        treatment_category,
        treatment_type,
        route,
        inpatient_required,
        description
    FROM treatment_master
    ORDER BY treatment_id
    """

    with engine.connect() as connection:

        treatments = pd.read_sql(
            text(query),
            connection
        )

    return treatments


# ==========================================================
# CHECK SINGLE TREATMENT
# ==========================================================

def evaluate_treatment_eligibility(
    candidate,
    treatment_master
):
    """
    Evaluate the candidate using only knowledge
    explicitly represented in the current project database.

    This is a prototype eligibility layer.

    It does NOT claim to implement a complete
    medical contraindication system.
    """

    treatment_id = candidate[
        "treatment_id"
    ]

    matches = treatment_master[
        treatment_master["treatment_id"]
        == treatment_id
    ]

    safety_flags = []

    reasons = []

    eligible = True

    # ------------------------------------------------------
    # Treatment master existence
    # ------------------------------------------------------

    if matches.empty:

        eligible = False

        safety_flags.append(
            "MISSING_TREATMENT_MASTER_RECORD"
        )

        reasons.append(
            "Treatment is present in the disease/severity "
            "mapping but has no treatment master record."
        )

        return {
            "eligible": eligible,
            "eligibility_status": "INELIGIBLE",
            "safety_flags": safety_flags,
            "eligibility_reasons": reasons,
            "treatment_name": None,
            "treatment_category": None,
            "treatment_type": None,
            "route": None,
            "inpatient_required": None,
        }

    treatment = matches.iloc[0]

    # ------------------------------------------------------
    # Referral requirement
    # ------------------------------------------------------

    referral_required = candidate[
        "referral_required"
    ]

    if (
        str(referral_required).lower()
        in ["true", "yes", "1"]
    ):

        safety_flags.append(
            "REFERRAL_REQUIRED"
        )

        reasons.append(
            "Treatment mapping indicates that "
            "clinical referral is required."
        )

    # ------------------------------------------------------
    # Inpatient requirement
    # ------------------------------------------------------

    inpatient_required = treatment[
        "inpatient_required"
    ]

    if (
        str(inpatient_required).lower()
        in ["true", "yes", "1"]
    ):

        safety_flags.append(
            "INPATIENT_REQUIRED"
        )

        reasons.append(
            "Treatment master indicates that "
            "inpatient care is required."
        )

    # ------------------------------------------------------
    # Mapping comments
    # ------------------------------------------------------

    comments = candidate.get(
        "comments"
    )

    if (
        comments is not None
        and not pd.isna(comments)
        and str(comments).strip()
    ):

        reasons.append(
            f"Mapping note: {comments}"
        )

    # ------------------------------------------------------
    # Determine status
    # ------------------------------------------------------

    if not eligible:

        status = "INELIGIBLE"

    elif safety_flags:

        status = "ELIGIBLE_WITH_REVIEW"

    else:

        status = "ELIGIBLE"

    return {
        "eligible": eligible,
        "eligibility_status": status,
        "safety_flags": safety_flags,
        "eligibility_reasons": reasons,

        "treatment_name": treatment[
            "treatment_name"
        ],

        "treatment_category": treatment[
            "treatment_category"
        ],

        "treatment_type": treatment[
            "treatment_type"
        ],

        "route": treatment[
            "route"
        ],

        "inpatient_required": treatment[
            "inpatient_required"
        ],
    }


# ==========================================================
# EVALUATE ALL CANDIDATES
# ==========================================================

def evaluate_candidates(
    candidates,
    treatment_master
):

    evaluated = []

    for _, candidate in candidates.iterrows():

        evaluation = evaluate_treatment_eligibility(
            candidate,
            treatment_master
        )

        record = candidate.to_dict()

        record.update(
            evaluation
        )

        evaluated.append(
            record
        )

    if not evaluated:

        return pd.DataFrame()

    return pd.DataFrame(
        evaluated
    )


# ==========================================================
# E1 -> E2 -> E3 PIPELINE
# ==========================================================

def evaluate_encounter(
    encounter_id
):
    """
    Complete pipeline:

    encounter
       ↓
    E1 clinical context
       ↓
    E2 candidate generation
       ↓
    E3 clinical eligibility
    """

    context = build_patient_context(
        encounter_id
    )

    candidates = get_candidates_from_context(
        context
    )

    treatment_master = load_treatment_master()

    evaluated = evaluate_candidates(
        candidates,
        treatment_master
    )

    return (
        context,
        candidates,
        evaluated
    )


# ==========================================================
# DISPLAY
# ==========================================================

def display_eligibility(
    context,
    evaluated
):

    print("=" * 70)
    print(
        "OBJECTIVE E3 - CLINICAL ELIGIBILITY / SAFETY"
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
        f"\nCandidates evaluated: "
        f"{len(evaluated)}"
    )

    if evaluated.empty:

        print(
            "\nNo candidates available."
        )

        return

    print(
        "\nEligibility results:"
    )

    for _, row in evaluated.iterrows():

        print(
            "\n" + "-" * 70
        )

        print(
            f"Treatment ID       : "
            f"{row['treatment_id']}"
        )

        print(
            f"Treatment          : "
            f"{row['treatment_name']}"
        )

        print(
            f"Priority           : "
            f"{row['priority']}"
        )

        print(
            f"Eligible            : "
            f"{row['eligible']}"
        )

        print(
            f"Status              : "
            f"{row['eligibility_status']}"
        )

        print(
            f"Route               : "
            f"{row['route']}"
        )

        print(
            f"Inpatient required  : "
            f"{row['inpatient_required']}"
        )

        flags = row[
            "safety_flags"
        ]

        if flags:

            print(
                "Safety / review flags:"
            )

            for flag in flags:
                print(
                    f"  • {flag}"
                )

        else:

            print(
                "Safety / review flags: None"
            )

        reasons = row[
            "eligibility_reasons"
        ]

        if reasons:

            print(
                "Eligibility notes:"
            )

            for reason in reasons:
                print(
                    f"  • {reason}"
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

    context, candidates, evaluated = (
        evaluate_encounter(
            encounter_id
        )
    )

    display_eligibility(
        context,
        evaluated
    )
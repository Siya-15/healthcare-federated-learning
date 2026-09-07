import sys
import os

# ==========================================================
# PROJECT PATH
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)

import pandas as pd

from sqlalchemy import text

from database import get_engine

from .clinical_eligibility import evaluate_encounter


# ==========================================================
# E4 DATA DIRECTORY
# ==========================================================

E4_DATA_DIR = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "e4_data"
)

GUIDELINE_FILE = os.path.join(
    E4_DATA_DIR,
    "treatment_guideline_config.csv"
)

AVAILABILITY_FILE = os.path.join(
    E4_DATA_DIR,
    "hospital_treatment_availability.csv"
)

RESOURCE_FILE = os.path.join(
    E4_DATA_DIR,
    "treatment_resource_config.csv"
)


# ==========================================================
# EXPECTED SCHEMAS
# ==========================================================

GUIDELINE_COLUMNS = [
    "treatment_id",
    "guideline_status",
    "guideline_source_type",
    "guideline_note",
]

AVAILABILITY_COLUMNS = [
    "hospital_id",
    "treatment_id",
    "availability_status",
    "configuration_type",
    "availability_note",
]

RESOURCE_COLUMNS = [
    "treatment_id",
    "resource_tier",
    "cost_level",
    "configuration_type",
    "cost_note",
]


# ==========================================================
# LOAD E4 CONFIGURATION
# ==========================================================

def load_guideline_config():

    if not os.path.exists(GUIDELINE_FILE):

        raise FileNotFoundError(
            f"Guideline configuration not found: "
            f"{GUIDELINE_FILE}"
        )

    data = pd.read_csv(
        GUIDELINE_FILE
    )

    missing = [
        column
        for column in GUIDELINE_COLUMNS
        if column not in data.columns
    ]

    if missing:

        raise ValueError(
            "Guideline configuration is missing "
            f"columns: {missing}"
        )

    return data[GUIDELINE_COLUMNS].copy()


def load_availability_config():

    if not os.path.exists(
        AVAILABILITY_FILE
    ):

        raise FileNotFoundError(
            f"Availability configuration not found: "
            f"{AVAILABILITY_FILE}"
        )

    data = pd.read_csv(
        AVAILABILITY_FILE
    )

    missing = [
        column
        for column in AVAILABILITY_COLUMNS
        if column not in data.columns
    ]

    if missing:

        raise ValueError(
            "Availability configuration is missing "
            f"columns: {missing}"
        )

    return data[AVAILABILITY_COLUMNS].copy()


def load_resource_config():

    if not os.path.exists(
        RESOURCE_FILE
    ):

        raise FileNotFoundError(
            f"Resource configuration not found: "
            f"{RESOURCE_FILE}"
        )

    data = pd.read_csv(
        RESOURCE_FILE
    )

    missing = [
        column
        for column in RESOURCE_COLUMNS
        if column not in data.columns
    ]

    if missing:

        raise ValueError(
            "Resource configuration is missing "
            f"columns: {missing}"
        )

    return data[RESOURCE_COLUMNS].copy()


# ==========================================================
# VALIDATE CONFIGURATION
# ==========================================================

def validate_e4_configuration():

    guidelines = load_guideline_config()

    availability = load_availability_config()

    resources = load_resource_config()

    errors = []

    # ------------------------------------------------------
    # Duplicate guideline entries
    # ------------------------------------------------------

    duplicate_guidelines = (
        guidelines[
            guidelines.duplicated(
                subset=["treatment_id"],
                keep=False
            )
        ]
    )

    if not duplicate_guidelines.empty:

        errors.append(
            "Duplicate treatment IDs found in "
            "guideline configuration."
        )

    # ------------------------------------------------------
    # Duplicate resource entries
    # ------------------------------------------------------

    duplicate_resources = (
        resources[
            resources.duplicated(
                subset=["treatment_id"],
                keep=False
            )
        ]
    )

    if not duplicate_resources.empty:

        errors.append(
            "Duplicate treatment IDs found in "
            "resource configuration."
        )

    # ------------------------------------------------------
    # Duplicate hospital availability
    # ------------------------------------------------------

    duplicate_availability = (
        availability[
            availability.duplicated(
                subset=[
                    "hospital_id",
                    "treatment_id"
                ],
                keep=False
            )
        ]
    )

    if not duplicate_availability.empty:

        errors.append(
            "Duplicate hospital/treatment combinations "
            "found in availability configuration."
        )

    # ------------------------------------------------------
    # Allowed values
    # ------------------------------------------------------

    valid_guidelines = {
        "PROJECT_SUPPORTED",
        "REVIEW_REQUIRED",
        "NOT_CONFIGURED",
    }

    valid_availability = {
        "AVAILABLE",
        "LIMITED",
        "UNAVAILABLE",
        "UNKNOWN",
    }

    valid_resources = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "UNKNOWN",
    }

    invalid_guidelines = set(
        guidelines["guideline_status"].dropna()
    ) - valid_guidelines

    invalid_availability = set(
        availability["availability_status"].dropna()
    ) - valid_availability

    invalid_resources = set(
        resources["resource_tier"].dropna()
    ) - valid_resources

    if invalid_guidelines:

        errors.append(
            f"Invalid guideline statuses: "
            f"{invalid_guidelines}"
        )

    if invalid_availability:

        errors.append(
            f"Invalid availability statuses: "
            f"{invalid_availability}"
        )

    if invalid_resources:

        errors.append(
            f"Invalid resource tiers: "
            f"{invalid_resources}"
        )

    if errors:

        raise ValueError(
            "E4 configuration validation failed:\n"
            + "\n".join(
                f"- {error}"
                for error in errors
            )
        )

    return {
        "valid": True,
        "guideline_rows": len(guidelines),
        "availability_rows": len(availability),
        "resource_rows": len(resources),
    }


# ==========================================================
# GET GUIDELINE INFORMATION
# ==========================================================

def get_guideline_information(
    treatment_id,
    guideline_config
):

    matches = guideline_config[
        guideline_config["treatment_id"]
        == treatment_id
    ]

    if matches.empty:

        return {
            "guideline_status": "NOT_CONFIGURED",
            "guideline_source_type": "NOT_CONFIGURED",
            "guideline_note": (
                "No project guideline configuration "
                "exists for this treatment."
            ),
        }

    row = matches.iloc[0]

    return {
        "guideline_status": row[
            "guideline_status"
        ],

        "guideline_source_type": row[
            "guideline_source_type"
        ],

        "guideline_note": row[
            "guideline_note"
        ],
    }


# ==========================================================
# GET AVAILABILITY INFORMATION
# ==========================================================

def get_availability_information(
    hospital_id,
    treatment_id,
    availability_config
):

    matches = availability_config[
        (
            availability_config["hospital_id"]
            == hospital_id
        )
        &
        (
            availability_config["treatment_id"]
            == treatment_id
        )
    ]

    if matches.empty:

        return {
            "availability_status": "UNKNOWN",
            "configuration_type": "NOT_CONFIGURED",
            "availability_note": (
                "No hospital-specific availability "
                "configuration exists."
            ),
        }

    row = matches.iloc[0]

    return {
        "availability_status": row[
            "availability_status"
        ],

        "configuration_type": row[
            "configuration_type"
        ],

        "availability_note": row[
            "availability_note"
        ],
    }


# ==========================================================
# GET RESOURCE INFORMATION
# ==========================================================

def get_resource_information(
    treatment_id,
    resource_config
):

    matches = resource_config[
        resource_config["treatment_id"]
        == treatment_id
    ]

    if matches.empty:

        return {
            "resource_tier": "UNKNOWN",
            "cost_level": "UNKNOWN",
            "cost_note": (
                "No resource/cost configuration "
                "exists for this treatment."
            ),
        }

    row = matches.iloc[0]

    return {
        "resource_tier": row[
            "resource_tier"
        ],

        "cost_level": row[
            "cost_level"
        ],

        "cost_note": row[
            "cost_note"
        ],
    }


# ==========================================================
# ENRICH ONE CANDIDATE
# ==========================================================

def enrich_treatment(
    candidate,
    hospital_id,
    guideline_config,
    availability_config,
    resource_config
):

    treatment_id = candidate[
        "treatment_id"
    ]

    record = candidate.to_dict()

    guideline = get_guideline_information(
        treatment_id,
        guideline_config
    )

    availability = get_availability_information(
        hospital_id,
        treatment_id,
        availability_config
    )

    resource = get_resource_information(
        treatment_id,
        resource_config
    )

    record.update(guideline)

    record.update(availability)

    record.update(resource)

    record["hospital_id"] = hospital_id

    return record


# ==========================================================
# E4 ENRICHMENT
# ==========================================================

def enrich_candidates(
    e3_results,
    hospital_id
):

    if e3_results.empty:

        return pd.DataFrame()

    guideline_config = (
        load_guideline_config()
    )

    availability_config = (
        load_availability_config()
    )

    resource_config = (
        load_resource_config()
    )

    enriched_records = []

    for _, candidate in e3_results.iterrows():

        # Only E3-eligible treatments proceed.
        if not bool(candidate["eligible"]):
            continue

        record = enrich_treatment(
            candidate,
            hospital_id,
            guideline_config,
            availability_config,
            resource_config
        )

        enriched_records.append(
            record
        )

    if not enriched_records:

        return pd.DataFrame()

    return pd.DataFrame(
        enriched_records
    )


# ==========================================================
# COMPLETE E1 -> E2 -> E3 -> E4 PIPELINE
# ==========================================================

def evaluate_e4(
    encounter_id,
    hospital_id
):

    context, candidates, e3_results = (
        evaluate_encounter(
            encounter_id
        )
    )

    enriched = enrich_candidates(
        e3_results,
        hospital_id
    )

    return (
        context,
        e3_results,
        enriched
    )


# ==========================================================
# DISPLAY
# ==========================================================

def display_e4(
    context,
    enriched
):

    print("=" * 70)

    print(
        "OBJECTIVE E4 - GUIDELINES / "
        "AVAILABILITY / COST"
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
        f"\nE4 candidates: "
        f"{len(enriched)}"
    )

    if enriched.empty:

        print(
            "\nNo eligible candidates available."
        )

        return

    for _, row in enriched.iterrows():

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
            f"Guideline status   : "
            f"{row['guideline_status']}"
        )

        print(
            f"Availability       : "
            f"{row['availability_status']}"
        )

        print(
            f"Resource tier      : "
            f"{row['resource_tier']}"
        )

        print(
            f"Cost level         : "
            f"{row['cost_level']}"
        )

        print(
            "\nGuideline note:"
        )

        print(
            f"  {row['guideline_note']}"
        )

        print(
            "\nAvailability note:"
        )

        print(
            f"  {row['availability_note']}"
        )

        print(
            "\nCost/resource note:"
        )

        print(
            f"  {row['cost_note']}"
        )


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    print(
        "Validating E4 configuration..."
    )

    validation = (
        validate_e4_configuration()
    )

    print(
        f"Guideline rows    : "
        f"{validation['guideline_rows']}"
    )

    print(
        f"Availability rows : "
        f"{validation['availability_rows']}"
    )

    print(
        f"Resource rows     : "
        f"{validation['resource_rows']}"
    )

    print(
        "Configuration     : VALID"
    )

    engine = get_engine()

    query = """
    SELECT
        encounter_id,
        hospital_id
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
            "No encounters found."
        )

    encounter_id = row[0]
    hospital_id = row[1]

    print(
        f"\nTesting encounter: "
        f"{encounter_id}"
    )

    print(
        f"Hospital: "
        f"{hospital_id}"
    )

    context, e3_results, enriched = (
        evaluate_e4(
            encounter_id,
            hospital_id
        )
    )

    display_e4(
        context,
        enriched
    )
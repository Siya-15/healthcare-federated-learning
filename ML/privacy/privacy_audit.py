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
from sqlalchemy import text

from database import get_engine


# ==========================================================
# PRIVACY CLASSIFICATION
# ==========================================================

PRIVACY_CLASSIFICATION = {

    # Direct identifiers
    "patient_id":
        "DIRECT_IDENTIFIER",

    "encounter_id":
        "LINKABLE_IDENTIFIER",

    # Quasi-identifiers
    "hospital_id":
        "QUASI_IDENTIFIER",

    "visit_timestamp":
        "QUASI_IDENTIFIER",

    "age":
        "QUASI_IDENTIFIER",

    "gender":
        "QUASI_IDENTIFIER",

    "occupation":
        "QUASI_IDENTIFIER",

    "district":
        "QUASI_IDENTIFIER",

    "state":
        "QUASI_IDENTIFIER",

    # Sensitive clinical information
    "temperature":
        "SENSITIVE_CLINICAL",

    "heart_rate":
        "SENSITIVE_CLINICAL",

    "respiratory_rate":
        "SENSITIVE_CLINICAL",

    "systolic_bp":
        "SENSITIVE_CLINICAL",

    "diastolic_bp":
        "SENSITIVE_CLINICAL",

    "spo2":
        "SENSITIVE_CLINICAL",

    "disease_id":
        "SENSITIVE_CLINICAL",

    "severity_id":
        "SENSITIVE_CLINICAL",

    "symptom_id":
        "SENSITIVE_CLINICAL",

    "symptom_text":
        "SENSITIVE_CLINICAL",

    "symptom_source":
        "SENSITIVE_CLINICAL",

    "onset_stage":
        "SENSITIVE_CLINICAL",

    "symptom_onset_days":
        "SENSITIVE_CLINICAL",

    "travel_history":
        "SENSITIVE_CLINICAL",

    "vaccination_status":
        "SENSITIVE_CLINICAL",

    "admission_status":
        "SENSITIVE_CLINICAL",

    "visit_type":
        "SENSITIVE_CLINICAL",

    "discharge_status":
        "SENSITIVE_CLINICAL",

    "recovery_days":
        "SENSITIVE_CLINICAL",

    "treatment_id":
        "SENSITIVE_CLINICAL",

    "treatment_notes":
        "SENSITIVE_CLINICAL",

    "complication_id":
        "SENSITIVE_CLINICAL",

    "identified_timestamp":
        "SENSITIVE_CLINICAL",

    "notes":
        "SENSITIVE_CLINICAL",

    # Clinical decision metadata
    "recommended_by_ai":
        "DECISION_METADATA",

    "accepted_by_doctor":
        "DECISION_METADATA",

    "treatment_origin":
        "DECISION_METADATA",

    "treatment_sequence":
        "DECISION_METADATA",

    "administered":
        "DECISION_METADATA",

    "is_primary":
        "DECISION_METADATA",

    "resolved":
        "DECISION_METADATA",
}


# ==========================================================
# TABLES TO AUDIT
# ==========================================================

TABLES = [
    "patient_encounter",
    "encounter_symptoms",
    "encounter_treatments",
    "encounter_complications",
]


# ==========================================================
# GET SCHEMA
# ==========================================================

def get_table_schema(table_name):

    engine = get_engine()

    query = """
    SELECT
        column_name,
        data_type
    FROM information_schema.columns
    WHERE
        table_name = :table_name
    ORDER BY ordinal_position
    """

    with engine.connect() as connection:

        df = pd.read_sql(
            text(query),
            connection,
            params={
                "table_name": table_name
            }
        )

    return df


# ==========================================================
# CLASSIFY COLUMN
# ==========================================================

def classify_column(column_name):

    return PRIVACY_CLASSIFICATION.get(
        column_name,
        "OTHER"
    )


# ==========================================================
# BUILD PRIVACY AUDIT
# ==========================================================

def build_privacy_audit():

    results = []

    for table in TABLES:

        schema = get_table_schema(table)

        for _, row in schema.iterrows():

            column = row["column_name"]

            classification = (
                classify_column(column)
            )

            results.append({

                "table_name":
                    table,

                "column_name":
                    column,

                "data_type":
                    row["data_type"],

                "privacy_classification":
                    classification
            })

    return pd.DataFrame(results)


# ==========================================================
# SUMMARY
# ==========================================================

def print_summary(audit):

    print("=" * 70)
    print("OBJECTIVE A - PRIVACY AUDIT")
    print("=" * 70)

    print(
        "\nTotal columns audited:",
        len(audit)
    )

    print(
        "\nPrivacy classification:"
    )

    summary = (
        audit[
            "privacy_classification"
        ]
        .value_counts()
    )

    print(
        summary.to_string()
    )

    print(
        "\nDirect / linkable identifiers:"
    )

    identifiers = audit[
        audit[
            "privacy_classification"
        ].isin([
            "DIRECT_IDENTIFIER",
            "LINKABLE_IDENTIFIER"
        ])
    ]

    print(
        identifiers[
            [
                "table_name",
                "column_name",
                "privacy_classification"
            ]
        ]
        .to_string(index=False)
    )

    print(
        "\nQuasi-identifiers:"
    )

    quasi = audit[
        audit[
            "privacy_classification"
        ]
        == "QUASI_IDENTIFIER"
    ]

    print(
        quasi[
            [
                "table_name",
                "column_name"
            ]
        ]
        .to_string(index=False)
    )

    print(
        "\nSensitive clinical fields:"
    )

    sensitive = audit[
        audit[
            "privacy_classification"
        ]
        == "SENSITIVE_CLINICAL"
    ]

    print(
        sensitive[
            [
                "table_name",
                "column_name"
            ]
        ]
        .to_string(index=False)
    )


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    audit = build_privacy_audit()

    print_summary(audit)

    output_file = (
        "privacy_audit.csv"
    )

    audit.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nAudit saved to: "
        f"{output_file}"
    )
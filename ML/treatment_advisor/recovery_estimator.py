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
# LOAD HISTORICAL RECOVERY DATA
# ==========================================================

def load_recovery_data():

    engine = get_engine()

    query = """
    SELECT
        pe.disease_id,
        pe.severity_id,
        pe.recovery_days,
        et.treatment_id

    FROM patient_encounter pe

    INNER JOIN encounter_treatments et
        ON pe.encounter_id = et.encounter_id

    WHERE
        et.administered = TRUE
        AND pe.recovery_days IS NOT NULL
    """

    with engine.connect() as connection:

        df = pd.read_sql(
            text(query),
            connection
        )

    return df


# ==========================================================
# BUILD RECOVERY ESTIMATES
# ==========================================================

def build_recovery_estimates():

    df = load_recovery_data()

    estimates = (
        df
        .groupby(
            [
                "disease_id",
                "severity_id",
                "treatment_id",
            ]
        )
        .agg(
            expected_recovery_days=(
                "recovery_days",
                "mean"
            ),
            historical_cases=(
                "recovery_days",
                "count"
            )
        )
        .reset_index()
    )

    estimates[
        "expected_recovery_days"
    ] = (
        estimates[
            "expected_recovery_days"
        ]
        .round(2)
    )

    return estimates


# ==========================================================
# GET ESTIMATE
# ==========================================================

def get_recovery_estimate(
    disease_id,
    severity_id,
    treatment_id
):

    estimates = build_recovery_estimates()

    result = estimates[
        (
            estimates["disease_id"]
            == disease_id
        )
        &
        (
            estimates["severity_id"]
            == severity_id
        )
        &
        (
            estimates["treatment_id"]
            == treatment_id
        )
    ]

    return result


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    disease_id = "D004"
    severity_id = "SV001"

    estimates = build_recovery_estimates()

    result = estimates[
        (
            estimates["disease_id"]
            == disease_id
        )
        &
        (
            estimates["severity_id"]
            == severity_id
        )
    ]

    print("=" * 60)
    print("OBJECTIVE E - EXPECTED RECOVERY ESTIMATION")
    print("=" * 60)

    print(
        f"\nDisease: {disease_id}"
    )

    print(
        f"Severity: {severity_id}"
    )

    print(
        "\nHistorical recovery estimates:"
    )

    if result.empty:

        print(
            "No historical data available."
        )

    else:

        print(
            result.to_string(
                index=False
            )
        )
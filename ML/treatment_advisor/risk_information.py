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
# LOAD COMPLICATION INFORMATION
# ==========================================================

def load_complication_data():

    engine = get_engine()

    query = """
    SELECT
        dcm.disease_id,
        dcm.complication_id,
        dcm.frequency,
        dcm.severity_id,
        cm.complication_name,
        cm.body_system,
        cm.description

    FROM disease_complication_mapping dcm

    INNER JOIN complication_master cm
        ON dcm.complication_id = cm.complication_id
    """

    with engine.connect() as connection:

        df = pd.read_sql(
            text(query),
            connection
        )

    return df


# ==========================================================
# GET RISKS FOR PATIENT
# ==========================================================

def get_risk_information(
    disease_id,
    severity_id
):

    data = load_complication_data()

    risks = data[
        (
            data["disease_id"]
            == disease_id
        )
        &
        (
            data["severity_id"]
            == severity_id
        )
    ].copy()

    return risks


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    disease_id = "D004"
    severity_id = "SV002"

    risks = get_risk_information(
        disease_id,
        severity_id
    )

    print("=" * 60)
    print("OBJECTIVE E - COMPLICATION / RISK INFORMATION")
    print("=" * 60)

    print(
        f"\nDisease: {disease_id}"
    )

    print(
        f"Severity: {severity_id}"
    )

    print(
        f"\nPotential complications: "
        f"{len(risks)}"
    )

    if risks.empty:

        print(
            "\nNo mapped complications found."
        )

    else:

        print(
            "\nRisk information:"
        )

        print(
            risks[
                [
                    "complication_id",
                    "complication_name",
                    "body_system",
                    "frequency",
                    "severity_id",
                    "description",
                ]
            ]
            .to_string(index=False)
        )
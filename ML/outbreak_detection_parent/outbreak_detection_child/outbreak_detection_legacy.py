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
import numpy as np

from database import get_engine
from sqlalchemy import text


# ==========================================================
# CONFIGURATION
# ==========================================================

HOSPITALS = [
    f"H{i:03d}"
    for i in range(1, 11)
]


# ==========================================================
# LOAD ALL HOSPITAL DATA
# ==========================================================

def load_all_data():

    engine = get_engine()

    query = """
    SELECT
        encounter_id,
        hospital_id,
        visit_timestamp,
        disease_id,
        severity_id
    FROM patient_encounter
    """

    with engine.connect() as connection:

        df = pd.read_sql(
            text(query),
            connection
        )

    return df

# ==========================================================
# PREPARE TIME DATA
# ==========================================================

def prepare_time_data(df):

    df["timestamp"] = pd.to_datetime(
        df["visit_timestamp"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["timestamp"]
    )

    df["week"] = (
        df["timestamp"]
        .dt.to_period("W")
        .apply(lambda x: x.start_time)
    )

    return df


# ==========================================================
# CALCULATE WEEKLY CASE COUNTS
# ==========================================================

def calculate_weekly_cases(df):

    weekly_cases = (
        df
        .groupby(
            [
                "week",
                "hospital_id",
            ]
        )
        .size()
        .reset_index(
            name="case_count"
        )
    )

    return weekly_cases


# ==========================================================
# DETECT ABNORMAL INCREASE
# ==========================================================

def detect_increases(weekly_cases):

    results = []

    for hospital_id in HOSPITALS:

        hospital_data = (
            weekly_cases[
                weekly_cases["hospital_id"]
                == hospital_id
            ]
            .sort_values("week")
            .copy()
        )

        if len(hospital_data) < 2:
            continue

        hospital_data["previous_cases"] = (
            hospital_data["case_count"]
            .shift(1)
        )

        hospital_data["growth_rate"] = (
            (
                hospital_data["case_count"]
                - hospital_data["previous_cases"]
            )
            /
            hospital_data["previous_cases"]
            .replace(0, np.nan)
        )

        hospital_data["alert_level"] = (
            hospital_data["growth_rate"]
            .apply(assign_alert_level)
        )

        results.append(
            hospital_data
        )

    if not results:
        return pd.DataFrame()

    return pd.concat(
        results,
        ignore_index=True
    )

# ==========================================================
# ASSIGN OUTBREAK ALERT LEVEL
# ==========================================================

def assign_alert_level(growth_rate):

    if pd.isna(growth_rate):
        return "GREEN"

    if growth_rate < 0.25:
        return "GREEN"

    elif growth_rate < 0.50:
        return "YELLOW"

    elif growth_rate < 1.00:
        return "ORANGE"

    else:
        return "RED"

# ==========================================================
# CROSS-HOSPITAL OUTBREAK ASSESSMENT
# ==========================================================

def assess_cross_hospital_outbreak(results):

    latest = (
        results
        .sort_values("week")
        .groupby("hospital_id")
        .tail(1)
    )

    total_hospitals = len(latest)

    red_hospitals = (
        latest["alert_level"] == "RED"
    ).sum()

    orange_or_above = (
        latest["alert_level"]
        .isin(["ORANGE", "RED"])
        .sum()
    )

    affected_percentage = (
        orange_or_above
        / total_hospitals
        * 100
    )

    # ------------------------------------------------------
    # Overall alert
    # ------------------------------------------------------

    if affected_percentage >= 75:

        overall_alert = "RED"

    elif affected_percentage >= 50:

        overall_alert = "ORANGE"

    elif affected_percentage >= 25:

        overall_alert = "YELLOW"

    else:

        overall_alert = "GREEN"

    potential_outbreak = (
        affected_percentage >= 50
    )

    return {
        "total_hospitals": total_hospitals,
        "red_hospitals": int(red_hospitals),
        "affected_percentage": affected_percentage,
        "overall_alert": overall_alert,
        "potential_outbreak": potential_outbreak,
    }


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("EPIDEMIC / PANDEMIC SURVEILLANCE")
    print("=" * 60)

    # ------------------------------------------------------
    # Load
    # ------------------------------------------------------

    df = load_all_data()

    print(
        f"\nTotal encounters: {len(df)}"
    )

    # ------------------------------------------------------
    # Prepare timestamps
    # ------------------------------------------------------

    df = prepare_time_data(df)

    print(
        f"Time range: "
        f"{df['timestamp'].min()} → "
        f"{df['timestamp'].max()}"
    )

    # ------------------------------------------------------
    # Weekly surveillance
    # ------------------------------------------------------

    weekly_cases = calculate_weekly_cases(
        df
    )

    # ------------------------------------------------------
    # Growth detection
    # ------------------------------------------------------

    results = detect_increases(
        weekly_cases
    )

    # ------------------------------------------------------
    # Display
    # ------------------------------------------------------

    print(
        "\nWeekly surveillance results:"
    )

    print(
        results
        .tail(20)
        .to_string(index=False)
    )

    print(
        "\nCurrent hospital alert levels:"
    )

    latest = (
        results
        .sort_values("week")
        .groupby("hospital_id")
        .tail(1)
    )

    print(
        latest[
            [
                "hospital_id",
                "case_count",
                "previous_cases",
                "growth_rate",
                "alert_level",
            ]
        ]
        .to_string(index=False)
    )

    # ------------------------------------------------------
    # CROSS-HOSPITAL ASSESSMENT
    # ------------------------------------------------------

    assessment = assess_cross_hospital_outbreak(
        results
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "CROSS-HOSPITAL OUTBREAK ASSESSMENT"
    )

    print(
        "=" * 60
    )

    print(
        f"\nHospitals monitored: "
        f"{assessment['total_hospitals']}"
    )

    print(
        f"Hospitals with RED alerts: "
        f"{assessment['red_hospitals']}"
    )

    print(
        f"Affected hospitals: "
        f"{assessment['affected_percentage']:.1f}%"
    )

    print(
        f"\nOverall alert level: "
        f"{assessment['overall_alert']}"
    )

    print(
        f"Potential outbreak signal: "
        f"{assessment['potential_outbreak']}"
    )

    # ------------------------------------------------------
    # Save
    # ------------------------------------------------------

    weekly_cases.to_csv(
        "weekly_hospital_cases.csv",
        index=False
    )

    results.to_csv(
        "outbreak_surveillance.csv",
        index=False
    )

    print(
        "\nResults saved:"
    )

    print(
        "  weekly_hospital_cases.csv"
    )

    print(
        "  outbreak_surveillance.csv"
    )
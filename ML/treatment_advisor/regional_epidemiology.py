"""
E5 - Regional Epidemiological Context

Provides hospital-level epidemiological context for the treatment advisor.

This module:
- Uses the patient's hospital as the regional unit.
- Compares the recent 7-day period with the preceding 7-day period.
- Calculates disease activity and disease share.
- Calculates disease severity distribution.
- Calculates recent symptom prevalence.
- Produces a descriptive trend without making outbreak/causal claims.

This is a prototype/project epidemiology layer.
It does NOT independently diagnose disease, declare an outbreak,
or modify treatment-success probabilities.
"""

from datetime import timedelta

import pandas as pd
from sqlalchemy import text

from database import get_engine


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RECENT_WINDOW_DAYS = 7
PREVIOUS_WINDOW_DAYS = 7

SEVERITY_LEVELS = ["SV001", "SV002", "SV003"]


# ---------------------------------------------------------------------------
# Database loading
# ---------------------------------------------------------------------------

def load_encounter_data():
    """
    Load the encounter-level data required for epidemiological analysis.
    """

    engine = get_engine()

    query = text("""
        SELECT
            encounter_id,
            hospital_id,
            visit_timestamp,
            disease_id,
            severity_id
        FROM patient_encounter
        WHERE visit_timestamp IS NOT NULL
    """)

    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    if df.empty:
        raise ValueError("No encounter data available.")

    df["visit_timestamp"] = pd.to_datetime(df["visit_timestamp"])

    return df


def load_symptom_data():
    """
    Load encounter-symptom associations.
    """

    engine = get_engine()

    query = text("""
        SELECT
            encounter_id,
            symptom_id,
            symptom_text
        FROM encounter_symptoms
        WHERE encounter_id IS NOT NULL
    """)

    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    return df


# ---------------------------------------------------------------------------
# Patient encounter context
# ---------------------------------------------------------------------------

def load_encounter_context(encounter_id):
    """
    Retrieve hospital, date and disease information for an encounter.
    """

    engine = get_engine()

    query = text("""
        SELECT
            encounter_id,
            hospital_id,
            visit_timestamp,
            disease_id
        FROM patient_encounter
        WHERE encounter_id = :encounter_id
    """)

    with engine.connect() as connection:
        df = pd.read_sql(
            query,
            connection,
            params={"encounter_id": encounter_id}
        )

    if df.empty:
        raise ValueError(
            f"Encounter not found: {encounter_id}"
        )

    row = df.iloc[0]

    return {
        "encounter_id": row["encounter_id"],
        "hospital_id": row["hospital_id"],
        "reference_date": pd.Timestamp(row["visit_timestamp"]),
        "disease_id": row["disease_id"],
    }


# ---------------------------------------------------------------------------
# Window calculations
# ---------------------------------------------------------------------------

def build_windows(reference_date):
    """
    Build recent and previous epidemiological windows.

    Recent:
        reference_date - 6 days through reference_date

    Previous:
        reference_date - 13 days through reference_date - 7 days

    The windows are inclusive and non-overlapping.
    """

    reference_date = pd.Timestamp(reference_date).normalize()

    recent_start = reference_date - timedelta(
        days=RECENT_WINDOW_DAYS - 1
    )

    previous_end = recent_start - timedelta(days=1)

    previous_start = previous_end - timedelta(
        days=PREVIOUS_WINDOW_DAYS - 1
    )

    return {
        "recent_start": recent_start,
        "recent_end": reference_date,
        "previous_start": previous_start,
        "previous_end": previous_end,
    }


def filter_window(df, hospital_id, start_date, end_date):
    """
    Filter encounters to one hospital and inclusive date window.
    """

    dates = pd.to_datetime(df["visit_timestamp"]).dt.normalize()

    mask = (
        (df["hospital_id"] == hospital_id)
        & (dates >= pd.Timestamp(start_date))
        & (dates <= pd.Timestamp(end_date))
    )

    return df.loc[mask].copy()


# ---------------------------------------------------------------------------
# Disease activity
# ---------------------------------------------------------------------------

def calculate_disease_activity(
    recent_df,
    previous_df,
    disease_id
):
    """
    Calculate disease case counts and disease share for both periods.
    """

    recent_total = len(recent_df)
    previous_total = len(previous_df)

    recent_cases = int(
        (recent_df["disease_id"] == disease_id).sum()
    )

    previous_cases = int(
        (previous_df["disease_id"] == disease_id).sum()
    )

    recent_share = (
        (recent_cases / recent_total) * 100
        if recent_total > 0
        else 0.0
    )

    previous_share = (
        (previous_cases / previous_total) * 100
        if previous_total > 0
        else 0.0
    )

    return {
        "recent_total_encounters": recent_total,
        "recent_disease_cases": recent_cases,
        "recent_disease_share": round(recent_share, 2),

        "previous_total_encounters": previous_total,
        "previous_disease_cases": previous_cases,
        "previous_disease_share": round(previous_share, 2),

        "case_change": recent_cases - previous_cases,
        "share_change": round(
            recent_share - previous_share,
            2
        ),
    }


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------

def calculate_trend(
    recent_cases,
    previous_cases
):
    """
    Classify descriptive disease-count trend.

    This is NOT an outbreak detector.
    """

    if previous_cases == 0:

        if recent_cases == 0:
            return {
                "direction": "NO_CHANGE",
                "percentage_change": 0.0,
            }

        return {
            "direction": "NEW_ACTIVITY",
            "percentage_change": None,
        }

    percentage_change = (
        (recent_cases - previous_cases)
        / previous_cases
    ) * 100

    # Small changes are treated as stable.
    if abs(percentage_change) < 10:
        direction = "STABLE"
    elif percentage_change > 0:
        direction = "INCREASING"
    else:
        direction = "DECREASING"

    return {
        "direction": direction,
        "percentage_change": round(
            percentage_change,
            2
        ),
    }


# ---------------------------------------------------------------------------
# Severity distribution
# ---------------------------------------------------------------------------

def calculate_severity_distribution(
    recent_df,
    disease_id
):
    """
    Calculate severity distribution for the selected disease
    during the recent epidemiological window.
    """

    disease_df = recent_df[
        recent_df["disease_id"] == disease_id
    ]

    total = len(disease_df)

    distribution = {}

    for severity_id in SEVERITY_LEVELS:

        count = int(
            (disease_df["severity_id"] == severity_id).sum()
        )

        percentage = (
            (count / total) * 100
            if total > 0
            else 0.0
        )

        distribution[severity_id] = {
            "count": count,
            "percentage": round(
                percentage,
                2
            ),
        }

    return distribution


# ---------------------------------------------------------------------------
# Symptom prevalence
# ---------------------------------------------------------------------------

def calculate_symptom_prevalence(
    recent_df,
    disease_id,
    symptom_df
):
    """
    Calculate the most prevalent symptoms among recent cases
    of the selected disease.

    Prevalence is calculated using unique encounters rather than
    raw symptom-record counts.
    """

    disease_encounters = recent_df[
        recent_df["disease_id"] == disease_id
    ][["encounter_id"]]

    if disease_encounters.empty or symptom_df.empty:
        return []

    disease_symptoms = symptom_df.merge(
        disease_encounters,
        on="encounter_id",
        how="inner"
    )

    if disease_symptoms.empty:
        return []

    total_cases = disease_encounters["encounter_id"].nunique()

    grouped = (
        disease_symptoms
        .groupby(
            ["symptom_id", "symptom_text"],
            dropna=False
        )["encounter_id"]
        .nunique()
        .reset_index(name="case_count")
    )

    grouped["prevalence"] = (
        grouped["case_count"] / total_cases
    ) * 100

    grouped = grouped.sort_values(
        ["case_count", "symptom_id"],
        ascending=[False, True]
    )

    results = []

    for _, row in grouped.head(10).iterrows():

        results.append({
            "symptom_id": row["symptom_id"],
            "symptom_text": row["symptom_text"],
            "case_count": int(row["case_count"]),
            "prevalence": round(
                float(row["prevalence"]),
                2
            ),
        })

    return results


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

def build_interpretation(
    disease_id,
    activity,
    trend
):
    """
    Generate a descriptive epidemiological interpretation.

    Deliberately avoids outbreak, causality or treatment claims.
    """

    recent_cases = activity["recent_disease_cases"]
    recent_share = activity["recent_disease_share"]
    direction = trend["direction"]

    if direction == "INCREASING":
        trend_text = (
            "Disease activity is higher than in the preceding "
            "7-day period."
        )

    elif direction == "DECREASING":
        trend_text = (
            "Disease activity is lower than in the preceding "
            "7-day period."
        )

    elif direction == "NEW_ACTIVITY":
        trend_text = (
            "Disease cases are present in the recent period "
            "but were absent in the preceding 7-day period."
        )

    elif direction == "NO_CHANGE":
        trend_text = (
            "No cases were observed in either comparison period."
        )

    else:
        trend_text = (
            "Disease activity is relatively stable compared "
            "with the preceding 7-day period."
        )

    return (
        f"{disease_id}: {recent_cases} recent cases, representing "
        f"{recent_share:.2f}% of hospital encounters. "
        f"{trend_text}"
    )


# ---------------------------------------------------------------------------
# Main E5 function
# ---------------------------------------------------------------------------

def get_regional_epidemiology(encounter_id):
    """
    Generate the complete E5 epidemiological context
    for an encounter.
    """

    context = load_encounter_context(encounter_id)

    encounter_df = load_encounter_data()
    symptom_df = load_symptom_data()

    windows = build_windows(
        context["reference_date"]
    )

    recent_df = filter_window(
        encounter_df,
        context["hospital_id"],
        windows["recent_start"],
        windows["recent_end"]
    )

    previous_df = filter_window(
        encounter_df,
        context["hospital_id"],
        windows["previous_start"],
        windows["previous_end"]
    )

    activity = calculate_disease_activity(
        recent_df,
        previous_df,
        context["disease_id"]
    )

    trend = calculate_trend(
        activity["recent_disease_cases"],
        activity["previous_disease_cases"]
    )

    severity_distribution = (
        calculate_severity_distribution(
            recent_df,
            context["disease_id"]
        )
    )

    symptom_prevalence = (
        calculate_symptom_prevalence(
            recent_df,
            context["disease_id"],
            symptom_df
        )
    )

    interpretation = build_interpretation(
        context["disease_id"],
        activity,
        trend
    )

    return {
        "encounter_id": context["encounter_id"],
        "hospital_id": context["hospital_id"],
        "disease_id": context["disease_id"],

        "reference_date": (
            context["reference_date"].strftime("%Y-%m-%d")
        ),

        "recent_window": {
            "start": windows["recent_start"].strftime("%Y-%m-%d"),
            "end": windows["recent_end"].strftime("%Y-%m-%d"),
        },

        "previous_window": {
            "start": windows["previous_start"].strftime("%Y-%m-%d"),
            "end": windows["previous_end"].strftime("%Y-%m-%d"),
        },

        "disease_activity": activity,

        "trend": trend,

        "severity_distribution": severity_distribution,

        "symptom_prevalence": symptom_prevalence,

        "interpretation": interpretation,

        "data_source": (
            "Synthetic project hospital encounter database"
        ),

        "disclaimer": (
            "Descriptive epidemiological context for clinical "
            "decision support. This output does not independently "
            "diagnose disease, establish causality, or declare an "
            "outbreak."
        ),
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_regional_epidemiology(result):
    """
    Validate the structure and basic integrity of an E5 result.
    """

    required_fields = [
        "encounter_id",
        "hospital_id",
        "disease_id",
        "reference_date",
        "recent_window",
        "previous_window",
        "disease_activity",
        "trend",
        "severity_distribution",
        "symptom_prevalence",
        "interpretation",
        "data_source",
        "disclaimer",
    ]

    missing = [
        field
        for field in required_fields
        if field not in result
    ]

    if missing:
        raise ValueError(
            f"Missing E5 fields: {missing}"
        )

    activity = result["disease_activity"]

    if activity["recent_total_encounters"] < 0:
        raise ValueError(
            "Recent encounter count cannot be negative."
        )

    if activity["previous_total_encounters"] < 0:
        raise ValueError(
            "Previous encounter count cannot be negative."
        )

    if not 0 <= activity["recent_disease_share"] <= 100:
        raise ValueError(
            "Recent disease share must be between 0 and 100."
        )

    if not 0 <= activity["previous_disease_share"] <= 100:
        raise ValueError(
            "Previous disease share must be between 0 and 100."
        )

    return True


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display_regional_epidemiology(result):
    """
    Human-readable E5 output.
    """

    print("=" * 80)
    print("E5 - REGIONAL EPIDEMIOLOGICAL CONTEXT")
    print("=" * 80)

    print(f"Encounter       : {result['encounter_id']}")
    print(f"Hospital        : {result['hospital_id']}")
    print(f"Disease         : {result['disease_id']}")
    print(f"Reference date  : {result['reference_date']}")

    print("\nRECENT WINDOW")
    print("-" * 40)

    recent = result["disease_activity"]

    print(
        f"Total encounters : "
        f"{recent['recent_total_encounters']}"
    )

    print(
        f"Disease cases    : "
        f"{recent['recent_disease_cases']}"
    )

    print(
        f"Disease share    : "
        f"{recent['recent_disease_share']:.2f}%"
    )

    print("\nPREVIOUS WINDOW")
    print("-" * 40)

    print(
        f"Total encounters : "
        f"{recent['previous_total_encounters']}"
    )

    print(
        f"Disease cases    : "
        f"{recent['previous_disease_cases']}"
    )

    print(
        f"Disease share    : "
        f"{recent['previous_disease_share']:.2f}%"
    )

    print("\nTREND")
    print("-" * 40)

    trend = result["trend"]

    print(
        f"Direction        : "
        f"{trend['direction']}"
    )

    print(
        f"Case change      : "
        f"{recent['case_change']}"
    )

    if trend["percentage_change"] is None:
        print("Percentage change: N/A")
    else:
        print(
            f"Percentage change: "
            f"{trend['percentage_change']:.2f}%"
        )

    print("\nSEVERITY DISTRIBUTION")
    print("-" * 40)

    for severity_id, values in (
        result["severity_distribution"].items()
    ):
        print(
            f"{severity_id}: "
            f"{values['count']} cases "
            f"({values['percentage']:.2f}%)"
        )

    print("\nTOP SYMPTOMS")
    print("-" * 40)

    for symptom in result["symptom_prevalence"]:

        print(
            f"{symptom['symptom_text']}: "
            f"{symptom['case_count']} cases "
            f"({symptom['prevalence']:.2f}%)"
        )

    print("\nINTERPRETATION")
    print("-" * 40)
    print(result["interpretation"])

    print("\nDISCLAIMER")
    print("-" * 40)
    print(result["disclaimer"])


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print("Testing E5 Regional Epidemiological Context...\n")

    engine = get_engine()

    sample_query = text("""
        SELECT encounter_id
        FROM patient_encounter
        ORDER BY visit_timestamp
        LIMIT 1
    """)

    with engine.connect() as connection:
        sample = pd.read_sql(
            sample_query,
            connection
        )

    if sample.empty:
        raise ValueError(
            "No encounters available for E5 test."
        )

    test_encounter = sample.iloc[0]["encounter_id"]

    print(f"Test encounter: {test_encounter}\n")

    result = get_regional_epidemiology(
        test_encounter
    )

    validate_regional_epidemiology(result)

    display_regional_epidemiology(result)

    print("\n" + "=" * 80)
    print("E5 VALIDATION: PASSED")
    print("=" * 80)
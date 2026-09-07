import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import text

# Project root
# synthetic_generator/
# └── ML/
#     └── outbreak_detection_parent/
#         └── outbreak_detection_child/
#             └── symptom_surveillance.py

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Same-folder module
CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from database import get_engine

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

OUTPUT_DIR = CURRENT_DIR
OUTPUT_FILE = OUTPUT_DIR / "symptom_weekly_surveillance.csv"

# -------------------------------------------------------------------
# Load encounter + symptom data
# -------------------------------------------------------------------

def load_symptom_data():
    engine = get_engine()

    query = text("""
        SELECT
            es.encounter_id,
            pe.hospital_id,
            pe.visit_timestamp,
            es.symptom_id
        FROM encounter_symptoms es
        JOIN patient_encounter pe
            ON es.encounter_id = pe.encounter_id
        WHERE pe.visit_timestamp IS NOT NULL
          AND es.symptom_id IS NOT NULL
    """)

    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    return df


# -------------------------------------------------------------------
# Load symptom master
# -------------------------------------------------------------------

def load_symptom_master():
    engine = get_engine()

    query = text("""
        SELECT
            symptom_id,
            symptom_name
        FROM symptom_master
        ORDER BY symptom_id
    """)

    with engine.connect() as connection:
        symptoms = pd.read_sql(query, connection)

    return symptoms


# -------------------------------------------------------------------
# Prepare time data
# -------------------------------------------------------------------

def prepare_time_data(df):
    df = df.copy()

    df["visit_timestamp"] = pd.to_datetime(
        df["visit_timestamp"],
        errors="coerce"
    )

    df = df.dropna(subset=["visit_timestamp"])

    # Monday-based weekly surveillance period
    df["week"] = (
        df["visit_timestamp"]
        .dt.to_period("W")
        .apply(lambda x: x.start_time)
    )

    return df


# -------------------------------------------------------------------
# Calculate weekly symptom cases
# -------------------------------------------------------------------

def calculate_weekly_symptom_cases(df):
    weekly = (
        df.groupby(
            ["week", "hospital_id", "symptom_id"],
            as_index=False
        )
        .agg(
            case_count=("encounter_id", "nunique")
        )
    )

    return weekly


# -------------------------------------------------------------------
# Calculate total hospital cases
# -------------------------------------------------------------------

def calculate_hospital_totals(df):
    totals = (
        df.groupby(
            ["week", "hospital_id"],
            as_index=False
        )
        .agg(
            hospital_total_cases=("encounter_id", "nunique")
        )
    )

    return totals


# -------------------------------------------------------------------
# Calculate growth
# -------------------------------------------------------------------

def calculate_growth(df):
    df = df.sort_values(
        ["hospital_id", "symptom_id", "week"]
    ).copy()

    df["previous_cases"] = (
        df.groupby(
            ["hospital_id", "symptom_id"]
        )["case_count"]
        .shift(1)
    )

    def growth_rate(row):
        previous = row["previous_cases"]
        current = row["case_count"]

        if pd.isna(previous):
            return np.nan

        # If previous week had zero cases:
        if previous == 0:
            if current > 0:
                return np.inf
            return 0.0

        return ((current - previous) / previous) * 100

    df["growth_rate"] = df.apply(
        growth_rate,
        axis=1
    )

    return df


# -------------------------------------------------------------------
# Add incidence proportion
# -------------------------------------------------------------------

def calculate_incidence(df):
    df = df.copy()

    df["incidence_proportion"] = (
        df["case_count"] /
        df["hospital_total_cases"]
    )

    return df


# -------------------------------------------------------------------
# Main B2 pipeline
# -------------------------------------------------------------------

def run_b2():
    print("=" * 80)
    print("B2 - SYMPTOM-LEVEL SURVEILLANCE")
    print("=" * 80)

    # Load data
    df = load_symptom_data()

    print(f"Total symptom records: {len(df)}")

    if df.empty:
        print("No symptom data found.")
        return None

    # Prepare timestamps
    df = prepare_time_data(df)

    # Load symptom names
    symptom_master = load_symptom_master()

    # Weekly symptom counts
    weekly = calculate_weekly_symptom_cases(df)

    # Hospital weekly totals
    hospital_totals = calculate_hospital_totals(df)

    # Growth
    weekly = calculate_growth(weekly)

    # Add hospital totals
    weekly = weekly.merge(
        hospital_totals,
        on=["week", "hospital_id"],
        how="left"
    )

    # Incidence
    weekly = calculate_incidence(weekly)

    # Add symptom names
    weekly = weekly.merge(
        symptom_master,
        on="symptom_id",
        how="left"
    )

    # Arrange columns
    weekly = weekly[
        [
            "week",
            "hospital_id",
            "symptom_id",
            "symptom_name",
            "case_count",
            "previous_cases",
            "growth_rate",
            "hospital_total_cases",
            "incidence_proportion",
        ]
    ]

    weekly = weekly.sort_values(
        ["week", "hospital_id", "symptom_id"]
    )

    # Save
    weekly.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print(f"Output rows: {len(weekly)}")
    print(f"Output saved: {OUTPUT_FILE}")

    print()
    print("Sample:")
    print(weekly.head(15).to_string(index=False))

    print()
    print("=" * 80)
    print("B2 COMPLETE")
    print("=" * 80)

    return weekly


if __name__ == "__main__":
    run_b2()
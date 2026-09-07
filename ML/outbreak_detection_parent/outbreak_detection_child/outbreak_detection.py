"""
Objective B — Epidemic/Pandemic Surveillance foundation.

Phase 1 preserves the current weekly hospital surveillance behavior while
turning it into reusable, database-driven functions. Later phases will add
disease/symptom surveillance, historical baselines, temporal intelligence,
spatial propagation, Objective A integration, severity, composite risk,
continuous updates, and controlled validation.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import text

# Project root:
# synthetic_generator/
# └── ML/
#     └── outbreak_detection_parent/
#         └── outbreak_detection_child/
#             └── outbreak_detection.py
PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Same-folder module
CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from database import get_engine
from disease_surveillance import build_disease_surveillance

HOSPITALS = [f"H{i:03d}" for i in range(1, 11)]


def load_all_data(engine=None) -> pd.DataFrame:
    """Load the encounter fields required by the current B foundation.

    PostgreSQL is the source of truth. An engine may be injected for tests.
    """
    engine = engine or get_engine()
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
        return pd.read_sql(text(query), connection)


def prepare_time_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize timestamps and add calendar-week start."""
    result = df.copy()
    result["timestamp"] = pd.to_datetime(
        result["visit_timestamp"], errors="coerce"
    )
    result = result.dropna(subset=["timestamp"]).copy()
    result["week"] = (
        result["timestamp"]
        .dt.to_period("W")
        .apply(lambda x: x.start_time)
    )
    return result


def calculate_weekly_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Current prototype: total encounters by hospital and week."""
    return (
        df.groupby(["week", "hospital_id"])
        .size()
        .reset_index(name="case_count")
    )


def assign_alert_level(growth_rate) -> str:
    """Preserve the existing growth-based alert thresholds."""
    if pd.isna(growth_rate):
        return "GREEN"
    if growth_rate < 0.25:
        return "GREEN"
    if growth_rate < 0.50:
        return "YELLOW"
    if growth_rate < 1.00:
        return "ORANGE"
    return "RED"


def detect_increases(
    weekly_cases: pd.DataFrame,
    hospitals: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Calculate week-over-week growth and hospital alert level."""
    hospitals = hospitals or HOSPITALS
    results = []

    for hospital_id in hospitals:
        hospital_data = (
            weekly_cases[weekly_cases["hospital_id"] == hospital_id]
            .sort_values("week")
            .copy()
        )
        if len(hospital_data) < 2:
            continue

        hospital_data["previous_cases"] = (
            hospital_data["case_count"].shift(1)
        )
        hospital_data["growth_rate"] = (
            (
                hospital_data["case_count"]
                - hospital_data["previous_cases"]
            )
            / hospital_data["previous_cases"].replace(0, np.nan)
        )
        hospital_data["alert_level"] = (
            hospital_data["growth_rate"].apply(assign_alert_level)
        )
        results.append(hospital_data)

    if not results:
        return pd.DataFrame()
    return pd.concat(results, ignore_index=True)


def assess_cross_hospital_outbreak(
    results: pd.DataFrame,
    hospitals: Optional[list[str]] = None,
) -> dict:
    """Preserve the current latest-hospital cross-hospital rule."""
    if results.empty:
        return {
            "total_hospitals": 0,
            "red_hospitals": 0,
            "affected_percentage": 0.0,
            "overall_alert": "GREEN",
            "potential_outbreak": False,
        }

    latest = (
        results.sort_values("week")
        .groupby("hospital_id")
        .tail(1)
    )
    total_hospitals = len(latest)
    red_hospitals = int((latest["alert_level"] == "RED").sum())
    orange_or_above = int(
        latest["alert_level"].isin(["ORANGE", "RED"]).sum()
    )
    affected_percentage = (
        orange_or_above / total_hospitals * 100
        if total_hospitals else 0.0
    )

    if affected_percentage >= 75:
        overall_alert = "RED"
    elif affected_percentage >= 50:
        overall_alert = "ORANGE"
    elif affected_percentage >= 25:
        overall_alert = "YELLOW"
    else:
        overall_alert = "GREEN"

    return {
        "total_hospitals": total_hospitals,
        "red_hospitals": red_hospitals,
        "affected_percentage": affected_percentage,
        "overall_alert": overall_alert,
        "potential_outbreak": affected_percentage >= 50,
    }


def run_foundation(engine=None) -> dict:
    """Run the current B foundation without requiring the CLI."""
    raw = load_all_data(engine=engine)
    prepared = prepare_time_data(raw)
    weekly_cases = calculate_weekly_cases(prepared)
    surveillance = detect_increases(weekly_cases)
    assessment = assess_cross_hospital_outbreak(surveillance)

    # B1: disease-specific surveillance uses the same database-loaded encounters.
    disease_surveillance = build_disease_surveillance(raw)

    return {
        "raw_data": raw,
        "prepared_data": prepared,
        "weekly_cases": weekly_cases,
        "surveillance": surveillance,
        "assessment": assessment,
        "disease_surveillance": disease_surveillance,
    }


def save_foundation_outputs(
    weekly_cases: pd.DataFrame,
    surveillance: pd.DataFrame,
    output_dir: str | Path = ".",
) -> tuple[Path, Path]:
    """Optional CSV reporting; CSVs are not the source of truth."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    weekly_path = output_dir / "weekly_hospital_cases.csv"
    surveillance_path = output_dir / "outbreak_surveillance.csv"
    weekly_cases.to_csv(weekly_path, index=False)
    surveillance.to_csv(surveillance_path, index=False)
    return weekly_path, surveillance_path


def main() -> None:
    print("=" * 60)
    print("EPIDEMIC / PANDEMIC SURVEILLANCE — PHASE 1")
    print("=" * 60)

    result = run_foundation()
    raw = result["raw_data"]
    prepared = result["prepared_data"]
    weekly_cases = result["weekly_cases"]
    surveillance = result["surveillance"]
    assessment = result["assessment"]
    disease_surveillance = result["disease_surveillance"]

    print(f"\nTotal encounters: {len(raw)}")
    if not prepared.empty:
        print(
            f"Time range: {prepared['timestamp'].min()} → "
            f"{prepared['timestamp'].max()}"
        )

    print("\nWeekly surveillance results:")
    print(surveillance.tail(20).to_string(index=False))

    if not surveillance.empty:
        latest = (
            surveillance.sort_values("week")
            .groupby("hospital_id")
            .tail(1)
        )
        print("\nCurrent hospital alert levels:")
        print(
            latest[
                [
                    "hospital_id",
                    "case_count",
                    "previous_cases",
                    "growth_rate",
                    "alert_level",
                ]
            ].to_string(index=False)
        )

    print("\n" + "=" * 60)
    print("CROSS-HOSPITAL OUTBREAK ASSESSMENT")
    print("=" * 60)
    print(f"\nHospitals monitored: {assessment['total_hospitals']}")
    print(f"Hospitals with RED alerts: {assessment['red_hospitals']}")
    print(f"Affected hospitals: {assessment['affected_percentage']:.1f}%")
    print(f"\nOverall alert level: {assessment['overall_alert']}")
    print(f"Potential outbreak signal: {assessment['potential_outbreak']}")

    weekly_path, surveillance_path = save_foundation_outputs(
        weekly_cases, surveillance
    )

    disease_path = Path("disease_weekly_surveillance.csv")
    disease_surveillance.to_csv(disease_path, index=False)

    print("\nOptional reporting outputs saved:")
    print(f"  {weekly_path}")
    print(f"  {surveillance_path}")
    print(f"  {disease_path}")


if __name__ == "__main__":
    main()

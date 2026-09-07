"""
Objective B1 — Disease-specific surveillance.

Calculates disease incidence at Hospital × Time × Disease level.

Design principles:
- PostgreSQL remains the source of truth.
- No static CSV is required as input.
- The function accepts a DataFrame so it can also be reused by validation/tests.
- Daily aggregation is the primary representation; weekly aggregation is derived
  from the same encounter-level data.
- Missing disease IDs are retained as UNKNOWN rather than silently discarded.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def prepare_disease_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize encounter data for disease surveillance."""
    required = {"hospital_id", "visit_timestamp", "disease_id"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required disease surveillance columns: {sorted(missing)}"
        )

    result = df.copy()

    result["timestamp"] = pd.to_datetime(
        result["visit_timestamp"],
        errors="coerce",
    )

    result = result.dropna(subset=["timestamp"]).copy()

    result["hospital_id"] = (
        result["hospital_id"]
        .astype("string")
        .str.strip()
    )

    result["disease_id"] = (
        result["disease_id"]
        .astype("string")
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
        .fillna("UNKNOWN")
    )

    result["day"] = result["timestamp"].dt.normalize()

    result["week"] = (
        result["timestamp"]
        .dt.to_period("W")
        .apply(lambda x: x.start_time)
    )

    return result


def calculate_daily_disease_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Return Hospital × Day × Disease encounter counts."""
    prepared = prepare_disease_data(df)

    return (
        prepared
        .groupby(
            ["day", "hospital_id", "disease_id"],
            dropna=False,
        )
        .size()
        .reset_index(name="case_count")
        .sort_values(
            ["hospital_id", "disease_id", "day"]
        )
        .reset_index(drop=True)
    )


def calculate_weekly_disease_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Return Hospital × Week × Disease encounter counts."""
    prepared = prepare_disease_data(df)

    return (
        prepared
        .groupby(
            ["week", "hospital_id", "disease_id"],
            dropna=False,
        )
        .size()
        .reset_index(name="case_count")
        .sort_values(
            ["hospital_id", "disease_id", "week"]
        )
        .reset_index(drop=True)
    )


def calculate_disease_growth(
    weekly_cases: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate week-over-week disease growth within each hospital."""
    required = {
        "week",
        "hospital_id",
        "disease_id",
        "case_count",
    }
    missing = required - set(weekly_cases.columns)

    if missing:
        raise ValueError(
            f"Missing required weekly disease columns: {sorted(missing)}"
        )

    result = weekly_cases.copy()
    result = result.sort_values(
        ["hospital_id", "disease_id", "week"]
    ).reset_index(drop=True)

    group_cols = ["hospital_id", "disease_id"]

    result["previous_cases"] = (
        result.groupby(group_cols)["case_count"].shift(1)
    )

    # A previous value of zero means percentage growth is undefined.
    # We keep it as NaN rather than creating artificial infinite growth.
    result["growth_rate"] = (
        (
            result["case_count"] - result["previous_cases"]
        )
        / result["previous_cases"].replace(0, pd.NA)
    )

    return result


def calculate_disease_incidence(
    weekly_cases: pd.DataFrame,
) -> pd.DataFrame:
    """Add hospital-level incidence proportion.

    Denominator = all encounters recorded for that hospital/week.
    This lets us distinguish disease growth from general hospital volume growth.
    """
    required = {
        "week",
        "hospital_id",
        "disease_id",
        "case_count",
    }
    missing = required - set(weekly_cases.columns)

    if missing:
        raise ValueError(
            f"Missing required weekly disease columns: {sorted(missing)}"
        )

    result = weekly_cases.copy()

    hospital_totals = (
        result.groupby(
            ["week", "hospital_id"],
            as_index=False,
        )["case_count"]
        .sum()
        .rename(columns={"case_count": "hospital_total_cases"})
    )

    result = result.merge(
        hospital_totals,
        on=["week", "hospital_id"],
        how="left",
    )

    result["incidence_proportion"] = (
        result["case_count"]
        / result["hospital_total_cases"].replace(0, pd.NA)
    )

    return result


def build_disease_surveillance(df: pd.DataFrame) -> pd.DataFrame:
    """Build the complete B1 weekly disease surveillance table."""
    weekly = calculate_weekly_disease_cases(df)
    weekly = calculate_disease_growth(weekly)
    weekly = calculate_disease_incidence(weekly)

    return weekly.sort_values(
        ["week", "hospital_id", "disease_id"]
    ).reset_index(drop=True)

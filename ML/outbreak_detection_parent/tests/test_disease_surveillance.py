import pandas as pd

from outbreak_detection.disease_surveillance import (
    calculate_daily_disease_cases,
    calculate_weekly_disease_cases,
    calculate_disease_growth,
    build_disease_surveillance,
)


def sample_data():
    return pd.DataFrame({
        "encounter_id": ["E1", "E2", "E3", "E4", "E5"],
        "hospital_id": ["H001", "H001", "H001", "H001", "H002"],
        "visit_timestamp": [
            "2026-08-03 10:00",
            "2026-08-03 11:00",
            "2026-08-04 10:00",
            "2026-08-10 10:00",
            "2026-08-10 10:00",
        ],
        "disease_id": ["D001", "D001", "D002", "D001", "D001"],
    })


def test_daily_disease_counts():
    result = calculate_daily_disease_cases(sample_data())
    assert result["case_count"].sum() == 5


def test_weekly_disease_counts():
    result = calculate_weekly_disease_cases(sample_data())
    d001_h001 = result[
        (result["hospital_id"] == "H001")
        & (result["disease_id"] == "D001")
    ]
    assert d001_h001["case_count"].tolist() == [2, 1]


def test_growth_is_calculated_within_hospital_and_disease():
    weekly = calculate_weekly_disease_cases(sample_data())
    result = calculate_disease_growth(weekly)

    row = result[
        (result["hospital_id"] == "H001")
        & (result["disease_id"] == "D001")
    ].sort_values("week").iloc[-1]

    assert row["previous_cases"] == 2
    assert row["growth_rate"] == -0.5


def test_full_disease_surveillance():
    result = build_disease_surveillance(sample_data())
    assert "incidence_proportion" in result.columns
    assert "growth_rate" in result.columns
    assert "disease_id" in result.columns

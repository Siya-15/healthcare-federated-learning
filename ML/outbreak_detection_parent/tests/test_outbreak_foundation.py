import pandas as pd

from outbreak_detection.outbreak_detection import (
    prepare_time_data,
    calculate_weekly_cases,
    detect_increases,
    assess_cross_hospital_outbreak,
)

def test_weekly_aggregation():
    df = pd.DataFrame({
        "hospital_id": ["H001", "H001", "H001", "H002"],
        "visit_timestamp": [
            "2026-08-03 10:00:00",
            "2026-08-04 10:00:00",
            "2026-08-10 10:00:00",
            "2026-08-10 10:00:00",
        ],
    })
    prepared = prepare_time_data(df)
    weekly = calculate_weekly_cases(prepared)
    assert weekly["case_count"].sum() == 4

def test_growth_alert_thresholds():
    weekly = pd.DataFrame({
        "week": pd.to_datetime(["2026-08-03", "2026-08-10"]),
        "hospital_id": ["H001", "H001"],
        "case_count": [10, 20],
    })
    result = detect_increases(weekly, hospitals=["H001"])
    assert result.iloc[-1]["growth_rate"] == 1.0
    assert result.iloc[-1]["alert_level"] == "RED"

def test_empty_cross_hospital_result():
    result = assess_cross_hospital_outbreak(pd.DataFrame())
    assert result["overall_alert"] == "GREEN"
    assert result["potential_outbreak"] is False

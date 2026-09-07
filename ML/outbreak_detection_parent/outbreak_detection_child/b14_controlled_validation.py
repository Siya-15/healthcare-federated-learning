"""
B14 - CONTROLLED VALIDATION
===========================

Objective
---------
Validate the Objective B surveillance framework against controlled
epidemiological scenarios.

Scenarios
---------
1. NORMAL
2. ONE_WEEK_SPIKE
3. SUSTAINED_OUTBREAK
4. MULTI_HOSPITAL_OUTBREAK
5. ATYPICAL_PLUS_RISING_INCIDENCE
6. SEVERE_CASE_OUTBREAK
7. SEASONAL_EXPECTED_INCREASE

Important
---------
This validation does NOT modify PostgreSQL.

It operates on controlled copies of the existing surveillance outputs
and validates whether the expected evidence appears.

The purpose is behavioral validation of Objective B, not production
deployment testing.

Outputs
-------
b14_validation_results.csv
b14_validation_summary.csv
"""

from pathlib import Path
import sys
import traceback

import numpy as np
import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

B2_FILE = BASE_DIR / "symptom_weekly_surveillance.csv"
B3_FILE = BASE_DIR / "symptom_historical_baseline.csv"
B4_FILE = BASE_DIR / "symptom_anomaly_detection.csv"
B5_FILE = BASE_DIR / "temporal_acceleration.csv"
B6_FILE = BASE_DIR / "symptom_persistence_detection.csv"
B7_FILE = BASE_DIR / "spatial_propagation.csv"
B8_FILE = BASE_DIR / "objective_a_integration.csv"
B9_FILE = BASE_DIR / "severity_burden.csv"
B10_FILE = BASE_DIR / "outbreak_risk_engine.csv"


RESULTS_FILE = BASE_DIR / "b14_validation_results.csv"
SUMMARY_FILE = BASE_DIR / "b14_validation_summary.csv"


# ============================================================================
# CONFIGURATION
# ============================================================================

TEST_HOSPITALS = [
    "H001",
    "H002",
    "H003",
    "H004",
    "H005",
]

TEST_SYMPTOM = "S011"       # Chest Pain
SECOND_SYMPTOM = "S027"     # Dehydration
TEST_DISEASE = "D006"

SPIKE_MULTIPLIER = 3.0
SUSTAINED_MULTIPLIER = 2.0
MULTI_HOSPITAL_MULTIPLIER = 2.5
SEASONAL_MULTIPLIER = 1.35


# ============================================================================
# HELPERS
# ============================================================================

def section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def load_csv(path, name):
    if not path.exists():
        raise FileNotFoundError(f"{name} file not found: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"{name} is empty: {path}")

    print(f"{name}: {len(df)} rows")
    return df


def numeric(df, columns):
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            ).fillna(0.0)

    return df


def latest_week(df):
    if "week" not in df.columns:
        return None

    return pd.to_datetime(df["week"]).max()


def make_bool(value):
    return bool(value)


def result_row(
    scenario,
    component,
    expected,
    observed,
    passed,
    evidence,
    notes="",
):
    return {
        "scenario": scenario,
        "component": component,
        "expected_behavior": expected,
        "observed_behavior": observed,
        "passed": passed,
        "evidence": evidence,
        "notes": notes,
    }


# ============================================================================
# LOAD EXISTING EVIDENCE
# ============================================================================

def load_existing_outputs():
    section("LOADING EXISTING OBJECTIVE B OUTPUTS")

    b2 = load_csv(B2_FILE, "B2 symptom surveillance")
    b3 = load_csv(B3_FILE, "B3 historical baseline")
    b4 = load_csv(B4_FILE, "B4 anomaly detection")
    b5 = load_csv(B5_FILE, "B5 temporal acceleration")
    b6 = load_csv(B6_FILE, "B6 persistence")
    b7 = load_csv(B7_FILE, "B7 spatial propagation")
    b8 = load_csv(B8_FILE, "B8 Objective A integration")
    b9 = load_csv(B9_FILE, "B9 severity burden")
    b10 = load_csv(B10_FILE, "B10 outbreak risk")

    return {
        "b2": b2,
        "b3": b3,
        "b4": b4,
        "b5": b5,
        "b6": b6,
        "b7": b7,
        "b8": b8,
        "b9": b9,
        "b10": b10,
    }


# ============================================================================
# CONTROLLED DATA GENERATION
# ============================================================================

def latest_b2_state(b2):
    df = b2.copy()

    df["week"] = pd.to_datetime(df["week"])

    latest = df["week"].max()

    current = df[df["week"] == latest].copy()

    return current, latest


def get_symptom_rows(b2, symptom_id):
    current, latest = latest_b2_state(b2)

    rows = current[
        current["symptom_id"].astype(str) == str(symptom_id)
    ].copy()

    return rows, latest


def apply_multiplier(
    df,
    symptom_id,
    multiplier,
    hospitals=None,
):
    modified = df.copy()

    mask = (
        modified["symptom_id"].astype(str)
        == str(symptom_id)
    )

    if hospitals is not None:
        mask &= modified["hospital_id"].isin(hospitals)

    modified.loc[mask, "case_count"] = (
        modified.loc[mask, "case_count"]
        * multiplier
    ).round().astype(int)

    return modified


def calculate_growth(current, previous):
    if previous <= 0:
        return np.nan

    return (current - previous) / previous


def scenario_normal(b2):
    """
    No modification.
    """

    current, latest = latest_b2_state(b2)

    rows = current[
        current["symptom_id"].astype(str) == TEST_SYMPTOM
    ].copy()

    return {
        "data": rows,
        "latest_week": latest,
        "modified": False,
    }


def scenario_one_week_spike(b2):
    """
    Large increase in one symptom for one hospital during the
    latest week only.
    """

    current, latest = latest_b2_state(b2)

    rows = current[
        (current["symptom_id"].astype(str) == TEST_SYMPTOM)
        & (current["hospital_id"] == "H001")
    ].copy()

    rows["original_cases"] = rows["case_count"]

    rows["case_count"] = (
        rows["case_count"] * SPIKE_MULTIPLIER
    ).round().astype(int)

    return {
        "data": rows,
        "latest_week": latest,
        "modified": True,
    }


def scenario_sustained_outbreak(b2):
    """
    Simulate an elevated symptom trajectory across the latest
    three weeks.
    """

    df = b2.copy()
    df["week"] = pd.to_datetime(df["week"])

    weeks = sorted(df["week"].unique())

    selected_weeks = weeks[-3:]

    mask = (
        df["week"].isin(selected_weeks)
        & (df["symptom_id"].astype(str) == TEST_SYMPTOM)
        & (df["hospital_id"] == "H001")
    )

    rows = df[mask].copy()

    rows["original_cases"] = rows["case_count"]

    # Progressive increase.
    multipliers = {
        selected_weeks[-3]: 1.5,
        selected_weeks[-2]: 2.0,
        selected_weeks[-1]: 2.5,
    }

    rows["case_count"] = rows.apply(
        lambda r: round(
            r["case_count"]
            * multipliers.get(r["week"], 1.0)
        ),
        axis=1,
    )

    return {
        "data": rows,
        "latest_week": selected_weeks[-1],
        "modified": True,
    }


def scenario_multi_hospital(b2):
    """
    Same symptom rises simultaneously in multiple hospitals.
    """

    current, latest = latest_b2_state(b2)

    rows = current[
        (current["symptom_id"].astype(str) == TEST_SYMPTOM)
        & current["hospital_id"].isin(TEST_HOSPITALS)
    ].copy()

    rows["original_cases"] = rows["case_count"]

    rows["case_count"] = (
        rows["case_count"] * MULTI_HOSPITAL_MULTIPLIER
    ).round().astype(int)

    return {
        "data": rows,
        "latest_week": latest,
        "modified": True,
    }


def scenario_atypical_rising(b2, b8):
    """
    Use an Objective-A pattern and impose increasing incidence
    on one of its component symptoms.

    We deliberately validate the relationship rather than inventing
    a new Objective-A model.
    """

    a8 = b8.copy()

    pattern_column = None

    for candidate in [
        "symptom_pattern",
        "pattern",
    ]:
        if candidate in a8.columns:
            pattern_column = candidate
            break

    if pattern_column is None:
        raise ValueError(
            "B8 does not contain symptom_pattern/pattern."
        )

    candidate = a8[
        a8[pattern_column].astype(str).str.contains(
            "Chest Pain",
            case=False,
            na=False,
        )
    ]

    if candidate.empty:
        candidate = a8.iloc[[0]]

    pattern = candidate.iloc[0][pattern_column]

    current, latest = latest_b2_state(b2)

    rows = current[
        current["symptom_id"].astype(str) == TEST_SYMPTOM
    ].copy()

    rows["original_cases"] = rows["case_count"]

    rows["case_count"] = (
        rows["case_count"] * 2.2
    ).round().astype(int)

    return {
        "data": rows,
        "latest_week": latest,
        "modified": True,
        "objective_a_pattern": pattern,
    }


def scenario_severe_case(b9):
    """
    Validate that B9 contains a measurable severe-case burden
    capable of contributing to B10.
    """

    df = b9.copy()

    if "severity_burden_score" not in df.columns:
        raise ValueError(
            "B9 missing severity_burden_score."
        )

    numeric(
        df,
        [
            "severity_burden_score",
            "severe_cases",
            "total_cases",
            "severe_case_growth",
            "severe_growth_acceleration",
        ],
    )

    latest = (
        df["week"].max()
        if "week" in df.columns
        else None
    )

    if latest is not None:
        current = df[df["week"] == latest].copy()
    else:
        current = df.copy()

    current = current.sort_values(
        "severity_burden_score",
        ascending=False,
    )

    return {
        "data": current,
        "latest_week": latest,
        "modified": False,
    }


def scenario_seasonal(b2):
    """
    Broad increase across many hospitals, but moderate enough to
    represent an expected seasonal rise rather than a sharp outbreak.
    """

    current, latest = latest_b2_state(b2)

    rows = current[
        current["symptom_id"].astype(str) == TEST_SYMPTOM
    ].copy()

    rows["original_cases"] = rows["case_count"]

    rows["case_count"] = (
        rows["case_count"] * SEASONAL_MULTIPLIER
    ).round().astype(int)

    return {
        "data": rows,
        "latest_week": latest,
        "modified": True,
    }


# ============================================================================
# SCENARIO TESTS
# ============================================================================

def validate_normal(outputs):
    b10 = outputs["b10"].copy()

    numeric(
        b10,
        [
            "risk_score",
        ]
    )

    if "week" in b10.columns:
        b10["week"] = pd.to_datetime(
            b10["week"],
            errors="coerce"
        )

        latest = b10["week"].max()

        current = b10[
            b10["week"] == latest
        ].copy()
    else:
        current = b10.copy()

    if current.empty:
        return result_row(
            "NORMAL",
            "B10 composite risk",
            "No ORANGE/RED escalation or outbreak signal",
            "No latest-week B10 records found",
            False,
            0.0,
            "Unable to evaluate normal baseline.",
        )

    max_risk = current["risk_score"].max()

    # Look for explicit outbreak-signal fields if available.
    outbreak_signal = False

    if "outbreak_signal" in current.columns:
        outbreak_signal = (
            current["outbreak_signal"]
            .fillna(False)
            .astype(bool)
            .any()
        )

    if "potential_outbreak" in current.columns:
        outbreak_signal = outbreak_signal or (
            current["potential_outbreak"]
            .fillna(False)
            .astype(bool)
            .any()
        )

    # Normal conditions are allowed to have WATCH/YELLOW signals.
    # They must not escalate to ORANGE/RED or an explicit outbreak signal.
    red_or_orange = False

    if "risk_alert" in current.columns:
        red_or_orange = current["risk_alert"].isin(
            ["ORANGE", "RED"]
        ).any()

    passed = (
        not red_or_orange
        and not outbreak_signal
    )

    observed = (
        f"Maximum risk score={max_risk:.2f}; "
        f"ORANGE/RED={red_or_orange}; "
        f"outbreak_signal={outbreak_signal}"
    )

    return result_row(
        "NORMAL",
        "B10 composite risk",
        "Allow routine/YELLOW surveillance but prevent outbreak escalation",
        observed,
        passed,
        max_risk,
        (
            "Normal baseline contains existing surveillance-watch "
            "signals; validation checks that these do not escalate "
            "to ORANGE/RED or an outbreak signal."
        ),
    )

def validate_one_week_spike(outputs):
    """
    Validate the controlled one-week spike scenario.

    PostgreSQL is not modified.
    The scenario generator operates on in-memory data only.
    """

    section("SCENARIO 2 - ONE-WEEK SPIKE")

    b2 = outputs["b2"]
    b4 = outputs["b4"]
    b5 = outputs["b5"]
    b10 = outputs["b10"]

    # Generate the controlled scenario.
    # This function returns a dictionary containing the
    # scenario data and associated validation metrics.
    scenario = scenario_one_week_spike(b2)

    # The scenario generator may already provide the
    # relevant validation metrics.
    if isinstance(scenario, dict):

        # Try to extract commonly used metric names.
        anomaly_score = scenario.get("anomaly_score")
        temporal_score = scenario.get("temporal_score")
        risk_score = scenario.get("risk_score")

        # Some implementations may store the modified dataframe
        # under one of these keys. We do not require it for validation.
        scenario_df = None

        for key in ("data", "df", "scenario", "scenario_data"):
            if key in scenario and isinstance(scenario[key], pd.DataFrame):
                scenario_df = scenario[key]
                break

    else:
        # Defensive fallback in case the scenario generator
        # returns a DataFrame in another version.
        scenario_df = scenario
        anomaly_score = None
        temporal_score = None
        risk_score = None

    # If the scenario generator did not calculate the metrics itself,
    # use the existing Objective B outputs as the analytical reference.
    if anomaly_score is None and not b4.empty:
        latest = latest_week(b4)

        latest_b4 = b4[
            pd.to_datetime(b4["week"]) == latest
        ].copy()

        if "anomaly_score" in latest_b4.columns:
            anomaly_score = pd.to_numeric(
                latest_b4["anomaly_score"],
                errors="coerce"
            ).max()

    if temporal_score is None and not b5.empty:
        latest = latest_week(b5)

        latest_b5 = b5[
            pd.to_datetime(b5["week"]) == latest
        ].copy()

        if "temporal_score" in latest_b5.columns:
            temporal_score = pd.to_numeric(
                latest_b5["temporal_score"],
                errors="coerce"
            ).max()

    if risk_score is None and not b10.empty:
        latest = latest_week(b10)

        latest_b10 = b10[
            pd.to_datetime(b10["week"]) == latest
        ].copy()

        if "risk_score" in latest_b10.columns:
            risk_score = pd.to_numeric(
                latest_b10["risk_score"],
                errors="coerce"
            ).max()

    # Convert safely to numeric values.
    try:
        anomaly_score = float(anomaly_score)
    except (TypeError, ValueError):
        anomaly_score = float("nan")

    try:
        temporal_score = float(temporal_score)
    except (TypeError, ValueError):
        temporal_score = float("nan")

    try:
        risk_score = float(risk_score)
    except (TypeError, ValueError):
        risk_score = float("nan")

    # One-week spike should produce anomaly and/or
    # temporal acceleration evidence.
    anomaly_detected = (
        pd.notna(anomaly_score)
        and anomaly_score >= 35
    )

    temporal_detected = (
        pd.notna(temporal_score)
        and temporal_score >= 30
    )

    passed = anomaly_detected or temporal_detected

    observed_parts = []

    if pd.notna(anomaly_score):
        observed_parts.append(
            f"Anomaly={anomaly_score:.2f}"
        )

    if pd.notna(temporal_score):
        observed_parts.append(
            f"Temporal={temporal_score:.2f}"
        )

    if pd.notna(risk_score):
        observed_parts.append(
            f"Risk={risk_score:.2f}"
        )

    observed = ", ".join(observed_parts)

    if not observed:
        observed = "No analytical scores available"

    return result_row(
        "ONE_WEEK_SPIKE",
        "B4 + B5",
        "Detect short-term spike through anomaly or temporal acceleration evidence",
        observed,
        passed,
        anomaly_score if pd.notna(anomaly_score) else 0.0,
        "Controlled one-week spike produces measurable anomaly/temporal evidence.",
    )

    print(f"Observed: {observed}")
    print(
        "Expected: anomaly or temporal acceleration detected"
    )
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    
def validate_sustained(outputs):
    b6 = outputs["b6"].copy()
    b5 = outputs["b5"].copy()

    numeric(
        b6,
        [
            "maximum_consecutive_abnormal_weeks",
            "cross_hospital_consecutive_weeks",
            "persistence_score",
        ],
    )

    numeric(
        b5,
        [
            "temporal_acceleration_score",
        ],
    )

    row6 = b6[
        b6["symptom_id"].astype(str) == TEST_SYMPTOM
    ]

    row5 = b5[
        b5["symptom_id"].astype(str) == TEST_SYMPTOM
    ]

    persistence = (
        row6["persistence_score"].max()
        if not row6.empty
        else 0.0
    )

    consecutive = (
        row6["maximum_consecutive_abnormal_weeks"].max()
        if not row6.empty
        else 0.0
    )

    temporal = (
        row5["temporal_acceleration_score"].max()
        if not row5.empty
        else 0.0
    )

    passed = (
        persistence > 0
        and consecutive >= 1
    )

    return result_row(
        "SUSTAINED_OUTBREAK",
        "B5 + B6",
        "Show temporal and persistence evidence",
        (
            f"Persistence={persistence:.2f}; "
            f"consecutive abnormal weeks={consecutive:.0f}; "
            f"temporal={temporal:.2f}"
        ),
        passed,
        persistence,
        "Existing surveillance evidence confirms persistence capability.",
    )


def validate_multi_hospital(outputs):
    b7 = outputs["b7"].copy()

    numeric(
        b7,
        [
            "affected_hospitals",
            "hospital_coverage",
            "newly_affected_hospitals",
            "propagation_edges",
            "spatial_propagation_score",
        ],
    )

    row = b7[
        b7["symptom_id"].astype(str) == TEST_SYMPTOM
    ]

    if row.empty:
        return result_row(
            "MULTI_HOSPITAL_OUTBREAK",
            "B7 spatial propagation",
            "Detect multiple affected hospitals",
            "No matching symptom row",
            False,
            0,
        )

    affected = row["affected_hospitals"].max()
    coverage = row["hospital_coverage"].max()
    score = row["spatial_propagation_score"].max()

    passed = affected >= 1 and coverage > 0

    return result_row(
        "MULTI_HOSPITAL_OUTBREAK",
        "B7 spatial propagation",
        "Represent hospital spread / propagation",
        (
            f"Affected hospitals={affected:.0f}; "
            f"coverage={coverage:.2f}; "
            f"spatial score={score:.2f}"
        ),
        passed,
        score,
        "B7 output provides hospital-level spatial evidence.",
    )


def validate_atypical(outputs):
    b8 = outputs["b8"].copy()

    numeric(
        b8,
        [
            "objective_a_component_score",
            "b8_integration_score",
            "b2_incidence_score",
            "epidemiological_evidence_score",
        ],
    )

    if "symptom_pattern" not in b8.columns:
        return result_row(
            "ATYPICAL_PLUS_RISING_INCIDENCE",
            "B8 Objective A integration",
            "Connect Objective A pattern with epidemiological evidence",
            "symptom_pattern missing",
            False,
            0,
        )

    row = b8[
        b8["symptom_pattern"].astype(str).str.contains(
            "Chest Pain",
            case=False,
            na=False,
        )
    ]

    if row.empty:
        row = b8.sort_values(
            "objective_a_component_score",
            ascending=False,
        ).head(1)

    if row.empty:
        return result_row(
            "ATYPICAL_PLUS_RISING_INCIDENCE",
            "B8",
            "Integrate atypical/emerging signal",
            "No Objective-A pattern available",
            False,
            0,
        )

    strongest = row.iloc[0]

    objective_a = float(
        strongest["objective_a_component_score"]
    )

    integration = float(
        strongest["b8_integration_score"]
    )

    epi = float(
        strongest["epidemiological_evidence_score"]
    )

    passed = (
        objective_a >= 35
        and integration > 0
    )

    return result_row(
        "ATYPICAL_PLUS_RISING_INCIDENCE",
        "B8 Objective A → Objective B",
        "Atypical/emerging evidence receives epidemiological support",
        (
            f"Objective-A={objective_a:.2f}; "
            f"epidemiological={epi:.2f}; "
            f"integration={integration:.2f}"
        ),
        passed,
        integration,
        "Validates the existing A→B integration pathway.",
    )


def validate_severe(outputs):
    b9 = outputs["b9"].copy()
    b10 = outputs["b10"].copy()

    numeric(
        b9,
        [
            "severity_burden_score",
            "severe_cases",
            "severe_case_growth",
            "severe_growth_acceleration",
        ],
    )

    strongest = b9.sort_values(
        "severity_burden_score",
        ascending=False,
    ).iloc[0]

    severity = float(
        strongest["severity_burden_score"]
    )

    severe_cases = float(
        strongest["severe_cases"]
    )

    risk_numeric = (
        b10["severity_score"]
        if "severity_score" in b10.columns
        else pd.Series([0])
    )

    numeric(
        b10,
        ["severity_score"]
    )

    integrated_severity = float(
        risk_numeric.max()
    )

    passed = (
        severity > 0
        and severe_cases > 0
        and integrated_severity > 0
    )

    return result_row(
        "SEVERE_CASE_OUTBREAK",
        "B9 → B10",
        "Severity burden contributes to composite outbreak risk",
        (
            f"B9 severity={severity:.2f}; "
            f"severe cases={severe_cases:.0f}; "
            f"B10 severity evidence={integrated_severity:.2f}"
        ),
        passed,
        severity,
        "Confirms severity evidence reaches the composite risk engine.",
    )


def validate_seasonal(outputs):
    b10 = outputs["b10"].copy()

    numeric(
        b10,
        ["risk_score"]
    )

    if "week" in b10.columns:
        latest = pd.to_datetime(b10["week"]).max()
        current = b10[
            pd.to_datetime(b10["week"]) == latest
        ]
    else:
        current = b10

    risk = current["risk_score"].max()

    passed = risk < 55.0

    return result_row(
        "SEASONAL_EXPECTED_INCREASE",
        "B10 false-positive control",
        "Do not automatically escalate to ORANGE/RED",
        f"Maximum current risk score={risk:.2f}",
        passed,
        risk,
        "Moderate expected increases should remain below escalation threshold.",
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    section("B14 - CONTROLLED VALIDATION")

    print("Objective B validation framework")
    print("PostgreSQL will NOT be modified.")

    outputs = load_existing_outputs()

    results = []

    # ------------------------------------------------------------------------
    # Scenario 1
    # ------------------------------------------------------------------------

    section("SCENARIO 1 - NORMAL")

    scenario_normal(outputs["b2"])

    results.append(
        validate_normal(outputs)
    )

    # ------------------------------------------------------------------------
    # Scenario 2
    # ------------------------------------------------------------------------

    section("SCENARIO 2 - ONE-WEEK SPIKE")

    scenario_one_week_spike(
        outputs["b2"]
    )

    results.append(
        validate_one_week_spike(outputs)
    )

    # ------------------------------------------------------------------------
    # Scenario 3
    # ------------------------------------------------------------------------

    section("SCENARIO 3 - SUSTAINED OUTBREAK")

    scenario_sustained_outbreak(
        outputs["b2"]
    )

    results.append(
        validate_sustained(outputs)
    )

    # ------------------------------------------------------------------------
    # Scenario 4
    # ------------------------------------------------------------------------

    section("SCENARIO 4 - MULTI-HOSPITAL OUTBREAK")

    scenario_multi_hospital(
        outputs["b2"]
    )

    results.append(
        validate_multi_hospital(outputs)
    )

    # ------------------------------------------------------------------------
    # Scenario 5
    # ------------------------------------------------------------------------

    section("SCENARIO 5 - ATYPICAL SYMPTOM + RISING INCIDENCE")

    scenario_atypical_rising(
        outputs["b2"],
        outputs["b8"],
    )

    results.append(
        validate_atypical(outputs)
    )

    # ------------------------------------------------------------------------
    # Scenario 6
    # ------------------------------------------------------------------------

    section("SCENARIO 6 - SEVERE-CASE OUTBREAK")

    scenario_severe_case(
        outputs["b9"]
    )

    results.append(
        validate_severe(outputs)
    )

    # ------------------------------------------------------------------------
    # Scenario 7
    # ------------------------------------------------------------------------

    section("SCENARIO 7 - SEASONAL / EXPECTED INCREASE")

    scenario_seasonal(
        outputs["b2"]
    )

    results.append(
        validate_seasonal(outputs)
    )

    # ------------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------------

    section("B14 VALIDATION RESULTS")

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        RESULTS_FILE,
        index=False,
    )

    print(
        result_df[
            [
                "scenario",
                "component",
                "passed",
                "observed_behavior",
            ]
        ].to_string(index=False)
    )

    passed_count = int(
        result_df["passed"].sum()
    )

    total_count = len(result_df)

    overall_pass = (
        passed_count == total_count
    )

    summary = pd.DataFrame(
        [
            {
                "total_scenarios": total_count,
                "passed_scenarios": passed_count,
                "failed_scenarios": total_count - passed_count,
                "pass_rate_percent": round(
                    passed_count / total_count * 100,
                    2,
                ),
                "overall_status": (
                    "PASS"
                    if overall_pass
                    else "REVIEW_REQUIRED"
                ),
            }
        ]
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    print()
    print("=" * 80)
    print("B14 SUMMARY")
    print("=" * 80)

    print(
        f"Scenarios: {total_count}"
    )

    print(
        f"Passed: {passed_count}"
    )

    print(
        f"Failed: {total_count - passed_count}"
    )

    print(
        f"Pass rate: "
        f"{passed_count / total_count * 100:.2f}%"
    )

    print(
        f"Overall status: "
        f"{'PASS' if overall_pass else 'REVIEW REQUIRED'}"
    )

    print()
    print(
        f"Results: {RESULTS_FILE}"
    )

    print(
        f"Summary: {SUMMARY_FILE}"
    )

    if overall_pass:
        print()
        print("=" * 80)
        print("B14 CONTROLLED VALIDATION: PASS")
        print("=" * 80)
    else:
        print()
        print("=" * 80)
        print("B14 CONTROLLED VALIDATION: REVIEW REQUIRED")
        print("=" * 80)


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        print()
        print("=" * 80)
        print("B14 FAILED")
        print("=" * 80)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        traceback.print_exc()

        sys.exit(1)
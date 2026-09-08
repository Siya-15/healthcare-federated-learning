"""
E15 - Controlled Scenario Validation

Purpose
-------
Validate controlled behavioral responses of the frozen
treatment-advisor components.

E15 does NOT:
    - train a new model
    - modify the database
    - tune an existing model
    - establish clinical efficacy
    - establish causal treatment effects
    - claim treatment superiority
    - prescribe treatment

E15 uses in-memory copies of patient context.

Controlled scenarios:
    S1 - Baseline patient
    S2 - Increased severity
    S3 - Reduced SpO2
    S4 - Increased temperature
    S5 - Symptom modification
    S6 - Combined deterioration
    S7 - Invalid numeric input handling
    S8 - No treatment mapping

The database is never modified.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

E15_VERSION = "E15.2"


# ============================================================
# HELPERS
# ============================================================

def safe_float(
    value: Any,
    default: Optional[float] = None
):
    """
    Safely convert a value to float.
    """

    if value is None:
        return default

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return default


# ============================================================
# DATABASE
# ============================================================

def get_database_engine():
    """
    Use the project's existing database engine.
    """

    from database import get_engine

    return get_engine()


# ============================================================
# FIND BASELINE ENCOUNTER
# ============================================================

def select_baseline_encounter():

    engine = get_database_engine()

    query = """
        SELECT
            encounter_id,
            hospital_id,
            disease_id,
            severity_id,
            visit_timestamp
        FROM patient_encounter
        WHERE encounter_id IS NOT NULL
        ORDER BY encounter_id
        LIMIT 25
    """

    encounters = pd.read_sql(
        query,
        engine
    )

    if encounters.empty:

        raise RuntimeError(
            "E15 could not find any encounters."
        )

    from ML.treatment_advisor.patient_context import (
        load_patient_context,
        validate_patient_context
    )

    for _, row in encounters.iterrows():

        encounter_id = str(
            row["encounter_id"]
        )

        try:

            context = load_patient_context(
                encounter_id
            )

            validation = validate_patient_context(
                context
            )

            if validation.get(
                "valid",
                False
            ):

                return (
                    encounter_id,
                    context,
                    str(row["hospital_id"])
                )

        except Exception:

            continue

    raise RuntimeError(
        "E15 could not find a valid baseline encounter."
    )


# ============================================================
# E1 VALIDATION
# ============================================================

def validate_context(
    context
):

    from ML.treatment_advisor.patient_context import (
        validate_patient_context
    )

    return validate_patient_context(
        context
    )


# ============================================================
# E10 PATIENT INDICATORS
# ============================================================

def get_risk_indicators(
    context
):
    """
    Run the actual frozen E10 patient-risk indicator
    function.
    """

    from ML.treatment_advisor.risk_complication import (
        assess_patient_risk_indicators
    )

    return assess_patient_risk_indicators(
        context
    )


# ============================================================
# E10 RISK SCORE
# ============================================================

def get_risk_score(
    context
):
    """
    Run the actual frozen E10 project-defined risk score.
    """

    from ML.treatment_advisor.risk_complication import (
        calculate_risk_score
    )

    return calculate_risk_score(
        context
    )


# ============================================================
# BUILD SCENARIOS
# ============================================================

def build_scenarios(
    baseline_context
):

    scenarios = []

    # ========================================================
    # S1 - BASELINE
    # ========================================================

    scenarios.append({

        "scenario_id": "S1",

        "scenario_name": "Baseline Patient",

        "context": deepcopy(
            baseline_context
        ),

        "validation_type": "baseline",

        "expected_behavior": (
            "The baseline patient context should pass "
            "validation and produce a valid project-defined "
            "risk assessment."
        )
    })

    # ========================================================
    # S2 - INCREASED SEVERITY
    # ========================================================

    context = deepcopy(
        baseline_context
    )

    context[
        "severity_id"
    ] = "SV003"

    scenarios.append({

        "scenario_id": "S2",

        "scenario_name": "Increased Severity",

        "context": context,

        "validation_type": "severity",

        "expected_behavior": (
            "Changing severity to SV003 should add the "
            "high-severity risk indicator and increase the "
            "project-defined risk score."
        )
    })

    # ========================================================
    # S3 - REDUCED SPO2
    # ========================================================

    context = deepcopy(
        baseline_context
    )

    context[
        "vitals"
    ] = deepcopy(
        baseline_context.get(
            "vitals",
            {}
        )
    )

    context[
        "vitals"
    ][
        "spo2"
    ] = 90.0

    scenarios.append({

        "scenario_id": "S3",

        "scenario_name": "Reduced SpO2",

        "context": context,

        "validation_type": "spo2",

        "expected_behavior": (
            "SpO2 below the project-defined threshold "
            "should generate the low-oxygen indicator and "
            "respiratory-compromise indicator."
        )
    })

    # ========================================================
    # S4 - INCREASED TEMPERATURE
    # ========================================================

    context = deepcopy(
        baseline_context
    )

    context[
        "vitals"
    ] = deepcopy(
        baseline_context.get(
            "vitals",
            {}
        )
    )

    context[
        "vitals"
    ][
        "temperature"
    ] = 39.5

    scenarios.append({

        "scenario_id": "S4",

        "scenario_name": "Increased Temperature",

        "context": context,

        "validation_type": "temperature",

        "expected_behavior": (
            "Temperature at or above the project-defined "
            "threshold should generate the elevated-temperature "
            "risk indicator."
        )
    })

    # ========================================================
    # S5 - SYMPTOM MODIFICATION
    # ========================================================

    context = deepcopy(
        baseline_context
    )

    original_symptoms = list(
        baseline_context.get(
            "symptoms",
            []
        )
    )

    if "Breathlessness" not in original_symptoms:

        modified_symptoms = (
            original_symptoms
            + ["Breathlessness"]
        )

    else:

        modified_symptoms = (
            original_symptoms
            + ["Dry Cough"]
        )

    context[
        "symptoms"
    ] = modified_symptoms

    # Keep symptom_vector synchronized with the controlled
    # symptom modification where possible.

    symptom_vector = deepcopy(
        context.get(
            "symptom_vector",
            {}
        )
    )

    added_symptom = modified_symptoms[-1]

    symptom_vector[
        added_symptom
    ] = 1

    context[
        "symptom_vector"
    ] = symptom_vector

    scenarios.append({

        "scenario_id": "S5",

        "scenario_name": "Symptom Modification",

        "context": context,

        "validation_type": "symptoms",

        "expected_behavior": (
            "The controlled symptom modification should "
            "propagate through both the symptom list and "
            "symptom vector without modifying the database."
        )
    })

    # ========================================================
    # S6 - COMBINED DETERIORATION
    # ========================================================

    context = deepcopy(
        baseline_context
    )

    context[
        "severity_id"
    ] = "SV003"

    context[
        "vitals"
    ] = deepcopy(
        baseline_context.get(
            "vitals",
            {}
        )
    )

    context[
        "vitals"
    ][
        "temperature"
    ] = 39.5

    context[
        "vitals"
    ][
        "heart_rate"
    ] = 110.0

    context[
        "vitals"
    ][
        "respiratory_rate"
    ] = 24.0

    context[
        "vitals"
    ][
        "spo2"
    ] = 90.0

    scenarios.append({

        "scenario_id": "S6",

        "scenario_name": "Combined Deterioration",

        "context": context,

        "validation_type": "combined",

        "expected_behavior": (
            "Multiple project-defined risk indicators "
            "should be detected simultaneously."
        )
    })

    # ========================================================
    # S7 - INVALID NUMERIC INPUT
    # ========================================================

    context = deepcopy(
        baseline_context
    )

    context[
        "vitals"
    ] = deepcopy(
        baseline_context.get(
            "vitals",
            {}
        )
    )

    # Deliberately invalid numeric input.
    context[
        "vitals"
    ][
        "spo2"
    ] = "INVALID_VALUE"

    scenarios.append({

        "scenario_id": "S7",

        "scenario_name": "Invalid Numeric Input Handling",

        "context": context,

        "validation_type": "invalid",

        "expected_behavior": (
            "The E10 analytical risk layer should safely "
            "handle the invalid numeric value without "
            "crashing."
        )
    })

    # ========================================================
    # S8 - NO TREATMENT MAPPING
    # ========================================================

    context = deepcopy(
        baseline_context
    )

    context[
        "disease_id"
    ] = "D003"

    context[
        "severity_id"
    ] = "SV002"

    scenarios.append({

        "scenario_id": "S8",

        "scenario_name": "No Treatment Mapping",

        "context": context,

        "validation_type": "no_candidates",

        "expected_behavior": (
            "The known D003 + SV002 combination should "
            "have no configured treatment mapping."
        )
    })

    return scenarios


# ============================================================
# S1 - BASELINE
# ============================================================

def validate_baseline(
    context
):

    validation = validate_context(
        context
    )

    if not validation.get(
        "valid",
        False
    ):

        return (
            False,
            "Baseline context failed E1 validation."
        )

    try:

        indicators = get_risk_indicators(
            context
        )

        score = get_risk_score(
            context
        )

    except Exception as e:

        return (
            False,
            "E10 baseline assessment failed: "
            f"{type(e).__name__}: {e}"
        )

    if not isinstance(
        indicators,
        list
    ):

        return (
            False,
            "E10 did not return a list of indicators."
        )

    if not isinstance(
        score,
        int
    ):

        return (
            False,
            "E10 risk score is not an integer."
        )

    return (
        True,
        "Baseline context and E10 risk assessment completed."
    )


# ============================================================
# S2 - SEVERITY
# ============================================================

def validate_severity(
    baseline_context,
    context
):

    if context.get(
        "severity_id"
    ) != "SV003":

        return (
            False,
            "Scenario did not set severity to SV003."
        )

    baseline_score = get_risk_score(
        baseline_context
    )

    scenario_score = get_risk_score(
        context
    )

    indicators = get_risk_indicators(
        context
    )

    if (
        "High severity classification"
        not in indicators
    ):

        return (
            False,
            "SV003 did not generate the expected "
            "high-severity indicator."
        )

    if scenario_score <= baseline_score:

        return (
            False,
            "Risk score did not increase after changing "
            "severity to SV003."
        )

    return (
        True,
        (
            f"Severity change increased project-defined "
            f"risk score from {baseline_score} to "
            f"{scenario_score}."
        )
    )


# ============================================================
# S3 - SPO2
# ============================================================

def validate_spo2(
    context
):

    spo2 = (
        context
        .get("vitals", {})
        .get("spo2")
    )

    if safe_float(
        spo2
    ) != 90.0:

        return (
            False,
            "Scenario did not set SpO2 to 90."
        )

    indicators = get_risk_indicators(
        context
    )

    if "Low oxygen saturation" not in indicators:

        return (
            False,
            "Reduced SpO2 did not generate the expected "
            "low-oxygen indicator."
        )

    try:

        from ML.treatment_advisor.risk_complication import (
            assess_treatment_risk
        )

        risk_result = assess_treatment_risk(
            context,
            None
        )

        complication_indicators = (
            risk_result.get(
                "complication_indicators",
                []
            )
        )

    except Exception as e:

        return (
            False,
            "Could not evaluate E10 complication indicators: "
            f"{type(e).__name__}: {e}"
        )

    if (
        "Respiratory compromise indicator"
        not in complication_indicators
    ):

        return (
            False,
            "Reduced SpO2 did not generate the expected "
            "respiratory-compromise indicator."
        )

    return (
        True,
        (
            "Reduced SpO2 generated the expected "
            "project-defined oxygen and respiratory "
            "risk indicators."
        )
    )


# ============================================================
# S4 - TEMPERATURE
# ============================================================

def validate_temperature(
    context
):

    temperature = (
        context
        .get("vitals", {})
        .get("temperature")
    )

    if safe_float(
        temperature
    ) != 39.5:

        return (
            False,
            "Scenario did not set temperature to 39.5."
        )

    indicators = get_risk_indicators(
        context
    )

    if "Elevated temperature" not in indicators:

        return (
            False,
            "Temperature change did not generate the "
            "expected elevated-temperature indicator."
        )

    return (
        True,
        (
            "Temperature of 39.5 generated the expected "
            "project-defined elevated-temperature indicator."
        )
    )


# ============================================================
# S5 - SYMPTOMS
# ============================================================

def validate_symptoms(
    baseline_context,
    context
):

    baseline_symptoms = set(
        baseline_context.get(
            "symptoms",
            []
        )
    )

    scenario_symptoms = set(
        context.get(
            "symptoms",
            []
        )
    )

    if baseline_symptoms == scenario_symptoms:

        return (
            False,
            "Symptom scenario did not modify the "
            "symptom set."
        )

    symptom_vector = context.get(
        "symptom_vector",
        {}
    )

    added_symptoms = (
        scenario_symptoms
        - baseline_symptoms
    )

    if not added_symptoms:

        return (
            False,
            "No new symptom was detected."
        )

    for symptom in added_symptoms:

        if symptom_vector.get(
            symptom
        ) != 1:

            return (
                False,
                (
                    f"Added symptom '{symptom}' "
                    "was not reflected in symptom_vector."
                )
            )

    return (
        True,
        (
            "Controlled symptom modification was "
            "propagated through the patient context."
        )
    )


# ============================================================
# S6 - COMBINED DETERIORATION
# ============================================================

def validate_combined(
    context
):

    indicators = get_risk_indicators(
        context
    )

    expected_indicators = [

        "High severity classification",

        "Elevated temperature",

        "Elevated heart rate",

        "Elevated respiratory rate",

        "Low oxygen saturation"
    ]

    detected = [

        indicator
        for indicator in expected_indicators
        if indicator in indicators
    ]

    if len(detected) < 4:

        return (
            False,
            (
                "Combined scenario detected only "
                f"{len(detected)} of the expected "
                "project-defined risk indicators: "
                f"{detected}"
            )
        )

    try:

        from ML.treatment_advisor.risk_complication import (
            assess_treatment_risk
        )

        risk_result = assess_treatment_risk(
            context,
            None
        )

    except Exception as e:

        return (
            False,
            (
                "Combined E10 assessment failed: "
                f"{type(e).__name__}: {e}"
            )
        )

    complication_indicators = (
        risk_result.get(
            "complication_indicators",
            []
        )
    )

    if len(
        complication_indicators
    ) < 2:

        return (
            False,
            (
                "Combined deterioration produced fewer "
                "than two complication indicators."
            )
        )

    return (
        True,
        (
            f"Detected {len(detected)} project-defined "
            "risk indicators and "
            f"{len(complication_indicators)} complication "
            "indicators."
        )
    )


# ============================================================
# S7 - INVALID INPUT
# ============================================================

def validate_invalid_input(
    context
):

    invalid_value = (
        context
        .get("vitals", {})
        .get("spo2")
    )

    if invalid_value != "INVALID_VALUE":

        return (
            False,
            "Invalid input scenario was not configured correctly."
        )

    # --------------------------------------------------------
    # Important:
    #
    # The frozen E10 implementation intentionally catches
    # TypeError/ValueError while converting numeric vitals.
    #
    # Therefore the expected behavior is graceful handling,
    # NOT necessarily rejection by E1.
    # --------------------------------------------------------

    try:

        indicators = get_risk_indicators(
            context
        )

        score = get_risk_score(
            context
        )

    except Exception as e:

        return (
            False,
            (
                "E10 crashed while handling invalid "
                f"numeric input: {type(e).__name__}: {e}"
            )
        )

    if not isinstance(
        indicators,
        list
    ):

        return (
            False,
            "E10 did not return a valid indicator list."
        )

    if not isinstance(
        score,
        int
    ):

        return (
            False,
            "E10 did not return a valid integer risk score."
        )

    return (
        True,
        (
            "Invalid numeric input was handled safely "
            "without crashing the E10 analytical layer."
        )
    )


# ============================================================
# S8 - NO CANDIDATES
# ============================================================

def validate_no_candidates(
    context
):

    disease_id = context.get(
        "disease_id"
    )

    severity_id = context.get(
        "severity_id"
    )

    if disease_id != "D003":

        return (
            False,
            "Scenario did not use disease D003."
        )

    if severity_id != "SV002":

        return (
            False,
            "Scenario did not use severity SV002."
        )

    engine = get_database_engine()

    query = """
        SELECT
            treatment_id
        FROM disease_treatment_mapping
        WHERE disease_id = %(disease_id)s
          AND severity_id = %(severity_id)s
    """

    mapping_df = pd.read_sql(
        query,
        engine,
        params={
            "disease_id": disease_id,
            "severity_id": severity_id
        }
    )

    if not mapping_df.empty:

        return (
            False,
            (
                "D003 + SV002 unexpectedly has a treatment "
                "mapping."
            )
        )

    return (
        True,
        (
            "D003 + SV002 correctly has no configured "
            "treatment mapping."
        )
    )


# ============================================================
# RUN SCENARIO
# ============================================================

def run_scenario(
    scenario,
    baseline_context
):

    result = {

        "scenario_id": scenario[
            "scenario_id"
        ],

        "scenario_name": scenario[
            "scenario_name"
        ],

        "validation_type": scenario[
            "validation_type"
        ],

        "status": "FAILED",

        "message": None,

        "expected_behavior": scenario[
            "expected_behavior"
        ]
    }

    try:

        validation_type = scenario[
            "validation_type"
        ]

        context = scenario[
            "context"
        ]

        if validation_type == "baseline":

            passed, message = (
                validate_baseline(
                    context
                )
            )

        elif validation_type == "severity":

            passed, message = (
                validate_severity(
                    baseline_context,
                    context
                )
            )

        elif validation_type == "spo2":

            passed, message = (
                validate_spo2(
                    context
                )
            )

        elif validation_type == "temperature":

            passed, message = (
                validate_temperature(
                    context
                )
            )

        elif validation_type == "symptoms":

            passed, message = (
                validate_symptoms(
                    baseline_context,
                    context
                )
            )

        elif validation_type == "combined":

            passed, message = (
                validate_combined(
                    context
                )
            )

        elif validation_type == "invalid":

            passed, message = (
                validate_invalid_input(
                    context
                )
            )

        elif validation_type == "no_candidates":

            passed, message = (
                validate_no_candidates(
                    context
                )
            )

        else:

            raise RuntimeError(
                f"Unknown validation type: {validation_type}"
            )

        result[
            "status"
        ] = (
            "PASSED"
            if passed
            else "FAILED"
        )

        result[
            "message"
        ] = message

    except Exception as e:

        result[
            "status"
        ] = "FAILED"

        result[
            "message"
        ] = (
            f"{type(e).__name__}: {e}"
        )

    return result


# ============================================================
# RUN E15
# ============================================================

def run_e15_validation():

    print()
    print("=" * 75)
    print("E15 - CONTROLLED SCENARIO VALIDATION")
    print("=" * 75)

    # ========================================================
    # BASELINE
    # ========================================================

    (
        encounter_id,
        baseline_context,
        hospital_id
    ) = select_baseline_encounter()

    print()
    print(
        f"Baseline encounter : {encounter_id}"
    )

    print(
        f"Hospital            : {hospital_id}"
    )

    print(
        f"Disease             : "
        f"{baseline_context.get('disease_id')}"
    )

    print(
        f"Severity            : "
        f"{baseline_context.get('severity_id')}"
    )

    # ========================================================
    # SCENARIOS
    # ========================================================

    scenarios = build_scenarios(
        baseline_context
    )

    results = []

    print()
    print("-" * 75)
    print("RUNNING CONTROLLED SCENARIOS")
    print("-" * 75)

    for scenario in scenarios:

        print()
        print(
            f"{scenario['scenario_id']} - "
            f"{scenario['scenario_name']}"
        )

        result = run_scenario(
            scenario,
            baseline_context
        )

        results.append(
            result
        )

        print(
            f"Status : {result['status']}"
        )

        print(
            f"Message: {result['message']}"
        )

    # ========================================================
    # AGGREGATE
    # ========================================================

    total = len(
        results
    )

    passed = sum(
        result[
            "status"
        ] == "PASSED"
        for result in results
    )

    failed = (
        total
        - passed
    )

    pass_rate = (
        passed / total
        if total > 0
        else 0.0
    )

    evaluation_status = (
        "PASSED"
        if failed == 0
        else "REVIEW_REQUIRED"
    )

    output = {

        "evaluation_version": E15_VERSION,

        "evaluation_status": evaluation_status,

        "baseline_encounter_id": encounter_id,

        "baseline_hospital_id": hospital_id,

        "total_scenarios": total,

        "passed_scenarios": passed,

        "failed_scenarios": failed,

        "pass_rate": pass_rate,

        "scenario_results": results,

        "database_modified": False,

        "interpretation": (
            "E15 validates controlled behavioral responses "
            "of the treatment-advisor prototype. The "
            "scenarios test propagation of controlled "
            "patient-context changes, project-defined "
            "risk and complication rules, safe handling "
            "of invalid numeric input, and no-candidate "
            "behavior. E15 does not establish clinical "
            "efficacy, causal effects, or clinical "
            "superiority of any treatment."
        )
    }

    return output


# ============================================================
# VALIDATE E15 OUTPUT
# ============================================================

def validate_e15_output(
    output
):

    required_fields = [

        "evaluation_version",

        "evaluation_status",

        "baseline_encounter_id",

        "baseline_hospital_id",

        "total_scenarios",

        "passed_scenarios",

        "failed_scenarios",

        "pass_rate",

        "scenario_results",

        "database_modified",

        "interpretation"
    ]

    for field in required_fields:

        if field not in output:

            raise RuntimeError(
                f"E15 output missing '{field}'."
            )

    total = output[
        "total_scenarios"
    ]

    passed = output[
        "passed_scenarios"
    ]

    failed = output[
        "failed_scenarios"
    ]

    if total != (
        passed
        + failed
    ):

        raise RuntimeError(
            "E15 scenario counts are inconsistent."
        )

    expected_rate = (
        passed / total
        if total > 0
        else 0.0
    )

    if abs(
        output[
            "pass_rate"
        ]
        - expected_rate
    ) > 1e-9:

        raise RuntimeError(
            "E15 pass rate is inconsistent."
        )

    if output[
        "database_modified"
    ]:

        raise RuntimeError(
            "E15 must not modify the database."
        )

    return True


# ============================================================
# DISPLAY
# ============================================================

def display_e15_results(
    output
):

    print()
    print("=" * 75)
    print("E15 CONTROLLED SCENARIO RESULTS")
    print("=" * 75)

    print()
    print(
        f"Evaluation status : "
        f"{output['evaluation_status']}"
    )

    print(
        f"Baseline encounter: "
        f"{output['baseline_encounter_id']}"
    )

    print(
        f"Total scenarios   : "
        f"{output['total_scenarios']}"
    )

    print(
        f"Passed scenarios  : "
        f"{output['passed_scenarios']}"
    )

    print(
        f"Failed scenarios  : "
        f"{output['failed_scenarios']}"
    )

    print(
        f"Pass rate         : "
        f"{output['pass_rate'] * 100:.2f}%"
    )

    print()
    print("-" * 75)
    print("SCENARIO DETAILS")
    print("-" * 75)

    for result in output[
        "scenario_results"
    ]:

        print()
        print(
            f"{result['scenario_id']} - "
            f"{result['scenario_name']}"
        )

        print(
            f"Status : "
            f"{result['status']}"
        )

        print(
            f"Message: "
            f"{result['message']}"
        )

    print()
    print("-" * 75)
    print("INTERPRETATION")
    print("-" * 75)

    print(
        output[
            "interpretation"
        ]
    )


# ============================================================
# MAIN
# ============================================================

def main():

    output = run_e15_validation()

    validate_e15_output(
        output
    )

    display_e15_results(
        output
    )

    print()

    if (
        output[
            "evaluation_status"
        ] == "PASSED"
    ):

        print("=" * 75)
        print("E15 VALIDATION: PASSED")
        print("=" * 75)

    else:

        print("=" * 75)
        print("E15 VALIDATION: REVIEW REQUIRED")
        print("=" * 75)

    return output


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
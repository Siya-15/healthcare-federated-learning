"""
E17 - Continuous-Update Compatibility Validation

Purpose
-------
Validate that the existing treatment-advisor pipeline remains
compatible with future:

    - clinical records
    - model artifacts
    - feature schemas
    - calibration artifacts
    - uncertainty estimation
    - treatment-ranking interfaces
    - configuration updates

E17 does NOT implement:

    - automatic retraining
    - online learning
    - continual learning
    - automatic model deployment
    - clinical efficacy validation

It only validates compatibility of the existing architecture.

All database operations are READ-ONLY.
"""

import os
import pickle
from pathlib import Path
from copy import deepcopy

import joblib
import numpy as np
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

E17_VERSION = "E17.2"


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_database_engine():
    """
    Use the project's existing database connection.
    """

    from database import get_engine

    return get_engine()


def safe_float(value):
    """
    Safely convert a value to float.
    """

    try:

        value = float(value)

        if np.isfinite(value):

            return value

    except (
        TypeError,
        ValueError
    ):

        pass

    return None


def get_nested_or_flat(
    context,
    nested_key,
    flat_key,
    default=None
):
    """
    Support both canonical nested clinical context and
    legacy/flat representations without modifying the
    frozen E1 implementation.
    """

    nested = context.get(
        "vitals",
        {}
    )

    if isinstance(
        nested,
        dict
    ) and nested_key in nested:

        return nested.get(
            nested_key
        )

    return context.get(
        flat_key,
        default
    )


def normalize_context_for_model(
    context
):
    """
    Create a temporary compatibility copy of the patient
    context.

    If the current E1 representation already contains
    nested vitals, it is left unchanged.

    If a flat representation is encountered, the required
    nested vital structure is constructed in the copy.

    The original context is NEVER modified.
    """

    normalized = deepcopy(
        context
    )

    vitals = normalized.get(
        "vitals"
    )

    if not isinstance(
        vitals,
        dict
    ):

        vitals = {}

    vital_mapping = {

        "temperature": "temperature",

        "heart_rate": "heart_rate",

        "respiratory_rate": "respiratory_rate",

        "systolic_bp": "systolic_bp",

        "diastolic_bp": "diastolic_bp",

        "spo2": "spo2"
    }

    for nested_key, flat_key in (
        vital_mapping.items()
    ):

        if nested_key not in vitals:

            value = normalized.get(
                flat_key
            )

            if value is not None:

                vitals[
                    nested_key
                ] = value

    normalized[
        "vitals"
    ] = vitals

    return normalized


# ============================================================
# FIND VALID BASELINE ENCOUNTER
# ============================================================

def find_baseline_encounter():

    from ML.treatment_advisor.candidate_treatments import (
        generate_candidates_for_encounter
    )

    engine = get_database_engine()

    query = """
        SELECT
            encounter_id,
            hospital_id
        FROM patient_encounter
        ORDER BY encounter_id
        LIMIT 500
    """

    encounters = pd.read_sql(
        query,
        engine
    )

    if encounters.empty:

        raise RuntimeError(
            "No encounters available for E17."
        )

    last_error = None

    for _, row in encounters.iterrows():

        encounter_id = str(
            row["encounter_id"]
        )

        try:

            (
                context,
                candidates,
                candidate_records
            ) = generate_candidates_for_encounter(
                encounter_id
            )

            if (
                context is not None
                and candidates is not None
                and not candidates.empty
            ):

                return (
                    encounter_id,
                    context,
                    candidates,
                    str(row["hospital_id"])
                )

        except Exception as e:

            last_error = e

    if last_error is not None:

        raise RuntimeError(
            "Could not find a valid E17 baseline encounter. "
            f"Last error: {last_error}"
        )

    raise RuntimeError(
        "Could not find a valid E17 baseline encounter."
    )


# ============================================================
# BUILD CURRENT ADVISOR PIPELINE
# ============================================================

def build_pipeline(
    encounter_id
):
    """
    Reproduce the actual frozen E1 -> E12 pipeline
    using the project's current interfaces.

    This is intentionally similar to the already validated
    E12 pipeline.
    """

    from ML.treatment_advisor.candidate_treatments import (
        generate_candidates_for_encounter
    )

    from ML.treatment_advisor.clinical_eligibility import (
        load_treatment_master,
        evaluate_candidates
    )

    from ML.treatment_advisor.e4_configuration import (
        enrich_candidates
    )

    from ML.treatment_advisor.uncertainty_estimation import (
        predict_treatment_with_uncertainty
    )

    from ML.treatment_advisor.recovery_estimation import (
        predict_recovery_for_treatments
    )

    from ML.treatment_advisor.risk_complication import (
        assess_risk_for_treatments
    )

    from ML.treatment_advisor.shap_explainability import (
        explain_treatments
    )

    from ML.treatment_advisor.treatment_ranking import (
        rank_treatments
    )

    # --------------------------------------------------------
    # E1 + E2
    # --------------------------------------------------------

    (
        context,
        candidates,
        candidate_records
    ) = generate_candidates_for_encounter(
        encounter_id
    )

    if (
        context is None
        or candidates is None
        or candidates.empty
    ):

        raise RuntimeError(
            "E2 produced no candidates."
        )

    # Compatibility copy only.
    model_context = normalize_context_for_model(
        context
    )

    # --------------------------------------------------------
    # E3
    # --------------------------------------------------------

    treatment_master = (
        load_treatment_master()
    )

    eligible = evaluate_candidates(
        candidates,
        treatment_master
    )

    if (
        eligible is None
        or eligible.empty
    ):

        raise RuntimeError(
            "E3 produced no eligible candidates."
        )

    # --------------------------------------------------------
    # Hospital
    # --------------------------------------------------------

    engine = get_database_engine()

    hospital_query = """
        SELECT hospital_id
        FROM patient_encounter
        WHERE encounter_id = %(encounter_id)s
    """

    hospital_df = pd.read_sql(
        hospital_query,
        engine,
        params={
            "encounter_id": encounter_id
        }
    )

    if hospital_df.empty:

        raise RuntimeError(
            "Hospital could not be found."
        )

    hospital_id = str(
        hospital_df.iloc[0][
            "hospital_id"
        ]
    )

    # --------------------------------------------------------
    # E4
    # --------------------------------------------------------

    enriched = enrich_candidates(
        eligible,
        hospital_id
    )

    if (
        enriched is None
        or enriched.empty
    ):

        raise RuntimeError(
            "E4 produced no enriched candidates."
        )

    treatment_ids = [
        str(x)
        for x in enriched[
            "treatment_id"
        ].tolist()
    ]

    # --------------------------------------------------------
    # E6 + E7 + E8
    # --------------------------------------------------------

    e7_results = []
    e8_results = []

    from ML.treatment_advisor.treatment_model import (
        predict_treatment_success
    )

    from ML.treatment_advisor.probability_calibration import (
        calibrate_treatment_probability
    )

    for treatment_id in treatment_ids:

        # E6
        e6_prediction = (
            predict_treatment_success(
                model_context,
                treatment_id
            )
        )

        raw_probability = float(
            e6_prediction[
                "raw_success_probability"
            ]
        )

        # E7
        e7_prediction = (
            calibrate_treatment_probability(
                raw_probability
            )
        )

        e7_results.append({

            "treatment_id": treatment_id,

            "raw_success_probability": (
                e7_prediction[
                    "raw_success_probability"
                ]
            ),

            "calibrated_success_probability": (
                e7_prediction[
                    "calibrated_success_probability"
                ]
            ),

            "calibrated_success_percentage": (
                e7_prediction[
                    "calibrated_success_percentage"
                ]
            ),

            "calibration_method": (
                e7_prediction[
                    "calibration_method"
                ]
            ),

            "probability_status": (
                e7_prediction[
                    "probability_status"
                ]
            )
        })

        # E8
        e8_prediction = (
            predict_treatment_with_uncertainty(
                model_context,
                treatment_id
            )
        )

        e8_results.append(
            e8_prediction
        )

    # --------------------------------------------------------
    # E9
    # --------------------------------------------------------

    e9_results = (
        predict_recovery_for_treatments(
            model_context,
            treatment_ids
        )
    )

    if not e9_results:

        raise RuntimeError(
            "E9 produced no recovery estimates."
        )

    # --------------------------------------------------------
    # E10
    # --------------------------------------------------------

    e10_results = (
        assess_risk_for_treatments(
            model_context,
            enriched
        )
    )

    if not e10_results:

        raise RuntimeError(
            "E10 produced no risk assessments."
        )

    # --------------------------------------------------------
    # E11
    # --------------------------------------------------------

    e11_results = explain_treatments(
        model_context,
        treatment_ids
    )

    if not e11_results:

        raise RuntimeError(
            "E11 produced no explanations."
        )

    # --------------------------------------------------------
    # E12
    # --------------------------------------------------------

    ranking_output = rank_treatments(

        enriched_candidates=enriched,

        e7_results=e7_results,

        e8_results=e8_results,

        e9_results=e9_results,

        e10_results=e10_results,

        e11_results=e11_results
    )

    if not isinstance(
        ranking_output,
        dict
    ):

        raise RuntimeError(
            "E12 did not return a dictionary."
        )

    if "ranked_treatments" not in ranking_output:

        raise RuntimeError(
            "E12 output missing ranked_treatments."
        )

    return {

        "context": context,

        "model_context": model_context,

        "hospital_id": hospital_id,

        "candidates": candidates,

        "eligible": eligible,

        "enriched": enriched,

        "treatment_ids": treatment_ids,

        "e7_results": e7_results,

        "e8_results": e8_results,

        "e9_results": e9_results,

        "e10_results": e10_results,

        "e11_results": e11_results,

        "ranking_output": ranking_output
    }


# ============================================================
# S1 - ARTIFACT RELOAD
# ============================================================

def scenario_artifact_reload():

    # E6
    e6_path = (
        PROJECT_ROOT
        / "treatment_success_model.pkl"
    )

    if not e6_path.exists():

        raise RuntimeError(
            f"E6 artifact not found: {e6_path}"
        )

    e6 = joblib.load(
        e6_path
    )

    if not isinstance(
        e6,
        dict
    ):

        raise RuntimeError(
            "E6 artifact is not a dictionary."
        )

    if "model" not in e6:

        raise RuntimeError(
            "E6 artifact missing model."
        )

    if "feature_names" not in e6:

        raise RuntimeError(
            "E6 artifact missing feature_names."
        )

    # E7
    e7_path = (
        PROJECT_ROOT
        / "treatment_probability_calibrator.pkl"
    )

    if not e7_path.exists():

        raise RuntimeError(
            f"E7 artifact not found: {e7_path}"
        )

    e7 = joblib.load(
        e7_path
    )

    if not isinstance(
        e7,
        dict
    ):

        raise RuntimeError(
            "E7 artifact is not a dictionary."
        )

    if "calibrator" not in e7:

        raise RuntimeError(
            "E7 artifact missing calibrator."
        )

    # E8
    e8_path = (
        PROJECT_ROOT
        / "treatment_probability_uncertainty.pkl"
    )

    if not e8_path.exists():

        raise RuntimeError(
            f"E8 artifact not found: {e8_path}"
        )

    e8 = joblib.load(
        e8_path
    )

    if not isinstance(
        e8,
        dict
    ):

        raise RuntimeError(
            "E8 artifact is not a dictionary."
        )

    # E9
    from ML.treatment_advisor.recovery_estimation import (
        load_recovery_model
    )

    e9 = load_recovery_model()

    if not isinstance(
        e9,
        dict
    ):

        raise RuntimeError(
            "E9 recovery artifact is invalid."
        )

    return (
        f"E6/E7/E8 artifacts and E9 recovery model "
        f"reloaded successfully. "
        f"E6 features: {len(e6['feature_names'])}."
    )


# ============================================================
# S2 - NEW ENCOUNTER COMPATIBILITY
# ============================================================

def scenario_new_encounter(
    encounter_id,
    context
):

    if not context:

        raise RuntimeError(
            "Patient context is empty."
        )

    required = [

        "encounter_id",

        "age",

        "gender",

        "disease_id",

        "severity_id",

        "symptoms",

        "symptom_vector"
    ]

    missing = [
        field
        for field in required
        if field not in context
    ]

    if missing:

        raise RuntimeError(
            f"Required E1 fields missing: {missing}"
        )

    normalized = normalize_context_for_model(
        context
    )

    vitals = normalized.get(
        "vitals",
        {}
    )

    required_vitals = [

        "temperature",

        "heart_rate",

        "respiratory_rate",

        "systolic_bp",

        "diastolic_bp",

        "spo2"
    ]

    missing_vitals = [
        field
        for field in required_vitals
        if field not in vitals
    ]

    if missing_vitals:

        raise RuntimeError(
            "Required vital fields missing: "
            f"{missing_vitals}"
        )

    return (
        f"Encounter {encounter_id} is compatible with "
        f"the current clinical-context representation."
    )


# ============================================================
# S3 - FUTURE RECORD SCHEMA
# ============================================================

def scenario_future_record(
    context
):

    future_record = deepcopy(
        context
    )

    future_record[
        "encounter_id"
    ] = (
        str(
            context[
                "encounter_id"
            ]
        )
        + "-FUTURE"
    )

    normalized = normalize_context_for_model(
        future_record
    )

    required = [

        "encounter_id",

        "age",

        "gender",

        "disease_id",

        "severity_id",

        "symptoms",

        "symptom_vector",

        "vitals"
    ]

    missing = [
        field
        for field in required
        if field not in normalized
    ]

    if missing:

        raise RuntimeError(
            f"Future record schema missing: {missing}"
        )

    if not isinstance(
        normalized["symptom_vector"],
        dict
    ):

        raise RuntimeError(
            "Future symptom_vector is not dictionary-compatible."
        )

    if not isinstance(
        normalized["vitals"],
        dict
    ):

        raise RuntimeError(
            "Future vitals are not dictionary-compatible."
        )

    return (
        "A simulated future encounter record retained "
        "the required E1 schema without database modification."
    )


# ============================================================
# S4 - FEATURE SCHEMA
# ============================================================

def scenario_feature_schema():

    path = (
        PROJECT_ROOT
        / "treatment_success_model.pkl"
    )

    artifact = joblib.load(
        path
    )

    feature_names = artifact[
        "feature_names"
    ]

    model = artifact[
        "model"
    ]

    if len(
        feature_names
    ) != len(
        set(feature_names)
    ):

        raise RuntimeError(
            "Duplicate E6 feature names detected."
        )

    model_features = getattr(
        model,
        "n_features_in_",
        None
    )

    if (
        model_features is not None
        and model_features
        != len(feature_names)
    ):

        raise RuntimeError(
            "Model feature count does not match "
            "stored feature schema."
        )

    return (
        f"E6 feature schema remains compatible: "
        f"{len(feature_names)} features."
    )


# ============================================================
# S5 - CALIBRATION COMPATIBILITY
# ============================================================

def scenario_calibration():

    from ML.treatment_advisor.probability_calibration import (
        calibrate_treatment_probability
    )

    result = (
        calibrate_treatment_probability(
            0.70
        )
    )

    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "E7 did not return a dictionary."
        )

    if "calibrated_success_probability" not in result:

        raise RuntimeError(
            "E7 output missing calibrated_success_probability."
        )

    probability = safe_float(
        result[
            "calibrated_success_probability"
        ]
    )

    if probability is None:

        raise RuntimeError(
            "E7 calibrated probability is not numeric."
        )

    if not (
        0.0
        <= probability
        <= 1.0
    ):

        raise RuntimeError(
            "E7 calibrated probability is outside [0,1]."
        )

    return (
        f"E7 calibration remained compatible; "
        f"test probability 0.70 -> {probability:.4f}."
    )


# ============================================================
# S6 - UNCERTAINTY COMPATIBILITY
# ============================================================

def scenario_uncertainty(
    pipeline
):

    from ML.treatment_advisor.uncertainty_estimation import (
        predict_treatment_with_uncertainty
    )

    treatment_id = pipeline[
        "treatment_ids"
    ][0]

    context = pipeline[
        "model_context"
    ]

    result = (
        predict_treatment_with_uncertainty(
            context,
            treatment_id
        )
    )

    required = [

        "raw_success_probability",

        "calibrated_success_probability",

        "uncertainty_lower",

        "uncertainty_upper",

        "uncertainty_std",

        "uncertainty_interval_width",

        "uncertainty_level"
    ]

    missing = [
        field
        for field in required
        if field not in result
    ]

    if missing:

        raise RuntimeError(
            f"E8 output missing: {missing}"
        )

    lower = safe_float(
        result[
            "uncertainty_lower"
        ]
    )

    upper = safe_float(
        result[
            "uncertainty_upper"
        ]
    )

    if (
        lower is None
        or upper is None
    ):

        raise RuntimeError(
            "E8 uncertainty interval is not numeric."
        )

    if lower > upper:

        raise RuntimeError(
            "E8 lower uncertainty bound exceeds upper bound."
        )

    return (
        f"E8 uncertainty remained compatible: "
        f"{lower:.4f}-{upper:.4f}, "
        f"level={result['uncertainty_level']}."
    )


# ============================================================
# S7 - RANKING COMPATIBILITY
# ============================================================

def scenario_ranking(
    pipeline
):

    ranking = pipeline[
        "ranking_output"
    ]

    if not isinstance(
        ranking,
        dict
    ):

        raise RuntimeError(
            "E12 output is not a dictionary."
        )

    if "ranked_treatments" not in ranking:

        raise RuntimeError(
            "E12 output missing ranked_treatments."
        )

    ranked = ranking[
        "ranked_treatments"
    ]

    if not isinstance(
        ranked,
        list
    ):

        raise RuntimeError(
            "E12 ranked_treatments is not a list."
        )

    return (
        f"E12 ranking interface remained compatible: "
        f"{len(ranked)} treatment(s) ranked."
    )


# ============================================================
# S8 - FINAL ADVISOR OUTPUT
# ============================================================

def scenario_final_advisor(
    pipeline
):

    """
    Validate the actual E13 module without assuming a
    nonexistent E12 wrapper function.

    E13 remains a presentation/orchestration layer.
    """

    try:

        from ML.treatment_advisor import (
            final_advisor_output
        )

    except Exception as e:

        raise RuntimeError(
            "E13 module could not be imported: "
            f"{type(e).__name__}: {e}"
        )

    if not hasattr(
        final_advisor_output,
        "generate_final_advisor_output"
    ):

        raise RuntimeError(
            "E13 generate_final_advisor_output() "
            "interface was not found."
        )

    generate_output = (
        final_advisor_output
        .generate_final_advisor_output
    )

    context = pipeline[
        "context"
    ]

    ranking = pipeline[
        "ranking_output"
    ]

    # E13 accepts regional context optionally.
    output = generate_output(

        ranking_output=ranking,

        patient_context=context,

        regional_context=None
    )

    if not isinstance(
        output,
        dict
    ):

        raise RuntimeError(
            "E13 did not return a dictionary."
        )

    required = [

        "advisor_version",

        "advisor_status",

        "encounter_id",

        "summary",

        "recommendations",

        "excluded_treatments",

        "disclaimer"
    ]

    missing = [
        field
        for field in required
        if field not in output
    ]

    if missing:

        raise RuntimeError(
            f"E13 output missing: {missing}"
        )

    return (
        f"E13 final advisor output remained compatible; "
        f"status={output['advisor_status']}."
    )


# ============================================================
# S9 - E4 CONFIGURATION COMPATIBILITY
# ============================================================

def scenario_configuration(
    pipeline
):

    from ML.treatment_advisor.e4_configuration import (
        enrich_candidates
    )

    enriched = enrich_candidates(

        pipeline[
            "eligible"
        ].copy(),

        pipeline[
            "hospital_id"
        ]
    )

    if (
        enriched is None
        or enriched.empty
    ):

        raise RuntimeError(
            "E4 configuration could not enrich "
            "future-compatible candidate records."
        )

    required_columns = [

        "treatment_id",

        "treatment_name"
    ]

    missing = [
        column
        for column in required_columns
        if column not in enriched.columns
    ]

    if missing:

        raise RuntimeError(
            f"E4 enriched output missing: {missing}"
        )

    return (
        f"E4 configuration reload remained compatible: "
        f"{len(enriched)} treatment(s) enriched."
    )


# ============================================================
# S10 - DATABASE SAFETY
# ============================================================

def scenario_database_safety(
    encounter_id
):

    engine = get_database_engine()

    query = """
        SELECT COUNT(*) AS record_count
        FROM patient_encounter
        WHERE encounter_id = %(encounter_id)s
    """

    before_df = pd.read_sql(
        query,
        engine,
        params={
            "encounter_id": encounter_id
        }
    )

    before_count = int(
        before_df.iloc[0][
            "record_count"
        ]
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # No INSERT / UPDATE / DELETE operation is performed.
    # --------------------------------------------------------

    after_df = pd.read_sql(
        query,
        engine,
        params={
            "encounter_id": encounter_id
        }
    )

    after_count = int(
        after_df.iloc[0][
            "record_count"
        ]
    )

    if before_count != after_count:

        raise RuntimeError(
            "Database state changed during E17."
        )

    return (
        "E17 performed read-only database access; "
        "database state remained unchanged."
    )


# ============================================================
# RUN SCENARIO
# ============================================================

def run_scenario(
    scenario_id,
    scenario_name,
    function
):

    print()
    print(
        f"{scenario_id} - {scenario_name}"
    )

    result = {

        "scenario_id": scenario_id,

        "scenario_name": scenario_name,

        "status": "FAILED",

        "message": ""
    }

    try:

        message = function()

        result[
            "status"
        ] = "PASSED"

        result[
            "message"
        ] = str(
            message
        )

    except Exception as e:

        result[
            "status"
        ] = "FAILED"

        result[
            "message"
        ] = (
            f"{type(e).__name__}: {e}"
        )

    print(
        f"Status : {result['status']}"
    )

    print(
        f"Message: {result['message']}"
    )

    return result


# ============================================================
# MAIN E17 VALIDATION
# ============================================================

def run_e17_validation():

    print()
    print("=" * 75)
    print(
        "E17 - CONTINUOUS-UPDATE COMPATIBILITY VALIDATION"
    )
    print("=" * 75)

    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------

    (
        encounter_id,
        context,
        candidates,
        hospital_id
    ) = find_baseline_encounter()

    print()
    print(
        f"Baseline encounter : {encounter_id}"
    )

    print(
        f"Hospital            : {hospital_id}"
    )

    print(
        f"Disease             : "
        f"{context.get('disease_id')}"
    )

    print(
        f"Severity            : "
        f"{context.get('severity_id')}"
    )

    # --------------------------------------------------------
    # Build actual frozen pipeline once.
    #
    # This also ensures S6-S9 use a valid pipeline.
    # --------------------------------------------------------

    pipeline = build_pipeline(
        encounter_id
    )

    # --------------------------------------------------------
    # Scenarios
    # --------------------------------------------------------

    results = []

    results.append(
        run_scenario(
            "S1",
            "Existing Artifact Reload",
            scenario_artifact_reload
        )
    )

    results.append(
        run_scenario(
            "S2",
            "New Encounter Compatibility",
            lambda:
                scenario_new_encounter(
                    encounter_id,
                    context
                )
        )
    )

    results.append(
        run_scenario(
            "S3",
            "Future Record Schema Compatibility",
            lambda:
                scenario_future_record(
                    context
                )
        )
    )

    results.append(
        run_scenario(
            "S4",
            "Feature Schema Compatibility",
            scenario_feature_schema
        )
    )

    results.append(
        run_scenario(
            "S5",
            "Probability Calibration Compatibility",
            scenario_calibration
        )
    )

    results.append(
        run_scenario(
            "S6",
            "Uncertainty Compatibility",
            lambda:
                scenario_uncertainty(
                    pipeline
                )
        )
    )

    results.append(
        run_scenario(
            "S7",
            "Treatment Ranking Compatibility",
            lambda:
                scenario_ranking(
                    pipeline
                )
        )
    )

    results.append(
        run_scenario(
            "S8",
            "Final Advisor Output Compatibility",
            lambda:
                scenario_final_advisor(
                    pipeline
                )
        )
    )

    results.append(
        run_scenario(
            "S9",
            "Configuration Reload Compatibility",
            lambda:
                scenario_configuration(
                    pipeline
                )
        )
    )

    results.append(
        run_scenario(
            "S10",
            "Database Safety",
            lambda:
                scenario_database_safety(
                    encounter_id
                )
        )
    )

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

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

    status = (
        "PASSED"
        if failed == 0
        else "REVIEW_REQUIRED"
    )

    output = {

        "evaluation_version": E17_VERSION,

        "evaluation_status": status,

        "baseline_encounter": encounter_id,

        "hospital_id": hospital_id,

        "total_scenarios": total,

        "passed_scenarios": passed,

        "failed_scenarios": failed,

        "pass_rate": pass_rate,

        "scenario_results": results,

        "database_modified": False,

        "continuous_learning_implemented": False,

        "interpretation": (
            "E17 validates compatibility of the existing "
            "treatment-advisor architecture with future "
            "clinical records, model artifacts, feature "
            "schemas, calibration, uncertainty estimation, "
            "treatment ranking, final advisor output, and "
            "configuration updates. The validation does not "
            "implement automatic continuous learning or "
            "automatic retraining. All database operations "
            "performed by E17 are read-only."
        )
    }

    return output


# ============================================================
# OUTPUT VALIDATION
# ============================================================

def validate_e17_output(
    output
):

    required = [

        "evaluation_version",

        "evaluation_status",

        "baseline_encounter",

        "hospital_id",

        "total_scenarios",

        "passed_scenarios",

        "failed_scenarios",

        "pass_rate",

        "scenario_results",

        "database_modified",

        "continuous_learning_implemented",

        "interpretation"
    ]

    for field in required:

        if field not in output:

            raise RuntimeError(
                f"E17 output missing '{field}'."
            )

    if (
        output[
            "passed_scenarios"
        ]
        +
        output[
            "failed_scenarios"
        ]
        !=
        output[
            "total_scenarios"
        ]
    ):

        raise RuntimeError(
            "E17 scenario counts are inconsistent."
        )

    if output[
        "database_modified"
    ]:

        raise RuntimeError(
            "E17 incorrectly reports database modification."
        )

    if output[
        "continuous_learning_implemented"
    ]:

        raise RuntimeError(
            "E17 incorrectly claims continuous learning."
        )

    return True


# ============================================================
# DISPLAY
# ============================================================

def display_results(
    output
):

    print()
    print("=" * 75)
    print(
        "E17 CONTINUOUS-UPDATE COMPATIBILITY RESULTS"
    )
    print("=" * 75)

    print()
    print(
        f"Evaluation status : "
        f"{output['evaluation_status']}"
    )

    print(
        f"Baseline encounter: "
        f"{output['baseline_encounter']}"
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

    print(
        f"Database modified : "
        f"{output['database_modified']}"
    )

    print(
        "Continuous learning implemented: "
        f"{output['continuous_learning_implemented']}"
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
            f"Status : {result['status']}"
        )

        print(
            f"Message: {result['message']}"
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

    print()
    print("=" * 75)

    if (
        output[
            "evaluation_status"
        ]
        == "PASSED"
    ):

        print(
            "E17 VALIDATION: PASSED"
        )

    else:

        print(
            "E17 VALIDATION: REVIEW REQUIRED"
        )

    print("=" * 75)


# ============================================================
# MAIN
# ============================================================

def main():

    output = run_e17_validation()

    validate_e17_output(
        output
    )

    display_results(
        output
    )

    return output


if __name__ == "__main__":

    main()
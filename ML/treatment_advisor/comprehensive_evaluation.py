"""
E14 - Comprehensive Treatment Advisor Evaluation

Purpose
-------
Evaluate the complete E1 -> E13 treatment-advisor pipeline
across multiple encounters.

E14 does NOT:
    - train a new model
    - modify E1-E13 logic
    - change treatment rankings
    - tune model parameters
    - claim clinical validity
    - establish causal treatment effects
    - validate treatment recommendations clinically

E14 is an analytical and engineering evaluation layer.

The purpose is to determine whether the existing treatment
advisor consistently produces structurally valid and
internally coherent outputs across multiple encounters.

Important
---------
An encounter for which E2 correctly produces no treatment
candidates is NOT treated as a pipeline failure.

This is represented as:

    NO_CANDIDATES

This means:

    - E1 patient context was valid
    - E2 executed correctly
    - no configured treatment mapping was available
    - downstream treatment-ranking stages were not applicable

This is different from:

    FAILED

which represents an unexpected technical or validation failure.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import math

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

E14_VERSION = "E14.2"

DEFAULT_SAMPLE_SIZE = 10

E14_DISCLAIMER = (
    "E14 evaluates engineering and analytical consistency of "
    "the project treatment-advisor pipeline. It does not "
    "establish clinical validity, treatment efficacy, causal "
    "treatment effects, or autonomous prescribing capability."
)


# ============================================================
# BASIC HELPERS
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

        value = float(value)

        if math.isfinite(value):
            return value

    except (
        TypeError,
        ValueError
    ):

        pass

    return default


# ============================================================
# ENCOUNTER SELECTION
# ============================================================

def select_test_encounters(
    sample_size: int = DEFAULT_SAMPLE_SIZE
):
    """
    Select multiple encounters for E14 evaluation.

    Encounters are selected from the project database.

    The selection is deterministic so that repeated evaluation
    runs use the same encounter set.
    """

    from database import get_engine

    engine = get_engine()

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
        LIMIT %(sample_size)s
    """

    df = pd.read_sql(
        query,
        engine,
        params={
            "sample_size": int(sample_size)
        }
    )

    if df.empty:

        raise RuntimeError(
            "E14 could not find any encounters."
        )

    return df


# ============================================================
# SINGLE ENCOUNTER EVALUATION
# ============================================================

def evaluate_single_encounter(
    encounter_id: str
):
    """
    Run E1 -> E13 for one encounter.

    Returns a structured evaluation record.

    Possible statuses:

        PASSED
            Complete E1-E13 pipeline succeeded.

        NO_CANDIDATES
            E1 and E2 executed successfully, but E2 found
            no configured treatment candidates.

        FAILED
            Unexpected technical or validation failure.
    """

    result = {

        "encounter_id": encounter_id,

        "status": "FAILED",

        "e1": False,
        "e2": False,
        "e3": False,
        "e4": False,
        "e5": False,
        "e6": False,
        "e7": False,
        "e8": False,
        "e9": False,
        "e10": False,
        "e11": False,
        "e12": False,
        "e13": False,

        "ranked_treatments": 0,

        "excluded_treatments": 0,

        "top_treatment": None,

        "top_score": None,

        "error": None,

        "no_candidate_reason": None
    }

    try:

        # ====================================================
        # E1
        # ====================================================

        from ML.treatment_advisor.patient_context import (
            load_patient_context,
            validate_patient_context
        )

        context = load_patient_context(
            encounter_id
        )

        validation = validate_patient_context(
            context
        )

        if not validation.get(
            "valid",
            False
        ):

            raise RuntimeError(
                "E1 patient context validation failed."
            )

        result["e1"] = True

        # ====================================================
        # E2
        # ====================================================

        from ML.treatment_advisor.candidate_treatments import (
            generate_candidates_for_encounter
        )

        (
            context,
            candidates,
            candidate_records
        ) = generate_candidates_for_encounter(
            encounter_id
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Empty candidates are a valid outcome when the
        # knowledge configuration has no treatment mapping
        # for the patient's disease/severity combination.
        #
        # Do NOT classify this as a technical failure.
        # ----------------------------------------------------

        result["e2"] = True

        if (
            candidates is None
            or candidates.empty
        ):

            disease_id = context.get(
                "disease_id"
            )

            severity_id = context.get(
                "severity_id"
            )

            result["status"] = (
                "NO_CANDIDATES"
            )

            result[
                "no_candidate_reason"
            ] = (
                "No configured treatment mapping exists "
                f"for disease {disease_id} and "
                f"severity {severity_id}."
            )

            return result

        # ====================================================
        # E3
        # ====================================================

        from ML.treatment_advisor.clinical_eligibility import (
            load_treatment_master,
            evaluate_candidates
        )

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

        result["e3"] = True

        # ====================================================
        # HOSPITAL
        # ====================================================

        from database import get_engine

        engine = get_engine()

        hospital_query = """
            SELECT
                hospital_id
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
                "Hospital not found."
            )

        hospital_id = str(
            hospital_df.iloc[0]["hospital_id"]
        )

        # ====================================================
        # E4
        # ====================================================

        from ML.treatment_advisor.e4_configuration import (
            enrich_candidates
        )

        enriched = enrich_candidates(
            eligible,
            hospital_id
        )

        if (
            enriched is None
            or enriched.empty
        ):

            raise RuntimeError(
                "E4 produced no candidates."
            )

        result["e4"] = True

        # ====================================================
        # E5
        # ====================================================

        regional_context = None

        try:

            from ML.treatment_advisor.regional_epidemiology import (
                get_regional_epidemiology
            )

            regional_context = (
                get_regional_epidemiology(
                    hospital_id=hospital_id,
                    disease_id=context.get(
                        "disease_id"
                    )
                )
            )

            result["e5"] = True

        except Exception:

            # E5 is contextual and does not currently
            # determine whether treatment ranking can proceed.

            result["e5"] = False

        # ====================================================
        # TREATMENT IDS
        # ====================================================

        treatment_ids = (
            enriched[
                "treatment_id"
            ]
            .dropna()
            .astype(str)
            .tolist()
        )

        if not treatment_ids:

            raise RuntimeError(
                "No treatment IDs available after E4."
            )

        # ====================================================
        # E7 + E8
        # ====================================================

        from ML.treatment_advisor.uncertainty_estimation import (
            predict_treatment_with_uncertainty
        )

        e7_results = []
        e8_results = []

        for treatment_id in treatment_ids:

            prediction = (
                predict_treatment_with_uncertainty(
                    context,
                    treatment_id
                )
            )

            e7_results.append({

                "treatment_id": treatment_id,

                "raw_success_probability": (
                    prediction[
                        "raw_success_probability"
                    ]
                ),

                "calibrated_success_probability": (
                    prediction[
                        "calibrated_success_probability"
                    ]
                ),

                "calibration_method": (
                    "E7 probability calibration"
                )
            })

            e8_results.append(
                prediction
            )

        # ----------------------------------------------------
        # E6-E8 completed successfully through E8.
        # E6 is invoked internally by E8.
        # ----------------------------------------------------

        result["e6"] = True
        result["e7"] = True
        result["e8"] = True

        # ====================================================
        # E9
        # ====================================================

        from ML.treatment_advisor.recovery_estimation import (
            predict_recovery_for_treatments
        )

        e9_results = (
            predict_recovery_for_treatments(
                context,
                treatment_ids
            )
        )

        if not isinstance(
            e9_results,
            list
        ):

            raise RuntimeError(
                "E9 did not return a list."
            )

        result["e9"] = True

        # ====================================================
        # E10
        # ====================================================

        from ML.treatment_advisor.risk_complication import (
            assess_risk_for_treatments
        )

        e10_results = (
            assess_risk_for_treatments(
                context,
                enriched
            )
        )

        if not isinstance(
            e10_results,
            list
        ):

            raise RuntimeError(
                "E10 did not return a list."
            )

        result["e10"] = True

        # ====================================================
        # E11
        # ====================================================

        from ML.treatment_advisor.shap_explainability import (
            explain_treatments
        )

        e11_results = explain_treatments(
            context,
            treatment_ids
        )

        if not isinstance(
            e11_results,
            list
        ):

            raise RuntimeError(
                "E11 did not return a list."
            )

        result["e11"] = True

        # ====================================================
        # E12
        # ====================================================

        from ML.treatment_advisor.treatment_ranking import (
            rank_treatments,
            validate_ranking_output
        )

        ranking_output = rank_treatments(
            enriched_candidates=enriched,
            e7_results=e7_results,
            e8_results=e8_results,
            e9_results=e9_results,
            e10_results=e10_results,
            e11_results=e11_results
        )

        validate_ranking_output(
            ranking_output
        )

        result["e12"] = True

        result[
            "ranked_treatments"
        ] = len(
            ranking_output[
                "ranked_treatments"
            ]
        )

        result[
            "excluded_treatments"
        ] = len(
            ranking_output[
                "excluded_treatments"
            ]
        )

        if ranking_output[
            "ranked_treatments"
        ]:

            top = ranking_output[
                "ranked_treatments"
            ][0]

            result[
                "top_treatment"
            ] = top.get(
                "treatment_id"
            )

            result[
                "top_score"
            ] = safe_float(
                top.get(
                    "final_score"
                )
            )

        # ====================================================
        # E13
        # ====================================================

        from ML.treatment_advisor.final_advisor_output import (
            generate_final_advisor_output,
            validate_final_advisor_output
        )

        final_output = (
            generate_final_advisor_output(
                ranking_output=ranking_output,
                patient_context=context,
                regional_context=regional_context
            )
        )

        validate_final_advisor_output(
            final_output
        )

        result["e13"] = True

        # ====================================================
        # SUCCESS
        # ====================================================

        result["status"] = "PASSED"

    except Exception as e:

        result["status"] = "FAILED"

        result["error"] = (
            f"{type(e).__name__}: {str(e)}"
        )

    return result


# ============================================================
# E14 RESULT VALIDATION
# ============================================================

def validate_e14_record(
    record: Dict[str, Any]
):
    """
    Validate an individual E14 evaluation record.
    """

    if not isinstance(
        record,
        dict
    ):
        return False

    required_stage_fields = [
        "e1",
        "e2",
        "e3",
        "e4",
        "e5",
        "e6",
        "e7",
        "e8",
        "e9",
        "e10",
        "e11",
        "e12",
        "e13"
    ]

    for field in required_stage_fields:

        if field not in record:

            return False

    status = record.get(
        "status"
    )

    if status not in {
        "PASSED",
        "NO_CANDIDATES",
        "FAILED"
    }:

        return False

    # ========================================================
    # NO_CANDIDATES validation
    # ========================================================

    if status == "NO_CANDIDATES":

        # E1 and E2 must have succeeded.
        if not record["e1"]:
            return False

        if not record["e2"]:
            return False

        # Downstream stages are not applicable.
        for stage in [
            "e3",
            "e4",
            "e6",
            "e7",
            "e8",
            "e9",
            "e10",
            "e11",
            "e12",
            "e13"
        ]:

            if record[stage]:
                return False

        if not record.get(
            "no_candidate_reason"
        ):

            return False

        return True

    # ========================================================
    # PASSED validation
    # ========================================================

    if status == "PASSED":

        for stage in [
            "e1",
            "e2",
            "e3",
            "e4",
            "e6",
            "e7",
            "e8",
            "e9",
            "e10",
            "e11",
            "e12",
            "e13"
        ]:

            if not record[stage]:
                return False

    # ========================================================
    # Rank count
    # ========================================================

    ranked_count = record.get(
        "ranked_treatments",
        0
    )

    if not isinstance(
        ranked_count,
        int
    ):
        return False

    if ranked_count < 0:
        return False

    # ========================================================
    # Score
    # ========================================================

    score = record.get(
        "top_score"
    )

    if score is not None:

        score = safe_float(
            score
        )

        if score is None:
            return False

        if not (
            0.0
            <= score
            <= 1.0
        ):
            return False

    return True


# ============================================================
# AGGREGATE E14 METRICS
# ============================================================

def calculate_e14_metrics(
    records: List[Dict[str, Any]]
):
    """
    Calculate aggregate E14 metrics.

    Categories:

        PASSED
            Complete E1-E13 execution.

        NO_CANDIDATES
            Valid E1/E2 execution with no configured treatment
            mapping.

        FAILED
            Unexpected technical or validation failure.
    """

    if not records:

        return {

            "total_encounters": 0,

            "passed_encounters": 0,

            "no_candidate_encounters": 0,

            "failed_encounters": 0,

            "advisor_completion_rate": 0.0,

            "no_candidate_rate": 0.0,

            "unexpected_failure_rate": 0.0,

            "overall_engineering_validation_rate": 0.0,

            "stage_pass_rates": {},

            "average_ranked_treatments": 0.0,

            "average_top_score": None
        }

    total = len(
        records
    )

    passed = sum(
        record.get(
            "status"
        ) == "PASSED"
        for record in records
    )

    no_candidates = sum(
        record.get(
            "status"
        ) == "NO_CANDIDATES"
        for record in records
    )

    failed = sum(
        record.get(
            "status"
        ) == "FAILED"
        for record in records
    )

    # ========================================================
    # Stage pass rates
    #
    # E5 is contextual and may fail without invalidating
    # the treatment-ranking pipeline.
    # ========================================================

    stage_names = [
        "e1",
        "e2",
        "e3",
        "e4",
        "e5",
        "e6",
        "e7",
        "e8",
        "e9",
        "e10",
        "e11",
        "e12",
        "e13"
    ]

    stage_pass_rates = {}

    for stage in stage_names:

        count = sum(
            bool(
                record.get(
                    stage,
                    False
                )
            )
            for record in records
        )

        stage_pass_rates[
            stage
        ] = (
            count
            / total
        )

    # ========================================================
    # Ranked treatment counts
    # ========================================================

    ranked_counts = [
        record.get(
            "ranked_treatments",
            0
        )
        for record in records
    ]

    # ========================================================
    # Top scores
    # ========================================================

    top_scores = []

    for record in records:

        score = safe_float(
            record.get(
                "top_score"
            )
        )

        if score is not None:

            top_scores.append(
                score
            )

    # ========================================================
    # Engineering validation rate
    #
    # A valid NO_CANDIDATES outcome is NOT an unexpected
    # engineering failure.
    #
    # Therefore:
    #
    #     engineering validation rate =
    #         (PASSED + NO_CANDIDATES) / total
    #
    # ========================================================

    valid_outcomes = (
        passed
        + no_candidates
    )

    return {

        "total_encounters": total,

        "passed_encounters": passed,

        "no_candidate_encounters": no_candidates,

        "failed_encounters": failed,

        "advisor_completion_rate": (
            passed
            / total
        ),

        "no_candidate_rate": (
            no_candidates
            / total
        ),

        "unexpected_failure_rate": (
            failed
            / total
        ),

        "overall_engineering_validation_rate": (
            valid_outcomes
            / total
        ),

        "stage_pass_rates": (
            stage_pass_rates
        ),

        "average_ranked_treatments": (
            float(
                np.mean(
                    ranked_counts
                )
            )
        ),

        "average_top_score": (
            float(
                np.mean(
                    top_scores
                )
            )
            if top_scores
            else None
        )
    }


# ============================================================
# RUN E14
# ============================================================

def run_e14_evaluation(
    sample_size: int = DEFAULT_SAMPLE_SIZE
):
    """
    Run the comprehensive E14 evaluation.
    """

    print()
    print("=" * 75)
    print("E14 - COMPREHENSIVE TREATMENT ADVISOR EVALUATION")
    print("=" * 75)

    print()
    print(
        f"Evaluation sample size : {sample_size}"
    )

    # ========================================================
    # SELECT ENCOUNTERS
    # ========================================================

    encounters = (
        select_test_encounters(
            sample_size
        )
    )

    print(
        f"Encounters selected    : "
        f"{len(encounters)}"
    )

    # ========================================================
    # EVALUATE EACH ENCOUNTER
    # ========================================================

    records = []

    for position, (_, row) in enumerate(
        encounters.iterrows(),
        start=1
    ):

        encounter_id = str(
            row[
                "encounter_id"
            ]
        )

        print()
        print(
            f"[{position}/{len(encounters)}] "
            f"Evaluating {encounter_id}..."
        )

        record = (
            evaluate_single_encounter(
                encounter_id
            )
        )

        records.append(
            record
        )

        # ----------------------------------------------------
        # PASSED
        # ----------------------------------------------------

        if record[
            "status"
        ] == "PASSED":

            print(
                "  RESULT: PASSED"
            )

            print(
                f"  Ranked treatments: "
                f"{record['ranked_treatments']}"
            )

            print(
                f"  Top treatment: "
                f"{record['top_treatment']}"
            )

        # ----------------------------------------------------
        # NO CANDIDATES
        # ----------------------------------------------------

        elif record[
            "status"
        ] == "NO_CANDIDATES":

            print(
                "  RESULT: NO_CANDIDATES"
            )

            print(
                f"  Reason: "
                f"{record['no_candidate_reason']}"
            )

        # ----------------------------------------------------
        # FAILURE
        # ----------------------------------------------------

        else:

            print(
                "  RESULT: FAILED"
            )

            print(
                f"  Error: "
                f"{record['error']}"
            )

    # ========================================================
    # VALIDATE RECORDS
    # ========================================================

    for record in records:

        if not validate_e14_record(
            record
        ):

            raise RuntimeError(
                "E14 generated an invalid "
                "evaluation record."
            )

    # ========================================================
    # METRICS
    # ========================================================

    metrics = calculate_e14_metrics(
        records
    )

    # ========================================================
    # E14 STATUS
    #
    # PASSED when:
    #
    #     - at least one encounter was evaluated
    #     - there are zero unexpected failures
    #
    # NO_CANDIDATES does not count as failure.
    # ========================================================

    if (
        metrics[
            "total_encounters"
        ] > 0
        and metrics[
            "failed_encounters"
        ] == 0
    ):

        evaluation_status = "PASSED"

    else:

        evaluation_status = "REVIEW_REQUIRED"

    # ========================================================
    # BUILD OUTPUT
    # ========================================================

    evaluation_output = {

        "evaluation_version": E14_VERSION,

        "evaluation_status": (
            evaluation_status
        ),

        "evaluation_scope": (
            "Multi-encounter engineering and analytical "
            "evaluation of the E1-E13 treatment-advisor "
            "pipeline."
        ),

        "sample_size": sample_size,

        "metrics": metrics,

        "encounter_results": records,

        "interpretation": (
            "E14 evaluates whether the treatment-advisor "
            "pipeline produces structurally valid and "
            "internally coherent outputs across multiple "
            "encounters. Encounters with no configured "
            "treatment candidates are treated as valid "
            "NO_CANDIDATES outcomes rather than technical "
            "failures. E14 does not establish clinical "
            "validity or treatment efficacy."
        ),

        "disclaimer": E14_DISCLAIMER
    }

    return evaluation_output


# ============================================================
# DISPLAY E14
# ============================================================

def display_e14_results(
    evaluation_output: Dict[str, Any]
):
    """
    Display E14 results.
    """

    metrics = evaluation_output[
        "metrics"
    ]

    print()
    print("=" * 75)
    print("E14 EVALUATION RESULTS")
    print("=" * 75)

    print()
    print(
        f"Evaluation status              : "
        f"{evaluation_output['evaluation_status']}"
    )

    print(
        f"Total encounters               : "
        f"{metrics['total_encounters']}"
    )

    print(
        f"Completed advisor evaluations  : "
        f"{metrics['passed_encounters']}"
    )

    print(
        f"No-candidate encounters        : "
        f"{metrics['no_candidate_encounters']}"
    )

    print(
        f"Unexpected pipeline failures   : "
        f"{metrics['failed_encounters']}"
    )

    print(
        f"Advisor completion rate        : "
        f"{metrics['advisor_completion_rate'] * 100:.2f}%"
    )

    print(
        f"No-candidate rate              : "
        f"{metrics['no_candidate_rate'] * 100:.2f}%"
    )

    print(
        f"Unexpected failure rate        : "
        f"{metrics['unexpected_failure_rate'] * 100:.2f}%"
    )

    print(
        f"Engineering validation rate    : "
        f"{metrics['overall_engineering_validation_rate'] * 100:.2f}%"
    )

    print(
        f"Average ranked treatments      : "
        f"{metrics['average_ranked_treatments']:.2f}"
    )

    if metrics[
        "average_top_score"
    ] is not None:

        print(
            f"Average top score              : "
            f"{metrics['average_top_score']:.4f}"
        )

    # ========================================================
    # Stage pass rates
    # ========================================================

    print()
    print("-" * 75)
    print("STAGE PASS RATES")
    print("-" * 75)

    for stage, rate in (
        metrics[
            "stage_pass_rates"
        ].items()
    ):

        print(
            f"{stage.upper():<6}: "
            f"{rate * 100:.2f}%"
        )

    # ========================================================
    # Encounter summary
    # ========================================================

    print()
    print("=" * 75)
    print("ENCOUNTER RESULTS")
    print("=" * 75)

    for record in evaluation_output[
        "encounter_results"
    ]:

        print()
        print(
            f"Encounter : "
            f"{record['encounter_id']}"
        )

        print(
            f"Status    : "
            f"{record['status']}"
        )

        print(
            f"Ranked    : "
            f"{record['ranked_treatments']}"
        )

        print(
            f"Top       : "
            f"{record['top_treatment']}"
        )

        if record[
            "top_score"
        ] is not None:

            print(
                f"Score     : "
                f"{record['top_score']:.4f}"
            )

        if record[
            "no_candidate_reason"
        ]:

            print(
                f"Reason    : "
                f"{record['no_candidate_reason']}"
            )

        if record[
            "error"
        ]:

            print(
                f"Error     : "
                f"{record['error']}"
            )

    # ========================================================
    # Disclaimer
    # ========================================================

    print()
    print("=" * 75)
    print("E14 INTERPRETATION")
    print("=" * 75)

    print(
        evaluation_output[
            "interpretation"
        ]
    )

    print()
    print(
        evaluation_output[
            "disclaimer"
        ]
    )


# ============================================================
# VALIDATE COMPLETE E14 OUTPUT
# ============================================================

def validate_e14_output(
    evaluation_output: Dict[str, Any]
):
    """
    Validate the complete E14 output.
    """

    if not isinstance(
        evaluation_output,
        dict
    ):

        raise RuntimeError(
            "E14 output must be a dictionary."
        )

    required_fields = [
        "evaluation_version",
        "evaluation_status",
        "evaluation_scope",
        "sample_size",
        "metrics",
        "encounter_results",
        "interpretation",
        "disclaimer"
    ]

    for field in required_fields:

        if field not in evaluation_output:

            raise RuntimeError(
                f"E14 output missing '{field}'."
            )

    metrics = evaluation_output[
        "metrics"
    ]

    records = evaluation_output[
        "encounter_results"
    ]

    # ========================================================
    # Encounter count
    # ========================================================

    if metrics[
        "total_encounters"
    ] != len(records):

        raise RuntimeError(
            "E14 encounter count does not match "
            "evaluation records."
        )

    # ========================================================
    # Count consistency
    # ========================================================

    calculated_passed = sum(
        record.get(
            "status"
        ) == "PASSED"
        for record in records
    )

    calculated_no_candidates = sum(
        record.get(
            "status"
        ) == "NO_CANDIDATES"
        for record in records
    )

    calculated_failed = sum(
        record.get(
            "status"
        ) == "FAILED"
        for record in records
    )

    if calculated_passed != metrics[
        "passed_encounters"
    ]:

        raise RuntimeError(
            "E14 passed encounter count is inconsistent."
        )

    if calculated_no_candidates != metrics[
        "no_candidate_encounters"
    ]:

        raise RuntimeError(
            "E14 no-candidate count is inconsistent."
        )

    if calculated_failed != metrics[
        "failed_encounters"
    ]:

        raise RuntimeError(
            "E14 failed encounter count is inconsistent."
        )

    # ========================================================
    # Pass rates
    # ========================================================

    for metric_name in [
        "advisor_completion_rate",
        "no_candidate_rate",
        "unexpected_failure_rate",
        "overall_engineering_validation_rate"
    ]:

        value = safe_float(
            metrics.get(
                metric_name
            )
        )

        if value is None:

            raise RuntimeError(
                f"E14 metric '{metric_name}' is invalid."
            )

        if not (
            0.0
            <= value
            <= 1.0
        ):

            raise RuntimeError(
                f"E14 metric '{metric_name}' "
                "is outside [0,1]."
            )

    # ========================================================
    # Verify rate calculations
    # ========================================================

    total = metrics[
        "total_encounters"
    ]

    if total > 0:

        expected_engineering_rate = (
            (
                metrics[
                    "passed_encounters"
                ]
                +
                metrics[
                    "no_candidate_encounters"
                ]
            )
            / total
        )

        if not np.isclose(
            metrics[
                "overall_engineering_validation_rate"
            ],
            expected_engineering_rate,
            atol=1e-9
        ):

            raise RuntimeError(
                "E14 engineering validation rate "
                "is inconsistent."
            )

    # ========================================================
    # Stage rates
    # ========================================================

    for stage, rate in (
        metrics[
            "stage_pass_rates"
        ].items()
    ):

        if not (
            0.0
            <= float(rate)
            <= 1.0
        ):

            raise RuntimeError(
                f"E14 stage pass rate for "
                f"{stage} is invalid."
            )

    # ========================================================
    # Individual records
    # ========================================================

    for record in records:

        if not validate_e14_record(
            record
        ):

            raise RuntimeError(
                "E14 contains an invalid "
                "encounter record."
            )

    # ========================================================
    # Status consistency
    # ========================================================

    if (
        total > 0
        and metrics[
            "failed_encounters"
        ] == 0
    ):

        if evaluation_output[
            "evaluation_status"
        ] != "PASSED":

            raise RuntimeError(
                "E14 status should be PASSED because "
                "there are no unexpected failures."
            )

    if metrics[
        "failed_encounters"
    ] > 0:

        if evaluation_output[
            "evaluation_status"
        ] != "REVIEW_REQUIRED":

            raise RuntimeError(
                "E14 status should be REVIEW_REQUIRED "
                "when unexpected failures exist."
            )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 75)
    print("E14 - COMPREHENSIVE EVALUATION")
    print("=" * 75)

    evaluation_output = (
        run_e14_evaluation(
            sample_size=DEFAULT_SAMPLE_SIZE
        )
    )

    validate_e14_output(
        evaluation_output
    )

    display_e14_results(
        evaluation_output
    )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    if (
        evaluation_output[
            "evaluation_status"
        ] == "PASSED"
    ):

        print()
        print("=" * 75)
        print("E14 VALIDATION: PASSED")
        print("=" * 75)

    else:

        print()
        print("=" * 75)
        print("E14 VALIDATION: REVIEW REQUIRED")
        print("=" * 75)

        print(
            "One or more encounters experienced "
            "unexpected pipeline failures."
        )

    return evaluation_output


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
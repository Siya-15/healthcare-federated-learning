"""
E13 - Final Treatment Advisor Output

Purpose
-------
Convert the E12 treatment-ranking output into a clean,
frontend/backend-ready treatment advisor response.

Pipeline:

    E1 Patient Context
        ↓
    E2 Candidate Treatments
        ↓
    E3 Clinical Eligibility
        ↓
    E4 Configuration
        ↓
    E5 Regional Epidemiology
        ↓
    E6 Treatment Success
        ↓
    E7 Probability Calibration
        ↓
    E8 Uncertainty
        ↓
    E9 Recovery Estimation
        ↓
    E10 Risk & Complications
        ↓
    E11 SHAP Explainability
        ↓
    E12 Final Treatment Ranking
        ↓
    E13 Final Advisor Output

Important
---------
E13 does NOT:
    - train a new model
    - modify treatment rankings
    - calculate a new treatment score
    - make a prescribing decision
    - make causal treatment-effect claims
    - claim medical validation

E13 is an output and presentation layer.

The E12 ranking remains the source of treatment ordering.
E5 regional epidemiology is presented as contextual information
and is NOT converted into a treatment ranking score.
"""


from typing import Any, Dict, List, Optional
import math


# ============================================================
# CONFIGURATION
# ============================================================

E13_VERSION = "E13.1"

ADVISOR_DISCLAIMER = (
    "This treatment advisor is a project-level AI decision-support "
    "prototype. It does not provide autonomous prescribing, does "
    "not establish causal treatment effects, and does not replace "
    "clinical judgment or validated clinical guidelines."
)

UNKNOWN_VALUE = "UNKNOWN"


# ============================================================
# BASIC HELPERS
# ============================================================

def _safe_float(
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


def _safe_string(
    value: Any,
    default: str = UNKNOWN_VALUE
):
    """
    Safely convert a value to string.
    """

    if value is None:
        return default

    text = str(value).strip()

    if not text:
        return default

    return text


def _safe_list(
    value: Any
):
    """
    Ensure an output field is represented as a list.
    """

    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


# ============================================================
# PATIENT CONTEXT
# ============================================================

def build_patient_context_summary(
    patient_context: Optional[Dict[str, Any]]
):
    """
    Build a frontend-safe patient context summary.

    The complete raw patient record is intentionally not copied
    into the final advisor response.

    Only the clinical context already provided to the advisor
    is exposed here.
    """

    if not isinstance(
        patient_context,
        dict
    ):
        return {}

    vitals = patient_context.get(
        "vitals",
        {}
    )

    if not isinstance(
        vitals,
        dict
    ):
        vitals = {}

    symptoms = patient_context.get(
        "symptoms",
        []
    )

    return {
        "encounter_id": patient_context.get(
            "encounter_id"
        ),

        "age": patient_context.get(
            "age"
        ),

        "gender": patient_context.get(
            "gender"
        ),

        "disease_id": patient_context.get(
            "disease_id"
        ),

        "severity_id": patient_context.get(
            "severity_id"
        ),

        "vitals": {
            "temperature": vitals.get(
                "temperature"
            ),

            "heart_rate": vitals.get(
                "heart_rate"
            ),

            "respiratory_rate": vitals.get(
                "respiratory_rate"
            ),

            "systolic_bp": vitals.get(
                "systolic_bp"
            ),

            "diastolic_bp": vitals.get(
                "diastolic_bp"
            ),

            "spo2": vitals.get(
                "spo2"
            )
        },

        "symptoms": _safe_list(
            symptoms
        )
    }


# ============================================================
# E5 REGIONAL CONTEXT
# ============================================================

def build_regional_context(
    regional_context: Any
):
    """
    Preserve E5 regional epidemiological information.

    E5 is contextual only in E13.

    It is NOT used to change the E12 ranking.
    """

    if regional_context is None:
        return None

    if isinstance(
        regional_context,
        dict
    ):
        return dict(
            regional_context
        )

    return {
        "summary": str(
            regional_context
        )
    }


# ============================================================
# MODEL EXPLANATION
# ============================================================

def build_shap_explanation(
    shap_result: Any
):
    """
    Preserve the E11 SHAP explanation.

    SHAP information is explanatory metadata and is not
    converted into a treatment-quality score.
    """

    if shap_result is None:
        return None

    if isinstance(
        shap_result,
        dict
    ):
        return dict(
            shap_result
        )

    return {
        "explanation": str(
            shap_result
        )
    }


# ============================================================
# BUILD SINGLE RECOMMENDATION
# ============================================================

def build_recommendation(
    ranking_record: Dict[str, Any]
):
    """
    Convert one E12 ranking record into the E13
    frontend/backend representation.
    """

    if not isinstance(
        ranking_record,
        dict
    ):
        raise ValueError(
            "E13 received an invalid E12 ranking record."
        )

    ranking_components = ranking_record.get(
        "ranking_components",
        {}
    )

    weighted_contributions = ranking_record.get(
        "weighted_contributions",
        {}
    )

    if not isinstance(
        ranking_components,
        dict
    ):
        ranking_components = {}

    if not isinstance(
        weighted_contributions,
        dict
    ):
        weighted_contributions = {}

    return {

        # ====================================================
        # Identity / rank
        # ====================================================

        "rank": ranking_record.get(
            "rank"
        ),

        "treatment_id": ranking_record.get(
            "treatment_id"
        ),

        "treatment_name": ranking_record.get(
            "treatment_name"
        ),

        # ====================================================
        # E12 ranking
        # ====================================================

        "ranking": {

            "final_score": _safe_float(
                ranking_record.get(
                    "final_score"
                )
            ),

            "ranking_explanation": (
                ranking_record.get(
                    "ranking_explanation"
                )
            ),

            "ranking_components": {
                key: _safe_float(value)
                for key, value in (
                    ranking_components.items()
                )
            },

            "weighted_contributions": {
                key: _safe_float(value)
                for key, value in (
                    weighted_contributions.items()
                )
            }
        },

        # ====================================================
        # E6 / E7 treatment success
        # ====================================================

        "treatment_success": {

            "calibrated_probability": _safe_float(
                ranking_record.get(
                    "calibrated_success_probability"
                )
            ),

            "percentage": (
                round(
                    _safe_float(
                        ranking_record.get(
                            "calibrated_success_probability"
                        ),
                        0.0
                    ) * 100,
                    2
                )
            )
        },

        # ====================================================
        # E8 uncertainty
        # ====================================================

        "uncertainty": {

            "level": ranking_record.get(
                "uncertainty_level",
                UNKNOWN_VALUE
            ),

            "lower": _safe_float(
                ranking_record.get(
                    "uncertainty_lower"
                )
            ),

            "upper": _safe_float(
                ranking_record.get(
                    "uncertainty_upper"
                )
            ),

            "standard_deviation": _safe_float(
                ranking_record.get(
                    "uncertainty_std"
                )
            ),

            "interval_width": _safe_float(
                ranking_record.get(
                    "uncertainty_interval_width"
                )
            )
        },

        # ====================================================
        # E9 recovery
        # ====================================================

        "recovery": {

            "expected_days": _safe_float(
                ranking_record.get(
                    "expected_recovery_days"
                )
            ),

            "lower_days": _safe_float(
                ranking_record.get(
                    "recovery_lower_days"
                )
            ),

            "upper_days": _safe_float(
                ranking_record.get(
                    "recovery_upper_days"
                )
            ),

            "uncertainty_level": ranking_record.get(
                "recovery_uncertainty_level",
                UNKNOWN_VALUE
            )
        },

        # ====================================================
        # E10 risk / complications
        # ====================================================

        "risk": {

            "level": ranking_record.get(
                "risk_level",
                UNKNOWN_VALUE
            ),

            "score": _safe_float(
                ranking_record.get(
                    "risk_score"
                )
            ),

            "factors": _safe_list(
                ranking_record.get(
                    "risk_factors",
                    []
                )
            ),

            "complication_indicators": _safe_list(
                ranking_record.get(
                    "complication_indicators",
                    []
                )
            )
        },

        # ====================================================
        # E4 clinical/configuration information
        # ====================================================

        "clinical_configuration": {

            "eligibility_status": ranking_record.get(
                "eligibility_status",
                UNKNOWN_VALUE
            ),

            "guideline_status": ranking_record.get(
                "guideline_status",
                UNKNOWN_VALUE
            ),

            "availability": ranking_record.get(
                "availability",
                UNKNOWN_VALUE
            ),

            "resource_tier": ranking_record.get(
                "resource_tier",
                UNKNOWN_VALUE
            )
        },

        # ====================================================
        # E11 explanation
        # ====================================================

        "explainability": {

            "shap": build_shap_explanation(
                ranking_record.get(
                    "shap_explanation"
                )
            )
        }
    }


# ============================================================
# EXCLUDED TREATMENTS
# ============================================================

def build_excluded_treatments(
    excluded_treatments: Any
):
    """
    Preserve E12 excluded treatment information.
    """

    if not excluded_treatments:
        return []

    output = []

    for record in excluded_treatments:

        if not isinstance(
            record,
            dict
        ):
            continue

        output.append({

            "treatment_id": record.get(
                "treatment_id"
            ),

            "treatment_name": record.get(
                "treatment_name"
            ),

            "reason": record.get(
                "reason",
                "Treatment was excluded from ranking."
            )
        })

    return output


# ============================================================
# SUMMARY
# ============================================================

def build_advisor_summary(
    ranked_treatments: List[Dict[str, Any]]
):
    """
    Build a concise summary for the frontend.

    This does not introduce a new recommendation.
    It simply identifies the treatment already ranked first
    by E12.
    """

    if not ranked_treatments:

        return {
            "has_recommendations": False,

            "top_ranked_treatment": None,

            "message": (
                "No rankable treatment candidates were "
                "returned by the treatment-advisor pipeline."
            )
        }

    top = ranked_treatments[0]

    return {

        "has_recommendations": True,

        "top_ranked_treatment": {

            "rank": top.get(
                "rank"
            ),

            "treatment_id": top.get(
                "treatment_id"
            ),

            "treatment_name": top.get(
                "treatment_name"
            ),

            "final_score": top.get(
                "ranking",
                {}
            ).get(
                "final_score"
            ),

            "success_probability": top.get(
                "treatment_success",
                {}
            ).get(
                "calibrated_probability"
            ),

            "uncertainty_level": top.get(
                "uncertainty",
                {}
            ).get(
                "level"
            ),

            "risk_level": top.get(
                "risk",
                {}
            ).get(
                "level"
            )
        },

        "message": (
            "Treatment options are ordered according to "
            "the project-defined E12 analytical ranking."
        )
    }


# ============================================================
# E13 MAIN FUNCTION
# ============================================================

def generate_final_advisor_output(
    ranking_output: Dict[str, Any],
    patient_context: Optional[Dict[str, Any]] = None,
    regional_context: Any = None
):
    """
    Generate the final E13 treatment-advisor response.

    Parameters
    ----------
    ranking_output : dict
        Complete output generated by E12.

    patient_context : dict, optional
        E1 patient context.

    regional_context : dict, optional
        E5 regional epidemiology context.

    Returns
    -------
    dict
        Final frontend/backend-ready treatment advisor output.
    """

    # ========================================================
    # Validate input
    # ========================================================

    if not isinstance(
        ranking_output,
        dict
    ):
        raise ValueError(
            "E13 requires the E12 ranking output "
            "as a dictionary."
        )

    required_fields = [
        "ranked_treatments",
        "excluded_treatments",
        "ranking_weights",
        "ranking_method",
        "interpretation"
    ]

    for field in required_fields:

        if field not in ranking_output:

            raise ValueError(
                f"E13 received E12 output without "
                f"required field '{field}'."
            )

    ranked_e12 = ranking_output.get(
        "ranked_treatments",
        []
    )

    if not isinstance(
        ranked_e12,
        list
    ):
        raise ValueError(
            "E12 ranked_treatments must be a list."
        )

    # ========================================================
    # Build recommendations
    # ========================================================

    recommendations = []

    for record in ranked_e12:

        recommendations.append(
            build_recommendation(
                record
            )
        )

    # ========================================================
    # Build output
    # ========================================================

    final_output = {

        # ====================================================
        # E13 metadata
        # ====================================================

        "advisor_version": E13_VERSION,

        "advisor_status": (
            "COMPLETED"
            if recommendations
            else "NO_RANKABLE_TREATMENTS"
        ),

        # ====================================================
        # Encounter
        # ====================================================

        "encounter_id": (
            patient_context.get(
                "encounter_id"
            )
            if isinstance(
                patient_context,
                dict
            )
            else None
        ),

        # ====================================================
        # Patient clinical context
        # ====================================================

        "patient_context": (
            build_patient_context_summary(
                patient_context
            )
        ),

        # ====================================================
        # Regional epidemiology
        # ====================================================

        "regional_epidemiology": (
            build_regional_context(
                regional_context
            )
        ),

        # ====================================================
        # Advisor summary
        # ====================================================

        "summary": build_advisor_summary(
            recommendations
        ),

        # ====================================================
        # Final treatment recommendations
        # ====================================================

        "recommendations": recommendations,

        # ====================================================
        # Excluded candidates
        # ====================================================

        "excluded_treatments": (
            build_excluded_treatments(
                ranking_output.get(
                    "excluded_treatments",
                    []
                )
            )
        ),

        # ====================================================
        # Ranking methodology
        # ====================================================

        "ranking": {

            "method": ranking_output.get(
                "ranking_method"
            ),

            "weights": dict(
                ranking_output.get(
                    "ranking_weights",
                    {}
                )
            ),

            "interpretation": ranking_output.get(
                "interpretation"
            )
        },

        # ====================================================
        # Disclaimer
        # ====================================================

        "disclaimer": ADVISOR_DISCLAIMER
    }

    return final_output


# ============================================================
# VALIDATE E13 OUTPUT
# ============================================================

def validate_final_advisor_output(
    advisor_output: Dict[str, Any]
):
    """
    Validate the final E13 output structure.
    """

    if not isinstance(
        advisor_output,
        dict
    ):
        raise RuntimeError(
            "E13 output must be a dictionary."
        )

    required_fields = [
        "advisor_version",
        "advisor_status",
        "patient_context",
        "regional_epidemiology",
        "summary",
        "recommendations",
        "excluded_treatments",
        "ranking",
        "disclaimer"
    ]

    for field in required_fields:

        if field not in advisor_output:

            raise RuntimeError(
                f"E13 output missing '{field}'."
            )

    recommendations = advisor_output[
        "recommendations"
    ]

    if not isinstance(
        recommendations,
        list
    ):
        raise RuntimeError(
            "E13 recommendations must be a list."
        )

    # ========================================================
    # Validate rank sequence
    # ========================================================

    expected_ranks = list(
        range(
            1,
            len(recommendations) + 1
        )
    )

    actual_ranks = [
        result.get(
            "rank"
        )
        for result in recommendations
    ]

    if actual_ranks != expected_ranks:

        raise RuntimeError(
            "E13 recommendation ranks are not sequential."
        )

    # ========================================================
    # Validate recommendation structure
    # ========================================================

    required_recommendation_fields = [

        "rank",
        "treatment_id",
        "treatment_name",
        "ranking",
        "treatment_success",
        "uncertainty",
        "recovery",
        "risk",
        "clinical_configuration",
        "explainability"
    ]

    for recommendation in recommendations:

        for field in required_recommendation_fields:

            if field not in recommendation:

                raise RuntimeError(
                    "E13 recommendation missing "
                    f"field '{field}'."
                )

        # ----------------------------------------------------
        # Final score
        # ----------------------------------------------------

        final_score = _safe_float(
            recommendation[
                "ranking"
            ].get(
                "final_score"
            )
        )

        if final_score is None:

            raise RuntimeError(
                "E13 final score is invalid."
            )

        if not (
            0.0
            <= final_score
            <= 1.0
        ):

            raise RuntimeError(
                "E13 final score is outside [0,1]."
            )

        # ----------------------------------------------------
        # Success probability
        # ----------------------------------------------------

        probability = _safe_float(
            recommendation[
                "treatment_success"
            ].get(
                "calibrated_probability"
            )
        )

        if probability is None:

            raise RuntimeError(
                "E13 treatment-success probability "
                "is invalid."
            )

        if not (
            0.0
            <= probability
            <= 1.0
        ):

            raise RuntimeError(
                "E13 treatment-success probability "
                "is outside [0,1]."
            )

        # ----------------------------------------------------
        # Uncertainty
        # ----------------------------------------------------

        uncertainty = recommendation[
            "uncertainty"
        ]

        lower = _safe_float(
            uncertainty.get(
                "lower"
            )
        )

        upper = _safe_float(
            uncertainty.get(
                "upper"
            )
        )

        if (
            lower is not None
            and upper is not None
        ):

            if not (
                0.0
                <= lower
                <= upper
                <= 1.0
            ):

                raise RuntimeError(
                    "E13 uncertainty interval is invalid."
                )

        # ----------------------------------------------------
        # Recovery
        # ----------------------------------------------------

        recovery = recommendation[
            "recovery"
        ]

        expected_days = _safe_float(
            recovery.get(
                "expected_days"
            )
        )

        if expected_days is None:

            raise RuntimeError(
                "E13 expected recovery time is invalid."
            )

        if expected_days < 0:

            raise RuntimeError(
                "E13 expected recovery time "
                "cannot be negative."
            )

        # ----------------------------------------------------
        # Risk
        # ----------------------------------------------------

        risk_level = recommendation[
            "risk"
        ].get(
            "level"
        )

        if risk_level not in {
            "LOW",
            "MODERATE",
            "HIGH",
            UNKNOWN_VALUE
        }:

            raise RuntimeError(
                "E13 returned an invalid risk level."
            )

        # ----------------------------------------------------
        # Lists
        # ----------------------------------------------------

        if not isinstance(
            recommendation[
                "risk"
            ].get(
                "factors",
                []
            ),
            list
        ):

            raise RuntimeError(
                "E13 risk factors must be a list."
            )

        if not isinstance(
            recommendation[
                "risk"
            ].get(
                "complication_indicators",
                []
            ),
            list
        ):

            raise RuntimeError(
                "E13 complication indicators "
                "must be a list."
            )

    # ========================================================
    # Validate ranking metadata
    # ========================================================

    ranking = advisor_output[
        "ranking"
    ]

    if not isinstance(
        ranking,
        dict
    ):
        raise RuntimeError(
            "E13 ranking metadata must be a dictionary."
        )

    weights = ranking.get(
        "weights",
        {}
    )

    if not isinstance(
        weights,
        dict
    ):
        raise RuntimeError(
            "E13 ranking weights must be a dictionary."
        )

    # ========================================================
    # Validate summary
    # ========================================================

    summary = advisor_output[
        "summary"
    ]

    if not isinstance(
        summary,
        dict
    ):
        raise RuntimeError(
            "E13 summary must be a dictionary."
        )

    if recommendations:

        if not summary.get(
            "has_recommendations",
            False
        ):
            raise RuntimeError(
                "E13 summary incorrectly reports "
                "no recommendations."
            )

    else:

        if summary.get(
            "has_recommendations",
            False
        ):
            raise RuntimeError(
                "E13 summary incorrectly reports "
                "available recommendations."
            )

    # ========================================================
    # Validate disclaimer
    # ========================================================

    disclaimer = advisor_output[
        "disclaimer"
    ]

    if not isinstance(
        disclaimer,
        str
    ) or not disclaimer.strip():

        raise RuntimeError(
            "E13 disclaimer is missing."
        )

    return True


# ============================================================
# DISPLAY FINAL ADVISOR OUTPUT
# ============================================================

def display_final_advisor_output(
    advisor_output: Dict[str, Any]
):
    """
    Display E13 output in a readable form for validation.
    """

    print()
    print("=" * 75)
    print("E13 FINAL TREATMENT ADVISOR OUTPUT")
    print("=" * 75)

    print()
    print(
        f"Advisor version : "
        f"{advisor_output['advisor_version']}"
    )

    print(
        f"Status          : "
        f"{advisor_output['advisor_status']}"
    )

    print(
        f"Encounter ID    : "
        f"{advisor_output.get('encounter_id')}"
    )

    # ========================================================
    # Summary
    # ========================================================

    summary = advisor_output[
        "summary"
    ]

    print()
    print("-" * 75)
    print("ADVISOR SUMMARY")
    print("-" * 75)

    print(
        summary.get(
            "message"
        )
    )

    top = summary.get(
        "top_ranked_treatment"
    )

    if top:

        print()
        print(
            f"Top ranked treatment : "
            f"{top.get('treatment_name')}"
        )

        print(
            f"Treatment ID         : "
            f"{top.get('treatment_id')}"
        )

        print(
            f"Final score          : "
            f"{top.get('final_score')}"
        )

        probability = top.get(
            "success_probability"
        )

        if probability is not None:

            print(
                f"Success probability  : "
                f"{probability:.4f}"
            )

        print(
            f"Uncertainty          : "
            f"{top.get('uncertainty_level')}"
        )

        print(
            f"Risk level           : "
            f"{top.get('risk_level')}"
        )

    # ========================================================
    # Recommendations
    # ========================================================

    print()
    print("=" * 75)
    print("TREATMENT RECOMMENDATIONS")
    print("=" * 75)

    recommendations = advisor_output[
        "recommendations"
    ]

    if not recommendations:

        print(
            "No rankable treatment candidates."
        )

    for recommendation in recommendations:

        print()
        print(
            f"RANK {recommendation['rank']}"
        )

        print(
            "-" * 75
        )

        print(
            f"Treatment ID   : "
            f"{recommendation['treatment_id']}"
        )

        print(
            f"Treatment name : "
            f"{recommendation['treatment_name']}"
        )

        ranking = recommendation[
            "ranking"
        ]

        print(
            f"Final score    : "
            f"{ranking['final_score']:.4f}"
        )

        success = recommendation[
            "treatment_success"
        ]

        print(
            f"Success        : "
            f"{success['calibrated_probability']:.4f}"
            f" ({success['percentage']:.2f}%)"
        )

        uncertainty = recommendation[
            "uncertainty"
        ]

        print(
            f"Uncertainty    : "
            f"{uncertainty['level']}"
        )

        if (
            uncertainty["lower"] is not None
            and uncertainty["upper"] is not None
        ):

            print(
                f"Success range  : "
                f"{uncertainty['lower']:.4f} - "
                f"{uncertainty['upper']:.4f}"
            )

        recovery = recommendation[
            "recovery"
        ]

        print(
            f"Recovery       : "
            f"{recovery['expected_days']:.2f} days"
        )

        if (
            recovery["lower_days"] is not None
            and recovery["upper_days"] is not None
        ):

            print(
                f"Recovery range : "
                f"{recovery['lower_days']:.2f} - "
                f"{recovery['upper_days']:.2f} days"
            )

        risk = recommendation[
            "risk"
        ]

        print(
            f"Risk           : "
            f"{risk['level']}"
        )

        print(
            f"Availability   : "
            f"{recommendation['clinical_configuration']['availability']}"
        )

        print(
            f"Guideline      : "
            f"{recommendation['clinical_configuration']['guideline_status']}"
        )

        print(
            f"Resource tier  : "
            f"{recommendation['clinical_configuration']['resource_tier']}"
        )

        print()
        print(
            "Why it ranked:"
        )

        print(
            f"  {ranking['ranking_explanation']}"
        )

    # ========================================================
    # Excluded treatments
    # ========================================================

    excluded = advisor_output[
        "excluded_treatments"
    ]

    if excluded:

        print()
        print("=" * 75)
        print("EXCLUDED TREATMENTS")
        print("=" * 75)

        for record in excluded:

            print(
                f"{record['treatment_id']} - "
                f"{record['treatment_name']}: "
                f"{record['reason']}"
            )

    # ========================================================
    # Regional context
    # ========================================================

    regional = advisor_output[
        "regional_epidemiology"
    ]

    if regional is not None:

        print()
        print("=" * 75)
        print("REGIONAL EPIDEMIOLOGICAL CONTEXT")
        print("=" * 75)

        if isinstance(
            regional,
            dict
        ):

            for key, value in regional.items():

                print(
                    f"{key}: {value}"
                )

        else:

            print(
                regional
            )

    # ========================================================
    # Disclaimer
    # ========================================================

    print()
    print("=" * 75)
    print("INTERPRETATION / DISCLAIMER")
    print("=" * 75)

    print(
        advisor_output[
            "disclaimer"
        ]
    )


# ============================================================
# E13 PIPELINE TEST
# ============================================================

def run_e13_pipeline_test():
    """
    Run E13 using the existing E12 pipeline.

    E13 does not recreate E1-E12 logic. It simply consumes
    the E12 output and formats it for final advisor use.
    """

    print()
    print("=" * 75)
    print("E13 PIPELINE TEST")
    print("=" * 75)

    # ========================================================
    # IMPORT E12
    # ========================================================

    from ML.treatment_advisor.treatment_ranking import (
        run_e12_pipeline_test
    )

    # ========================================================
    # RUN E12
    # ========================================================

    print()
    print(
        "Running E12 to obtain ranking output..."
    )

    ranking_output = (
        run_e12_pipeline_test()
    )

    # ========================================================
    # EXTRACT OPTIONAL CONTEXT
    # ========================================================

    patient_context = None
    regional_context = None

    # E12's test pipeline does not currently return E1 context
    # and E5 context at the top level.
    #
    # Therefore E13 obtains the encounter context separately
    # for this validation run.
    #
    # This is only test orchestration. The backend can pass
    # these objects directly when the integrated API is built.

    first_ranked = ranking_output[
        "ranked_treatments"
    ]

    if first_ranked:

        # ----------------------------------------------------
        # Encounter ID is available from E12 pipeline indirectly
        # only if the E12 test is changed to expose it.
        #
        # For the current frozen E12 implementation, recover
        # the test encounter through the same E6 helper.
        # ----------------------------------------------------

        from ML.treatment_advisor.treatment_model import (
            find_valid_test_encounter
        )

        (
            encounter_id,
            patient_context
        ) = find_valid_test_encounter()

        # ----------------------------------------------------
        # E5 regional context
        # ----------------------------------------------------

        try:

            from database import get_engine
            import pandas as pd

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

            if not hospital_df.empty:

                hospital_id = str(
                    hospital_df.iloc[0][
                        "hospital_id"
                    ]
                )

                try:

                    from ML.treatment_advisor.regional_epidemiology import (
                        get_regional_epidemiology
                    )

                    regional_context = (
                        get_regional_epidemiology(
                            hospital_id=hospital_id,
                            disease_id=patient_context.get(
                                "disease_id"
                            )
                        )
                    )

                except Exception as e:

                    print(
                        "E5 context could not be loaded "
                        f"for E13 display: {type(e).__name__}"
                    )

        except Exception as e:

            print(
                "Regional context lookup skipped: "
                f"{type(e).__name__}"
            )

    # ========================================================
    # E13
    # ========================================================

    final_output = (
        generate_final_advisor_output(
            ranking_output=ranking_output,
            patient_context=patient_context,
            regional_context=regional_context
        )
    )

    # ========================================================
    # VALIDATE
    # ========================================================

    validate_final_advisor_output(
        final_output
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    display_final_advisor_output(
        final_output
    )

    # ========================================================
    # FINAL CHECK
    # ========================================================

    if final_output[
        "advisor_status"
    ] not in {
        "COMPLETED",
        "NO_RANKABLE_TREATMENTS"
    }:

        raise RuntimeError(
            "E13 returned an invalid advisor status."
        )

    print()
    print("=" * 75)
    print("E13 VALIDATION: PASSED")
    print("=" * 75)

    return final_output


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 75)
    print("E13 - FINAL TREATMENT ADVISOR OUTPUT")
    print("=" * 75)

    run_e13_pipeline_test()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
"""
E12 - Final Treatment Ranking

Purpose
-------
Rank treatment candidates using the outputs produced by the
previous treatment-advisor stages.

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

Important
---------
E12 does NOT train a new machine-learning model.

The ranking is based on project-defined weighted scoring.

It is NOT:
    - a clinical prescribing decision
    - a causal treatment-effect estimate
    - a medically validated treatment ranking
    - a guarantee of treatment success
    - a clinical guideline recommendation

E4 guideline information is project configuration only.
E8/E9 uncertainty intervals are model-derived predictive
spreads, not formal statistical confidence intervals.
"""

from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# PROJECT-DEFINED RANKING WEIGHTS
# ============================================================
#
# The weights sum to 1.0.
#
# These are project-defined analytical weights.
# They are NOT clinically validated weights.
#
# Success probability:
#     40%
#
# Uncertainty:
#     15%
#
# Recovery time:
#     15%
#
# Risk:
#     15%
#
# Availability:
#     5%
#
# Guideline/configuration support:
#     5%
#
# Resource tier:
#     5%
#
# ============================================================

WEIGHT_SUCCESS = 0.40
WEIGHT_UNCERTAINTY = 0.15
WEIGHT_RECOVERY = 0.15
WEIGHT_RISK = 0.15
WEIGHT_AVAILABILITY = 0.05
WEIGHT_GUIDELINE = 0.05
WEIGHT_RESOURCE = 0.05


# ============================================================
# RANKING CONFIGURATION
# ============================================================

RANKING_WEIGHTS = {
    "success": WEIGHT_SUCCESS,
    "uncertainty": WEIGHT_UNCERTAINTY,
    "recovery": WEIGHT_RECOVERY,
    "risk": WEIGHT_RISK,
    "availability": WEIGHT_AVAILABILITY,
    "guideline": WEIGHT_GUIDELINE,
    "resource": WEIGHT_RESOURCE,
}


# ============================================================
# SCORE MAPPINGS
# ============================================================
#
# All values are project-defined.
#
# Scores are normalized to [0, 1].
#
# Higher score = better ranking.
#
# ============================================================


# ------------------------------------------------------------
# E4 availability
# ------------------------------------------------------------

AVAILABILITY_SCORES = {
    "AVAILABLE": 1.0,
    "LIMITED": 0.5,
    "UNAVAILABLE": 0.0,
}


# ------------------------------------------------------------
# E4 guideline/configuration status
# ------------------------------------------------------------

GUIDELINE_SCORES = {
    "PROJECT_SUPPORTED": 1.0,
    "PROJECT_SUPPORTED_REVIEW": 0.5,
    "NOT_SUPPORTED": 0.0,
    "UNKNOWN": 0.0,
}


# ------------------------------------------------------------
# E4 resource tier
#
# Lower resource requirement receives a higher preference.
#
# LOW      = 1.0
# MEDIUM   = 0.6
# HIGH     = 0.2
#
# ------------------------------------------------------------

RESOURCE_SCORES = {
    "LOW": 1.0,
    "MEDIUM": 0.6,
    "HIGH": 0.2,
    "UNKNOWN": 0.0,
}


# ------------------------------------------------------------
# E8 uncertainty
#
# Lower uncertainty = better.
#
# LOW      = 1.0
# MODERATE = 0.5
# HIGH     = 0.0
#
# ------------------------------------------------------------

UNCERTAINTY_SCORES = {
    "LOW": 1.0,
    "MODERATE": 0.5,
    "HIGH": 0.0,
}


# ------------------------------------------------------------
# E10 risk
#
# Lower project-defined risk = better.
#
# LOW      = 1.0
# MODERATE = 0.5
# HIGH     = 0.0
#
# ------------------------------------------------------------

RISK_SCORES = {
    "LOW": 1.0,
    "MODERATE": 0.5,
    "HIGH": 0.0,
}


# ============================================================
# VALIDATE WEIGHTS
# ============================================================

def validate_ranking_weights():
    """
    Validate that ranking weights are correctly configured.
    """

    total = sum(
        RANKING_WEIGHTS.values()
    )

    if not np.isclose(
        total,
        1.0,
        atol=1e-9
    ):

        raise ValueError(
            "E12 ranking weights must sum to 1.0. "
            f"Current total: {total}"
        )

    for name, weight in (
        RANKING_WEIGHTS.items()
    ):

        if weight < 0:

            raise ValueError(
                f"E12 ranking weight '{name}' "
                "cannot be negative."
            )

    return True


# ============================================================
# NORMALIZE RECOVERY TIME
# ============================================================

def calculate_recovery_score(
    expected_recovery_days,
    min_days,
    max_days
):
    """
    Convert expected recovery time into a normalized score.

    Shorter expected recovery receives a higher score.

    Formula:

        score =
            (max_days - value)
            /
            (max_days - min_days)

    If all treatments have the same recovery estimate,
    every treatment receives a neutral score of 1.0.
    """

    try:

        value = float(
            expected_recovery_days
        )

        minimum = float(
            min_days
        )

        maximum = float(
            max_days
        )

    except (
        TypeError,
        ValueError
    ):

        return 0.0

    if not np.isfinite(value):

        return 0.0

    if maximum <= minimum:

        return 1.0

    score = (
        maximum - value
    ) / (
        maximum - minimum
    )

    return float(
        np.clip(
            score,
            0.0,
            1.0
        )
    )


# ============================================================
# EXTRACT AVAILABILITY SCORE
# ============================================================

def get_availability_score(
    availability
):
    """
    Convert E4 availability status to a project-defined score.
    """

    if availability is None:

        return 0.0

    status = str(
        availability
    ).strip().upper()

    return float(
        AVAILABILITY_SCORES.get(
            status,
            0.0
        )
    )


# ============================================================
# EXTRACT GUIDELINE SCORE
# ============================================================

def get_guideline_score(
    guideline_status
):
    """
    Convert E4 guideline/configuration status to a score.

    E4 status is project configuration and does not represent
    national or international clinical guideline approval.
    """

    if guideline_status is None:

        return 0.0

    status = str(
        guideline_status
    ).strip().upper()

    return float(
        GUIDELINE_SCORES.get(
            status,
            0.0
        )
    )


# ============================================================
# EXTRACT RESOURCE SCORE
# ============================================================

def get_resource_score(
    resource_tier
):
    """
    Convert E4 resource tier into a project-defined score.
    """

    if resource_tier is None:

        return 0.0

    tier = str(
        resource_tier
    ).strip().upper()

    return float(
        RESOURCE_SCORES.get(
            tier,
            0.0
        )
    )


# ============================================================
# EXTRACT UNCERTAINTY SCORE
# ============================================================

def get_uncertainty_score(
    uncertainty_level
):
    """
    Convert E8 uncertainty level into a ranking score.

    Lower uncertainty receives a higher score.
    """

    if uncertainty_level is None:

        return 0.0

    level = str(
        uncertainty_level
    ).strip().upper()

    return float(
        UNCERTAINTY_SCORES.get(
            level,
            0.0
        )
    )


# ============================================================
# EXTRACT RISK SCORE
# ============================================================

def get_risk_preference_score(
    risk_level
):
    """
    Convert E10 risk level into a ranking preference score.

    Lower project-defined risk receives a higher score.
    """

    if risk_level is None:

        return 0.0

    level = str(
        risk_level
    ).strip().upper()

    return float(
        RISK_SCORES.get(
            level,
            0.0
        )
    )


# ============================================================
# ELIGIBILITY CHECK
# ============================================================

def is_candidate_rankable(
    candidate_record
):
    """
    Determine whether a treatment can enter the normal ranking.

    Hard exclusion rules:

        INELIGIBLE
        UNAVAILABLE

    E3 is the source of clinical eligibility status.
    E4 is the source of availability.
    """

    eligibility = str(
        candidate_record.get(
            "eligibility_status",
            candidate_record.get(
                "status",
                "UNKNOWN"
            )
        )
    ).strip().upper()

    availability = str(
        candidate_record.get(
            "availability",
            "UNKNOWN"
        )
    ).strip().upper()

    if eligibility == "INELIGIBLE":

        return False

    if availability == "UNAVAILABLE":

        return False

    return True


# ============================================================
# CALCULATE INDIVIDUAL RANKING COMPONENTS
# ============================================================

def calculate_ranking_components(
    candidate_record,
    e7_result,
    e8_result,
    e9_result,
    e10_result,
    e11_result=None,
    all_recovery_values=None
):
    """
    Calculate normalized ranking components for one treatment.

    E11 is intentionally not used as a numerical ranking factor.

    SHAP explains the E6 model; it does not provide an independent
    treatment-quality score.

    Therefore E11 is attached to the final result as explanation
    metadata rather than being converted into a ranking score.
    """

    # --------------------------------------------------------
    # E7 success probability
    # --------------------------------------------------------

    success_probability = float(
        e7_result.get(
            "calibrated_success_probability",
            0.0
        )
    )

    success_probability = float(
        np.clip(
            success_probability,
            0.0,
            1.0
        )
    )

    success_score = (
        success_probability
    )

    # --------------------------------------------------------
    # E8 uncertainty
    # --------------------------------------------------------

    uncertainty_level = e8_result.get(
        "uncertainty_level",
        "UNKNOWN"
    )

    uncertainty_score = (
        get_uncertainty_score(
            uncertainty_level
        )
    )

    # --------------------------------------------------------
    # E9 recovery
    # --------------------------------------------------------

    expected_recovery_days = float(
        e9_result.get(
            "expected_recovery_days",
            0.0
        )
    )

    if all_recovery_values:

        min_recovery = min(
            all_recovery_values
        )

        max_recovery = max(
            all_recovery_values
        )

    else:

        min_recovery = expected_recovery_days
        max_recovery = expected_recovery_days

    recovery_score = (
        calculate_recovery_score(
            expected_recovery_days,
            min_recovery,
            max_recovery
        )
    )

    # --------------------------------------------------------
    # E10 risk
    # --------------------------------------------------------

    risk_level = e10_result.get(
        "risk_level",
        "UNKNOWN"
    )

    risk_score = (
        get_risk_preference_score(
            risk_level
        )
    )

    # --------------------------------------------------------
    # E4 availability
    # --------------------------------------------------------

    availability = candidate_record.get(
        "availability",
        "UNKNOWN"
    )

    availability_score = (
        get_availability_score(
            availability
        )
    )

    # --------------------------------------------------------
    # E4 guideline
    # --------------------------------------------------------

    guideline_status = candidate_record.get(
        "guideline_status",
        "UNKNOWN"
    )

    guideline_score = (
        get_guideline_score(
            guideline_status
        )
    )

    # --------------------------------------------------------
    # E4 resource tier
    #
    # Support multiple possible column names because the
    # configuration layer may expose resource information
    # differently.
    # --------------------------------------------------------

    resource_tier = candidate_record.get(
        "resource_tier",
        candidate_record.get(
            "resource_level",
            candidate_record.get(
                "cost_tier",
                "UNKNOWN"
            )
        )
    )

    resource_score = (
        get_resource_score(
            resource_tier
        )
    )

    # --------------------------------------------------------
    # Weighted contributions
    # --------------------------------------------------------

    weighted_success = (
        WEIGHT_SUCCESS
        * success_score
    )

    weighted_uncertainty = (
        WEIGHT_UNCERTAINTY
        * uncertainty_score
    )

    weighted_recovery = (
        WEIGHT_RECOVERY
        * recovery_score
    )

    weighted_risk = (
        WEIGHT_RISK
        * risk_score
    )

    weighted_availability = (
        WEIGHT_AVAILABILITY
        * availability_score
    )

    weighted_guideline = (
        WEIGHT_GUIDELINE
        * guideline_score
    )

    weighted_resource = (
        WEIGHT_RESOURCE
        * resource_score
    )

    final_score = (
        weighted_success
        + weighted_uncertainty
        + weighted_recovery
        + weighted_risk
        + weighted_availability
        + weighted_guideline
        + weighted_resource
    )

    return {

        # ----------------------------------------------------
        # Raw component scores
        # ----------------------------------------------------

        "success_score": success_score,

        "uncertainty_score": uncertainty_score,

        "recovery_score": recovery_score,

        "risk_score": risk_score,

        "availability_score": availability_score,

        "guideline_score": guideline_score,

        "resource_score": resource_score,

        # ----------------------------------------------------
        # Weighted contributions
        # ----------------------------------------------------

        "weighted_success": weighted_success,

        "weighted_uncertainty": weighted_uncertainty,

        "weighted_recovery": weighted_recovery,

        "weighted_risk": weighted_risk,

        "weighted_availability": weighted_availability,

        "weighted_guideline": weighted_guideline,

        "weighted_resource": weighted_resource,

        # ----------------------------------------------------
        # Final score
        # ----------------------------------------------------

        "final_score": float(
            np.clip(
                final_score,
                0.0,
                1.0
            )
        ),

        # ----------------------------------------------------
        # Supporting values
        # ----------------------------------------------------

        "success_probability": success_probability,

        "uncertainty_level": uncertainty_level,

        "expected_recovery_days": (
            expected_recovery_days
        ),

        "risk_level": risk_level,

        "availability": availability,

        "guideline_status": guideline_status,

        "resource_tier": resource_tier,

        # ----------------------------------------------------
        # E11 explanation
        # ----------------------------------------------------

        "shap_explanation": (
            e11_result
        )
    }


# ============================================================
# GENERATE RANKING EXPLANATION
# ============================================================

def generate_ranking_explanation(
    components
):
    """
    Generate a human-readable explanation for the ranking.
    """

    reasons = []

    # --------------------------------------------------------
    # Success probability
    # --------------------------------------------------------

    success_probability = components[
        "success_probability"
    ]

    if success_probability >= 0.80:

        reasons.append(
            "high calibrated treatment-success probability"
        )

    elif success_probability >= 0.60:

        reasons.append(
            "moderate-to-high calibrated treatment-success probability"
        )

    else:

        reasons.append(
            "lower calibrated treatment-success probability"
        )

    # --------------------------------------------------------
    # Uncertainty
    # --------------------------------------------------------

    if components[
        "uncertainty_level"
    ] == "LOW":

        reasons.append(
            "low model predictive uncertainty"
        )

    elif components[
        "uncertainty_level"
    ] == "MODERATE":

        reasons.append(
            "moderate model predictive uncertainty"
        )

    elif components[
        "uncertainty_level"
    ] == "HIGH":

        reasons.append(
            "high model predictive uncertainty"
        )

    # --------------------------------------------------------
    # Recovery
    # --------------------------------------------------------

    recovery_score = components[
        "recovery_score"
    ]

    if recovery_score >= 0.75:

        reasons.append(
            "favorable relative recovery estimate"
        )

    elif recovery_score < 0.25:

        reasons.append(
            "less favorable relative recovery estimate"
        )

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    risk_level = components[
        "risk_level"
    ]

    if risk_level == "LOW":

        reasons.append(
            "low project-defined risk level"
        )

    elif risk_level == "HIGH":

        reasons.append(
            "high project-defined risk level"
        )

    # --------------------------------------------------------
    # Availability
    # --------------------------------------------------------

    availability = str(
        components[
            "availability"
        ]
    ).upper()

    if availability == "AVAILABLE":

        reasons.append(
            "treatment is currently available"
        )

    elif availability == "LIMITED":

        reasons.append(
            "treatment has limited availability"
        )

    # --------------------------------------------------------
    # Guideline/configuration
    # --------------------------------------------------------

    guideline_status = str(
        components[
            "guideline_status"
        ]
    ).upper()

    if guideline_status == "PROJECT_SUPPORTED":

        reasons.append(
            "supported by the project configuration"
        )

    elif guideline_status == "PROJECT_SUPPORTED_REVIEW":

        reasons.append(
            "requires project-level configuration review"
        )

    # --------------------------------------------------------
    # Final text
    # --------------------------------------------------------

    if not reasons:

        return (
            "Ranking based on available project-defined "
            "treatment evidence."
        )

    return (
        "Ranked using "
        + ", ".join(reasons)
        + "."
    )


# ============================================================
# RANK TREATMENTS
# ============================================================

def rank_treatments(
    enriched_candidates,
    e7_results,
    e8_results,
    e9_results,
    e10_results,
    e11_results=None
):
    """
    Rank treatment candidates using E3-E11 outputs.

    Parameters
    ----------
    enriched_candidates : pandas.DataFrame
        E4-enriched treatment candidates.

    e7_results : list[dict]
        E7 calibrated probability results.

    e8_results : list[dict]
        E8 uncertainty results.

    e9_results : list[dict]
        E9 recovery estimates.

    e10_results : list[dict]
        E10 risk assessments.

    e11_results : list[dict], optional
        E11 SHAP explanations.

    Returns
    -------
    list[dict]
        Ranked treatment recommendations.

    Notes
    -----
    E11 is explanatory and does not contribute directly
    to the numerical ranking score.
    """

    validate_ranking_weights()

    if (
        enriched_candidates is None
        or enriched_candidates.empty
    ):

        raise ValueError(
            "E12 received no treatment candidates."
        )

    if e7_results is None:

        raise ValueError(
            "E12 received no E7 results."
        )

    if e8_results is None:

        raise ValueError(
            "E12 received no E8 results."
        )

    if e9_results is None:

        raise ValueError(
            "E12 received no E9 results."
        )

    if e10_results is None:

        raise ValueError(
            "E12 received no E10 results."
        )

    # --------------------------------------------------------
    # Index previous-stage results by treatment ID
    # --------------------------------------------------------

    e7_by_treatment = {
        str(result["treatment_id"]): result
        for result in e7_results
    }

    e8_by_treatment = {
        str(result["treatment_id"]): result
        for result in e8_results
    }

    e9_by_treatment = {
        str(result["treatment_id"]): result
        for result in e9_results
    }

    e10_by_treatment = {
        str(result["treatment_id"]): result
        for result in e10_results
    }

    e11_by_treatment = {}

    if e11_results:

        e11_by_treatment = {
            str(result["treatment_id"]): result
            for result in e11_results
        }

    # --------------------------------------------------------
    # Recovery values for relative normalization
    # --------------------------------------------------------

    recovery_values = []

    for result in e9_results:

        value = result.get(
            "expected_recovery_days"
        )

        try:

            value = float(value)

            if np.isfinite(value):

                recovery_values.append(
                    value
                )

        except (
            TypeError,
            ValueError
        ):

            continue

    # --------------------------------------------------------
    # Calculate ranking components
    # --------------------------------------------------------

    ranking_records = []

    excluded_records = []

    for _, candidate in (
        enriched_candidates.iterrows()
    ):

        candidate_record = (
            candidate.to_dict()
        )

        treatment_id = str(
            candidate_record.get(
                "treatment_id"
            )
        )

        treatment_name = str(
            candidate_record.get(
                "treatment_name",
                treatment_id
            )
        )

        # ----------------------------------------------------
        # Hard eligibility/availability filtering
        # ----------------------------------------------------

        if not is_candidate_rankable(
            candidate_record
        ):

            excluded_records.append({

                "treatment_id": treatment_id,

                "treatment_name": treatment_name,

                "reason": (
                    "Candidate is clinically ineligible "
                    "or currently unavailable."
                )
            })

            continue

        # ----------------------------------------------------
        # Check all required stage outputs
        # ----------------------------------------------------

        if treatment_id not in e7_by_treatment:

            raise ValueError(
                f"E7 result missing for treatment "
                f"{treatment_id}."
            )

        if treatment_id not in e8_by_treatment:

            raise ValueError(
                f"E8 result missing for treatment "
                f"{treatment_id}."
            )

        if treatment_id not in e9_by_treatment:

            raise ValueError(
                f"E9 result missing for treatment "
                f"{treatment_id}."
            )

        if treatment_id not in e10_by_treatment:

            raise ValueError(
                f"E10 result missing for treatment "
                f"{treatment_id}."
            )

        # ----------------------------------------------------
        # Previous-stage results
        # ----------------------------------------------------

        e7_result = e7_by_treatment[
            treatment_id
        ]

        e8_result = e8_by_treatment[
            treatment_id
        ]

        e9_result = e9_by_treatment[
            treatment_id
        ]

        e10_result = e10_by_treatment[
            treatment_id
        ]

        e11_result = e11_by_treatment.get(
            treatment_id
        )

        # ----------------------------------------------------
        # Calculate components
        # ----------------------------------------------------

        components = (
            calculate_ranking_components(
                candidate_record,
                e7_result,
                e8_result,
                e9_result,
                e10_result,
                e11_result=e11_result,
                all_recovery_values=recovery_values
            )
        )

        # ----------------------------------------------------
        # Explanation
        # ----------------------------------------------------

        explanation = (
            generate_ranking_explanation(
                components
            )
        )

        # ----------------------------------------------------
        # Build result
        # ----------------------------------------------------

        ranking_records.append({

            "treatment_id": treatment_id,

            "treatment_name": treatment_name,

            "final_score": components[
                "final_score"
            ],

            "eligibility_status": candidate_record.get(
                "eligibility_status",
                candidate_record.get(
                    "status",
                    "UNKNOWN"
                )
            ),

            "guideline_status": components[
                "guideline_status"
            ],

            "availability": components[
                "availability"
            ],

            "resource_tier": components[
                "resource_tier"
            ],

            "calibrated_success_probability": (
                components[
                    "success_probability"
                ]
            ),

            "uncertainty_level": components[
                "uncertainty_level"
            ],

            "uncertainty_lower": e8_result.get(
                "uncertainty_lower"
            ),

            "uncertainty_upper": e8_result.get(
                "uncertainty_upper"
            ),

            "uncertainty_std": e8_result.get(
                "uncertainty_std"
            ),

            "uncertainty_interval_width": (
                e8_result.get(
                    "uncertainty_interval_width"
                )
            ),

            "expected_recovery_days": (
                components[
                    "expected_recovery_days"
                ]
            ),

            "recovery_lower_days": e9_result.get(
                "recovery_lower_days"
            ),

            "recovery_upper_days": e9_result.get(
                "recovery_upper_days"
            ),

            "recovery_uncertainty_level": (
                e9_result.get(
                    "recovery_uncertainty_level"
                )
            ),

            "risk_level": components[
                "risk_level"
            ],

            "risk_score": e10_result.get(
                "risk_score"
            ),

            "risk_factors": e10_result.get(
                "risk_factors",
                []
            ),

            "complication_indicators": (
                e10_result.get(
                    "complication_indicators",
                    []
                )
            ),

            # ------------------------------------------------
            # Ranking components
            # ------------------------------------------------

            "ranking_components": {

                "success_score": components[
                    "success_score"
                ],

                "uncertainty_score": components[
                    "uncertainty_score"
                ],

                "recovery_score": components[
                    "recovery_score"
                ],

                "risk_score": components[
                    "risk_score"
                ],

                "availability_score": components[
                    "availability_score"
                ],

                "guideline_score": components[
                    "guideline_score"
                ],

                "resource_score": components[
                    "resource_score"
                ]
            },

            # ------------------------------------------------
            # Weighted contributions
            # ------------------------------------------------

            "weighted_contributions": {

                "success": components[
                    "weighted_success"
                ],

                "uncertainty": components[
                    "weighted_uncertainty"
                ],

                "recovery": components[
                    "weighted_recovery"
                ],

                "risk": components[
                    "weighted_risk"
                ],

                "availability": components[
                    "weighted_availability"
                ],

                "guideline": components[
                    "weighted_guideline"
                ],

                "resource": components[
                    "weighted_resource"
                ]
            },

            # ------------------------------------------------
            # E11 explanation
            # ------------------------------------------------

            "shap_explanation": (
                e11_result
            ),

            # ------------------------------------------------
            # Human-readable ranking explanation
            # ------------------------------------------------

            "ranking_explanation": explanation,

            # ------------------------------------------------
            # Interpretation
            # ------------------------------------------------

            "interpretation": (
                "E12 ranking is a project-defined analytical "
                "ranking based on model predictions and "
                "configuration factors. It is not a clinical "
                "prescribing decision or medically validated "
                "treatment recommendation."
            )
        })

    # --------------------------------------------------------
    # Sort
    #
    # Primary:
    #     final score descending
    #
    # Tie-breakers:
    #     success probability descending
    #     recovery time ascending
    #     treatment ID ascending
    # --------------------------------------------------------

    ranking_records.sort(
        key=lambda record: (
            -record["final_score"],
            -record[
                "calibrated_success_probability"
            ],
            record[
                "expected_recovery_days"
            ],
            record[
                "treatment_id"
            ]
        )
    )

    # --------------------------------------------------------
    # Assign ranks
    # --------------------------------------------------------

    for rank, record in enumerate(
        ranking_records,
        start=1
    ):

        record["rank"] = rank

    return {
        "ranked_treatments": ranking_records,
        "excluded_treatments": excluded_records,
        "ranking_weights": dict(
            RANKING_WEIGHTS
        ),
        "ranking_method": (
            "Project-defined weighted analytical "
            "treatment ranking"
        ),
        "interpretation": (
            "Ranking integrates treatment-success "
            "probability, predictive uncertainty, "
            "recovery estimate, risk indicators, "
            "availability, project configuration support, "
            "and resource tier. It is not a clinical "
            "prescribing decision."
        )
    }


# ============================================================
# VALIDATE RANKING OUTPUT
# ============================================================

def validate_ranking_output(
    ranking_output
):
    """
    Validate the complete E12 ranking output.
    """

    if not isinstance(
        ranking_output,
        dict
    ):

        raise RuntimeError(
            "E12 output must be a dictionary."
        )

    required_top_level = [
        "ranked_treatments",
        "excluded_treatments",
        "ranking_weights",
        "ranking_method",
        "interpretation"
    ]

    for field in required_top_level:

        if field not in ranking_output:

            raise RuntimeError(
                f"E12 output missing '{field}'."
            )

    ranked = ranking_output[
        "ranked_treatments"
    ]

    if not isinstance(
        ranked,
        list
    ):

        raise RuntimeError(
            "E12 ranked_treatments must be a list."
        )

    # --------------------------------------------------------
    # Validate weights
    # --------------------------------------------------------

    weights = ranking_output[
        "ranking_weights"
    ]

    if not np.isclose(
        sum(weights.values()),
        1.0,
        atol=1e-9
    ):

        raise RuntimeError(
            "E12 ranking weights do not sum to 1."
        )

    # --------------------------------------------------------
    # Validate ranks
    # --------------------------------------------------------

    expected_ranks = list(
        range(
            1,
            len(ranked) + 1
        )
    )

    actual_ranks = [
        result.get(
            "rank"
        )
        for result in ranked
    ]

    if actual_ranks != expected_ranks:

        raise RuntimeError(
            "E12 ranks are not sequential."
        )

    # --------------------------------------------------------
    # Validate individual results
    # --------------------------------------------------------

    required_fields = [

        "rank",
        "treatment_id",
        "treatment_name",
        "final_score",
        "eligibility_status",
        "guideline_status",
        "availability",
        "resource_tier",
        "calibrated_success_probability",
        "uncertainty_level",
        "uncertainty_lower",
        "uncertainty_upper",
        "expected_recovery_days",
        "recovery_lower_days",
        "recovery_upper_days",
        "risk_level",
        "risk_score",
        "risk_factors",
        "complication_indicators",
        "ranking_components",
        "weighted_contributions",
        "ranking_explanation",
        "interpretation"
    ]

    for result in ranked:

        for field in required_fields:

            if field not in result:

                raise RuntimeError(
                    "E12 treatment result missing "
                    f"field: {field}"
                )

        # ----------------------------------------------------
        # Final score
        # ----------------------------------------------------

        final_score = result[
            "final_score"
        ]

        if not np.isfinite(
            final_score
        ):

            raise RuntimeError(
                "E12 final score is not finite."
            )

        if not (
            0.0
            <= final_score
            <= 1.0
        ):

            raise RuntimeError(
                "E12 final score is outside [0,1]."
            )

        # ----------------------------------------------------
        # Success probability
        # ----------------------------------------------------

        probability = result[
            "calibrated_success_probability"
        ]

        if not (
            0.0
            <= probability
            <= 1.0
        ):

            raise RuntimeError(
                "E12 calibrated probability is outside [0,1]."
            )

        # ----------------------------------------------------
        # Uncertainty interval
        # ----------------------------------------------------

        lower = result[
            "uncertainty_lower"
        ]

        upper = result[
            "uncertainty_upper"
        ]

        if lower is not None and upper is not None:

            if not (
                0.0
                <= float(lower)
                <= float(upper)
                <= 1.0
            ):

                raise RuntimeError(
                    "E12 uncertainty interval is invalid."
                )

        # ----------------------------------------------------
        # Recovery
        # ----------------------------------------------------

        expected = result[
            "expected_recovery_days"
        ]

        if float(expected) < 0:

            raise RuntimeError(
                "E12 expected recovery cannot be negative."
            )

        # ----------------------------------------------------
        # Risk
        # ----------------------------------------------------

        if result[
            "risk_level"
        ] not in {
            "LOW",
            "MODERATE",
            "HIGH"
        }:

            raise RuntimeError(
                "E12 returned invalid risk level."
            )

        # ----------------------------------------------------
        # Uncertainty
        # ----------------------------------------------------

        if result[
            "uncertainty_level"
        ] not in {
            "LOW",
            "MODERATE",
            "HIGH",
            "UNKNOWN"
        }:

            raise RuntimeError(
                "E12 returned invalid uncertainty level."
            )

        # ----------------------------------------------------
        # Lists
        # ----------------------------------------------------

        if not isinstance(
            result["risk_factors"],
            list
        ):

            raise RuntimeError(
                "E12 risk_factors must be a list."
            )

        if not isinstance(
            result["complication_indicators"],
            list
        ):

            raise RuntimeError(
                "E12 complication_indicators must be a list."
            )

        # ----------------------------------------------------
        # Component dictionaries
        # ----------------------------------------------------

        if not isinstance(
            result["ranking_components"],
            dict
        ):

            raise RuntimeError(
                "E12 ranking_components must be a dictionary."
            )

        if not isinstance(
            result["weighted_contributions"],
            dict
        ):

            raise RuntimeError(
                "E12 weighted_contributions must be a dictionary."
            )

    # --------------------------------------------------------
    # Check descending ranking order
    # --------------------------------------------------------

    scores = [
        result[
            "final_score"
        ]
        for result in ranked
    ]

    for i in range(
        1,
        len(scores)
    ):

        if scores[i] > scores[i - 1] + 1e-12:

            raise RuntimeError(
                "E12 ranking is not sorted by final score."
            )

    return True


# ============================================================
# DISPLAY RANKING
# ============================================================

def display_ranking(
    ranking_output
):
    """
    Display the final E12 treatment ranking.
    """

    ranked = ranking_output[
        "ranked_treatments"
    ]

    excluded = ranking_output[
        "excluded_treatments"
    ]

    print()
    print("=" * 70)
    print("E12 FINAL TREATMENT RANKING")
    print("=" * 70)

    if not ranked:

        print(
            "\nNo rankable treatment candidates."
        )

    for result in ranked:

        print()
        print(
            f"RANK {result['rank']}"
        )

        print(
            "-" * 70
        )

        print(
            f"Treatment ID        : "
            f"{result['treatment_id']}"
        )

        print(
            f"Treatment name      : "
            f"{result['treatment_name']}"
        )

        print(
            f"Final score         : "
            f"{result['final_score']:.4f}"
        )

        print(
            f"Success probability : "
            f"{result['calibrated_success_probability']:.4f}"
        )

        print(
            f"Uncertainty         : "
            f"{result['uncertainty_level']}"
        )

        print(
            f"Uncertainty interval: "
            f"{result['uncertainty_lower']:.4f} - "
            f"{result['uncertainty_upper']:.4f}"
        )

        print(
            f"Expected recovery  : "
            f"{result['expected_recovery_days']:.2f} days"
        )

        print(
            f"Recovery interval   : "
            f"{result['recovery_lower_days']:.2f} - "
            f"{result['recovery_upper_days']:.2f} days"
        )

        print(
            f"Risk level          : "
            f"{result['risk_level']}"
        )

        print(
            f"Availability        : "
            f"{result['availability']}"
        )

        print(
            f"Guideline status    : "
            f"{result['guideline_status']}"
        )

        print(
            f"Resource tier       : "
            f"{result['resource_tier']}"
        )

        print()
        print(
            "Ranking components:"
        )

        components = result[
            "ranking_components"
        ]

        print(
            f"  Success       : "
            f"{components['success_score']:.4f}"
        )

        print(
            f"  Uncertainty   : "
            f"{components['uncertainty_score']:.4f}"
        )

        print(
            f"  Recovery      : "
            f"{components['recovery_score']:.4f}"
        )

        print(
            f"  Risk          : "
            f"{components['risk_score']:.4f}"
        )

        print(
            f"  Availability  : "
            f"{components['availability_score']:.4f}"
        )

        print(
            f"  Guideline     : "
            f"{components['guideline_score']:.4f}"
        )

        print(
            f"  Resource      : "
            f"{components['resource_score']:.4f}"
        )

        print()
        print(
            "Explanation:"
        )

        print(
            f"  {result['ranking_explanation']}"
        )

    # --------------------------------------------------------
    # Excluded treatments
    # --------------------------------------------------------

    if excluded:

        print()
        print("=" * 70)
        print("EXCLUDED TREATMENTS")
        print("=" * 70)

        for result in excluded:

            print(
                f"{result['treatment_id']} - "
                f"{result['treatment_name']}: "
                f"{result['reason']}"
            )

    # --------------------------------------------------------
    # Method
    # --------------------------------------------------------

    print()
    print("=" * 70)

    print(
        "Ranking method:"
    )

    print(
        ranking_output[
            "ranking_method"
        ]
    )

    print()
    print(
        "Weights:"
    )

    for name, weight in (
        ranking_output[
            "ranking_weights"
        ].items()
    ):

        print(
            f"  {name}: {weight:.2f}"
        )

    print()
    print(
        "Interpretation:"
    )

    print(
        ranking_output[
            "interpretation"
        ]
    )


# ============================================================
# E12 PIPELINE TEST
# ============================================================

def run_e12_pipeline_test():
    """
    Test the complete E1 -> E2 -> E3 -> E4 -> E5 -> E6
    -> E7 -> E8 -> E9 -> E10 -> E11 -> E12 flow.

    E5 is retrieved for context but does not currently
    contribute a numerical ranking score.

    This is intentional: E5 provides regional epidemiological
    context, while E12 ranking is based on the treatment-specific
    outputs currently available from E4 and E6-E11.

    E13 can expose the regional context alongside the ranking.
    """

    print()
    print("=" * 70)
    print("E12 PIPELINE TEST")
    print("=" * 70)

    # ========================================================
    # IMPORT PROJECT MODULES
    # ========================================================

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

    from ML.treatment_advisor.treatment_model import (
        find_valid_test_encounter
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

    # ========================================================
    # FIND VALID TEST ENCOUNTER
    # ========================================================

    (
        encounter_id,
        context
    ) = find_valid_test_encounter()

    print()
    print(
        f"Encounter ID : {encounter_id}"
    )

    print(
        f"Disease      : "
        f"{context.get('disease_id')}"
    )

    print(
        f"Severity     : "
        f"{context.get('severity_id')}"
    )

    print(
        "E1 context: VALID"
    )

    # ========================================================
    # E2
    # ========================================================

    (
        context,
        candidates,
        candidate_records
    ) = generate_candidates_for_encounter(
        encounter_id
    )

    if (
        candidates is None
        or candidates.empty
    ):

        raise RuntimeError(
            "E2 produced no candidates."
        )

    print(
        f"E2 candidates: {len(candidates)}"
    )

    # ========================================================
    # E3
    # ========================================================

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

    print(
        f"E3 candidates: {len(eligible)}"
    )

    # ========================================================
    # HOSPITAL
    # ========================================================

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
        hospital_df.iloc[0][
            "hospital_id"
        ]
    )

    print(
        f"Hospital     : {hospital_id}"
    )

    # ========================================================
    # E4
    # ========================================================

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

    print(
        f"E4 candidates: {len(enriched)}"
    )

    # ========================================================
    # E5
    # ========================================================
    #
    # E5 is regional epidemiological context.
    #
    # We retrieve it if available, but do not use it as a
    # numerical ranking component in this E12 version.
    #
    # This preserves the separation between:
    #     surveillance context
    # and
    #     treatment ranking.
    #
    # ========================================================

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

        print(
            "E5 regional context: AVAILABLE"
        )

    except Exception as e:

        print(
            "E5 regional context: "
            "not used in ranking "
            f"({type(e).__name__})"
        )

    # ========================================================
    # TREATMENT IDS
    # ========================================================

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
            "No treatment IDs available."
        )

    # ========================================================
    # E7 + E8 RESULTS
    # ========================================================

    print(
        "Generating E7 + E8 treatment predictions..."
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

        # --------------------------------------------
        # E7 result
        # --------------------------------------------

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

        # --------------------------------------------
        # E8 result
        # --------------------------------------------

        e8_results.append(
            prediction
        )

    # ========================================================
    # E9 RESULTS
    # ========================================================

    print(
        "Generating E9 recovery estimates..."
    )

    e9_results = (
        predict_recovery_for_treatments(
            context,
            treatment_ids
        )
    )

    # ========================================================
    # E10 RESULTS
    # ========================================================

    print(
        "Generating E10 risk assessments..."
    )

    e10_results = (
        assess_risk_for_treatments(
            context,
            enriched
        )
    )

    # ========================================================
    # E11 RESULTS
    # ========================================================

    print(
        "Generating E11 SHAP explanations..."
    )

    e11_results = explain_treatments(
        context,
        treatment_ids
    )

    # ========================================================
    # E12 RANKING
    # ========================================================

    print()
    print(
        "Generating E12 final ranking..."
    )

    ranking_output = rank_treatments(
        enriched_candidates=enriched,
        e7_results=e7_results,
        e8_results=e8_results,
        e9_results=e9_results,
        e10_results=e10_results,
        e11_results=e11_results
    )

    # ========================================================
    # VALIDATE
    # ========================================================

    validate_ranking_output(
        ranking_output
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    display_ranking(
        ranking_output
    )

    # ========================================================
    # OPTIONAL E5 CONTEXT DISPLAY
    # ========================================================

    if regional_context is not None:

        print()
        print("=" * 70)
        print("E5 REGIONAL CONTEXT")
        print("=" * 70)

        if isinstance(
            regional_context,
            dict
        ):

            for key, value in (
                regional_context.items()
            ):

                print(
                    f"{key}: {value}"
                )

        else:

            print(
                regional_context
            )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if len(
        ranking_output[
            "ranked_treatments"
        ]
    ) == 0:

        raise RuntimeError(
            "E12 produced no ranked treatments."
        )

    print()
    print("=" * 70)
    print("E12 VALIDATION: PASSED")
    print("=" * 70)

    return ranking_output


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("E12 - FINAL TREATMENT RANKING")
    print("=" * 70)

    # --------------------------------------------------------
    # Validate configuration
    # --------------------------------------------------------

    validate_ranking_weights()

    print()
    print(
        "Ranking weights validated."
    )

    # --------------------------------------------------------
    # Pipeline test
    # --------------------------------------------------------

    run_e12_pipeline_test()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
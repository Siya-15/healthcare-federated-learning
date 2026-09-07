"""
E10 - Risk & Complication Estimation

Purpose
-------
Assess treatment-related risk indicators and potential complications
using patient clinical context and treatment configuration.

E10 is intentionally separate from:
    E6 - Treatment success prediction
    E7 - Probability calibration
    E8 - Treatment probability uncertainty
    E9 - Recovery time estimation

Important interpretation
------------------------
This is a project-level risk assessment layer.

It is NOT:
    - a clinical diagnosis
    - a causal adverse-event prediction
    - a guaranteed complication probability
    - an autonomous prescribing decision

Risk thresholds and complication mappings used here are
project-defined unless explicitly backed by project data.
"""

from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

E4_DATA_DIR = BASE_DIR / "e4_data"

RISK_CONFIG_PATH = (
    E4_DATA_DIR / "treatment_risk_config.csv"
)


# ============================================================
# PROJECT RISK THRESHOLDS
# ============================================================

# These are project-defined prototype thresholds.
# They are NOT clinical diagnostic thresholds.

TEMPERATURE_HIGH = 38.0
HEART_RATE_HIGH = 100.0
RESPIRATORY_RATE_HIGH = 22.0
SPO2_LOW = 94.0
SYSTOLIC_BP_LOW = 90.0
SYSTOLIC_BP_HIGH = 140.0


# ============================================================
# LOAD RISK CONFIGURATION
# ============================================================

def load_risk_configuration():
    """
    Load optional treatment risk configuration.

    If the configuration file does not yet exist, E10 can still
    operate using patient-context risk indicators and E4 metadata.
    """

    if not RISK_CONFIG_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(
        RISK_CONFIG_PATH
    )

    return df


# ============================================================
# PATIENT RISK INDICATORS
# ============================================================

def assess_patient_risk_indicators(patient_context):
    """
    Identify risk indicators from the patient's clinical context.

    These are project-defined analytical indicators and should
    not be interpreted as clinical diagnoses.
    """

    indicators = []

    vitals = patient_context.get(
        "vitals",
        {}
    )

    severity_id = patient_context.get(
        "severity_id"
    )

    temperature = vitals.get(
        "temperature"
    )

    heart_rate = vitals.get(
        "heart_rate"
    )

    respiratory_rate = vitals.get(
        "respiratory_rate"
    )

    spo2 = vitals.get(
        "spo2"
    )

    systolic_bp = vitals.get(
        "systolic_bp"
    )

    # --------------------------------------------------------
    # Severity
    # --------------------------------------------------------

    if severity_id == "SV003":

        indicators.append(
            "High severity classification"
        )

    elif severity_id == "SV002":

        indicators.append(
            "Moderate severity classification"
        )

    # --------------------------------------------------------
    # Temperature
    # --------------------------------------------------------

    if temperature is not None:

        try:
            temperature = float(temperature)

            if temperature >= TEMPERATURE_HIGH:

                indicators.append(
                    "Elevated temperature"
                )

        except (TypeError, ValueError):
            pass

    # --------------------------------------------------------
    # Heart rate
    # --------------------------------------------------------

    if heart_rate is not None:

        try:
            heart_rate = float(heart_rate)

            if heart_rate >= HEART_RATE_HIGH:

                indicators.append(
                    "Elevated heart rate"
                )

        except (TypeError, ValueError):
            pass

    # --------------------------------------------------------
    # Respiratory rate
    # --------------------------------------------------------

    if respiratory_rate is not None:

        try:
            respiratory_rate = float(
                respiratory_rate
            )

            if respiratory_rate >= RESPIRATORY_RATE_HIGH:

                indicators.append(
                    "Elevated respiratory rate"
                )

        except (TypeError, ValueError):
            pass

    # --------------------------------------------------------
    # Oxygen saturation
    # --------------------------------------------------------

    if spo2 is not None:

        try:
            spo2 = float(spo2)

            if spo2 < SPO2_LOW:

                indicators.append(
                    "Low oxygen saturation"
                )

        except (TypeError, ValueError):
            pass

    # --------------------------------------------------------
    # Systolic blood pressure
    # --------------------------------------------------------

    if systolic_bp is not None:

        try:
            systolic_bp = float(
                systolic_bp
            )

            if systolic_bp < SYSTOLIC_BP_LOW:

                indicators.append(
                    "Low systolic blood pressure"
                )

            elif systolic_bp >= SYSTOLIC_BP_HIGH:

                indicators.append(
                    "Elevated systolic blood pressure"
                )

        except (TypeError, ValueError):
            pass

    return indicators


# ============================================================
# RISK SCORE
# ============================================================

def calculate_risk_score(
    patient_context,
    treatment_record=None
):
    """
    Calculate a project-defined analytical risk score.

    The score is NOT a probability of a clinical adverse event.

    Score components:
        - severity
        - abnormal vital indicators
        - treatment review requirements
        - inpatient requirement
    """

    score = 0

    patient_indicators = (
        assess_patient_risk_indicators(
            patient_context
        )
    )

    # --------------------------------------------------------
    # Patient indicators
    # --------------------------------------------------------

    score += len(patient_indicators)

    # --------------------------------------------------------
    # Severity weighting
    # --------------------------------------------------------

    severity_id = patient_context.get(
        "severity_id"
    )

    if severity_id == "SV003":

        score += 2

    elif severity_id == "SV002":

        score += 1

    # --------------------------------------------------------
    # Treatment configuration
    # --------------------------------------------------------

    if treatment_record is not None:

        # Referral requirement
        if bool(
            treatment_record.get(
                "referral_required",
                False
            )
        ):

            score += 1

        # Inpatient requirement
        if bool(
            treatment_record.get(
                "inpatient_required",
                False
            )
        ):

            score += 1

        # Guideline review
        guideline_status = treatment_record.get(
            "guideline_status"
        )

        if guideline_status == "PROJECT_SUPPORTED_REVIEW":

            score += 1

    return int(score)


# ============================================================
# RISK CLASSIFICATION
# ============================================================

def classify_risk(score):
    """
    Convert the project-defined analytical score into
    LOW / MODERATE / HIGH risk.

    These categories are project-defined.
    """

    if score <= 2:

        return "LOW"

    elif score <= 5:

        return "MODERATE"

    else:

        return "HIGH"


# ============================================================
# TREATMENT-SPECIFIC RISK
# ============================================================

def assess_treatment_risk(
    patient_context,
    treatment_record=None
):
    """
    Generate the complete E10 risk assessment for one
    patient-treatment combination.
    """

    patient_indicators = (
        assess_patient_risk_indicators(
            patient_context
        )
    )

    score = calculate_risk_score(
        patient_context,
        treatment_record
    )

    risk_level = classify_risk(
        score
    )

    treatment_id = None

    if treatment_record is not None:

        treatment_id = treatment_record.get(
            "treatment_id"
        )

    # --------------------------------------------------------
    # Treatment configuration factors
    # --------------------------------------------------------

    treatment_factors = []

    if treatment_record is not None:

        if bool(
            treatment_record.get(
                "referral_required",
                False
            )
        ):

            treatment_factors.append(
                "Referral/review required"
            )

        if bool(
            treatment_record.get(
                "inpatient_required",
                False
            )
        ):

            treatment_factors.append(
                "Inpatient care requirement"
            )

        if treatment_record.get(
            "availability"
        ) == "LIMITED":

            treatment_factors.append(
                "Limited treatment availability"
            )

        if treatment_record.get(
            "availability"
        ) == "UNAVAILABLE":

            treatment_factors.append(
                "Treatment currently unavailable"
            )

    # --------------------------------------------------------
    # Combined risk factors
    # --------------------------------------------------------

    risk_factors = (
        patient_indicators
        + treatment_factors
    )

    # --------------------------------------------------------
    # Complication indicators
    # --------------------------------------------------------

    complication_indicators = []

    if "Low oxygen saturation" in patient_indicators:

        complication_indicators.append(
            "Respiratory compromise indicator"
        )

    if "Elevated respiratory rate" in patient_indicators:

        complication_indicators.append(
            "Respiratory stress indicator"
        )

    if "Elevated heart rate" in patient_indicators:

        complication_indicators.append(
            "Cardiovascular stress indicator"
        )

    if (
        "Low systolic blood pressure"
        in patient_indicators
    ):

        complication_indicators.append(
            "Hemodynamic instability indicator"
        )

    if severity_id := patient_context.get(
        "severity_id"
    ):

        if severity_id == "SV003":

            complication_indicators.append(
                "Severe-condition complication monitoring indicator"
            )

    return {
        "treatment_id": treatment_id,
        "risk_score": score,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "complication_indicators": (
            complication_indicators
        ),
        "risk_method": (
            "Project-defined rule-based analytical "
            "risk assessment"
        ),
        "interpretation": (
            "Risk indicators are analytical prototype outputs "
            "and are not clinical adverse-event probabilities."
        )
    }


# ============================================================
# MULTIPLE TREATMENTS
# ============================================================

def assess_risk_for_treatments(
    patient_context,
    treatment_records
):
    """
    Assess risk for multiple treatment candidates.

    treatment_records may be:
        - a list of dictionaries
        - a pandas DataFrame
    """

    results = []

    if isinstance(
        treatment_records,
        pd.DataFrame
    ):

        records = (
            treatment_records
            .to_dict("records")
        )

    elif isinstance(
        treatment_records,
        list
    ):

        records = treatment_records

    else:

        raise TypeError(
            "treatment_records must be a DataFrame "
            "or list of dictionaries."
        )

    for record in records:

        results.append(
            assess_treatment_risk(
                patient_context,
                record
            )
        )

    return results


# ============================================================
# E10 PIPELINE TEST
# ============================================================

def run_e10_pipeline_test():
    """
    Test canonical E1 -> E2 -> E3 -> E4 -> E10 flow.
    """

    print()
    print("=" * 70)
    print("E10 PIPELINE TEST")
    print("=" * 70)

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

    # ========================================================
    # FIND TEST ENCOUNTER
    # ========================================================

    engine = get_database_engine()

    query = """
        SELECT
            encounter_id,
            hospital_id
        FROM patient_encounter
        WHERE recovery_days IS NOT NULL
        ORDER BY visit_timestamp
        LIMIT 500
    """

    encounters = pd.read_sql(
        query,
        engine
    )

    if encounters.empty:

        raise RuntimeError(
            "No suitable E10 test encounters found."
        )

    last_error = None

    for _, row in encounters.iterrows():

        encounter_id = row[
            "encounter_id"
        ]

        hospital_id = row[
            "hospital_id"
        ]

        try:

            # ------------------------------------------------
            # E1 + E2
            # ------------------------------------------------

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

                continue

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
                f"Hospital     : "
                f"{hospital_id}"
            )

            print("E1 context: VALID")

            print(
                f"E2 candidates: "
                f"{len(candidates)}"
            )

            # ------------------------------------------------
            # E3
            # ------------------------------------------------

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

                continue

            print(
                f"E3 candidates: "
                f"{len(eligible)}"
            )

            # ------------------------------------------------
            # E4
            # ------------------------------------------------

            enriched = enrich_candidates(
                eligible,
                hospital_id
            )

            if (
                enriched is None
                or enriched.empty
            ):

                continue

            print(
                f"E4 candidates: "
                f"{len(enriched)}"
            )

            # ------------------------------------------------
            # E10
            # ------------------------------------------------

            risk_results = (
                assess_risk_for_treatments(
                    context,
                    enriched
                )
            )

            if not risk_results:

                continue

            # ------------------------------------------------
            # Display
            # ------------------------------------------------

            print()
            print("-" * 70)
            print("E10 RISK & COMPLICATION ASSESSMENT")
            print("-" * 70)

            for result in risk_results:

                print()

                print(
                    f"Treatment ID: "
                    f"{result['treatment_id']}"
                )

                print(
                    f"Risk score: "
                    f"{result['risk_score']}"
                )

                print(
                    f"Risk level: "
                    f"{result['risk_level']}"
                )

                print(
                    "Risk factors: "
                    + (
                        ", ".join(
                            result["risk_factors"]
                        )
                        if result["risk_factors"]
                        else "None identified"
                    )
                )

                print(
                    "Complication indicators: "
                    + (
                        ", ".join(
                            result[
                                "complication_indicators"
                            ]
                        )
                        if result[
                            "complication_indicators"
                        ]
                        else "None identified"
                    )
                )

            # ------------------------------------------------
            # Validation
            # ------------------------------------------------

            valid_levels = {
                "LOW",
                "MODERATE",
                "HIGH"
            }

            for result in risk_results:

                if (
                    result["risk_level"]
                    not in valid_levels
                ):

                    raise RuntimeError(
                        "E10 returned invalid risk level."
                    )

                if result["risk_score"] < 0:

                    raise RuntimeError(
                        "E10 produced negative risk score."
                    )

                if not isinstance(
                    result["risk_factors"],
                    list
                ):

                    raise RuntimeError(
                        "E10 risk_factors must be a list."
                    )

                if not isinstance(
                    result[
                        "complication_indicators"
                    ],
                    list
                ):

                    raise RuntimeError(
                        "E10 complication_indicators "
                        "must be a list."
                    )

            print()
            print("=" * 70)
            print("E10 VALIDATION: PASSED")
            print("=" * 70)

            return

        except Exception as e:

            last_error = e
            continue

    if last_error is not None:

        raise RuntimeError(
            "Could not complete E10 pipeline test. "
            f"Last encountered error: {last_error}"
        )

    raise RuntimeError(
        "Could not find a valid E10 test encounter."
    )


# ============================================================
# DATABASE ENGINE
# ============================================================

def get_database_engine():
    """
    Import the project's existing database engine.
    """

    try:

        from database import get_engine

        return get_engine()

    except ImportError:

        raise ImportError(
            "Could not import project database engine."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("E10 - RISK & COMPLICATION ESTIMATION")
    print("=" * 70)

    run_e10_pipeline_test()


if __name__ == "__main__":
    main()
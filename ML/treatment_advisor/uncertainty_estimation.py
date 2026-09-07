"""
E8 - Uncertainty Estimation

Estimates model-based predictive uncertainty for the calibrated
treatment-success probability produced by E6 + E7.

Pipeline:

    E1 Patient Context
        ↓
    E2 Candidate Treatments
        ↓
    E3 Clinical Eligibility
        ↓
    E4 Configuration
        ↓
    E6 Random Forest
        ↓
    E7 Probability Calibration
        ↓
    E8 Uncertainty

Important:
- E6 is not modified.
- E7 is not modified.
- E8 uses variation across Random Forest trees.
- The resulting interval is a model-based predictive uncertainty
  interval, NOT a formal statistical confidence interval.
- Uncertainty thresholds are project-defined and are not clinical
  thresholds.
- This output is not a causal treatment-effect estimate.
- This output is not an autonomous prescribing decision.
"""


import os
import sys

# ==========================================================
# ALLOW IMPORT FROM PROJECT ROOT
# ==========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


import joblib
import numpy as np
import pandas as pd

from sqlalchemy import text

from sklearn.metrics import (
    brier_score_loss,
    roc_auc_score
)
from sklearn.model_selection import GroupShuffleSplit

from database import get_engine


# ==========================================================
# ARTIFACT PATHS
# ==========================================================

E6_MODEL_FILENAME = (
    "treatment_success_model.pkl"
)

E7_CALIBRATION_FILENAME = (
    "treatment_probability_calibrator.pkl"
)

E8_UNCERTAINTY_FILENAME = (
    "treatment_probability_uncertainty.pkl"
)


E6_MODEL_PATH = os.path.join(
    PROJECT_ROOT,
    E6_MODEL_FILENAME
)

E7_CALIBRATION_PATH = os.path.join(
    PROJECT_ROOT,
    E7_CALIBRATION_FILENAME
)

E8_UNCERTAINTY_PATH = os.path.join(
    PROJECT_ROOT,
    E8_UNCERTAINTY_FILENAME
)


# ==========================================================
# CONFIGURATION
# ==========================================================

RANDOM_STATE = 42

EVALUATION_TEST_SIZE = 0.20

# ----------------------------------------------------------
# Quantiles used for model uncertainty.
#
# 10th percentile
# 90th percentile
#
# These are predictive-spread bounds, not confidence
# intervals.
# ----------------------------------------------------------

LOWER_QUANTILE = 0.10
UPPER_QUANTILE = 0.90


# ==========================================================
# PROJECT UNCERTAINTY THRESHOLDS
# ==========================================================
#
# These thresholds classify the WIDTH of the model-based
# predictive interval.
#
# They are NOT medical/clinical thresholds.
#
# LOW:
#       interval width < 0.10
#
# MODERATE:
#       0.10 <= width < 0.20
#
# HIGH:
#       interval width >= 0.20
#
# ==========================================================

LOW_UNCERTAINTY_WIDTH = 0.10
MODERATE_UNCERTAINTY_WIDTH = 0.20


# ==========================================================
# LOAD E6 MODEL
# ==========================================================

def load_e6_model():

    if not os.path.exists(
        E6_MODEL_PATH
    ):

        raise FileNotFoundError(
            "E6 model artifact not found:\n"
            f"{E6_MODEL_PATH}\n\n"
            "Run E6 first."
        )

    artifact = joblib.load(
        E6_MODEL_PATH
    )

    if not isinstance(
        artifact,
        dict
    ):

        raise ValueError(
            "Invalid E6 model artifact."
        )

    if "model" not in artifact:

        raise ValueError(
            "E6 artifact missing 'model'."
        )

    if "feature_names" not in artifact:

        raise ValueError(
            "E6 artifact missing 'feature_names'."
        )

    model = artifact[
        "model"
    ]

    feature_names = artifact[
        "feature_names"
    ]

    if not hasattr(
        model,
        "estimators_"
    ):

        raise ValueError(
            "E6 model does not expose Random Forest "
            "estimators."
        )

    if not hasattr(
        model,
        "predict_proba"
    ):

        raise ValueError(
            "E6 model does not support predict_proba()."
        )

    if not feature_names:

        raise ValueError(
            "E6 feature list is empty."
        )

    return (
        model,
        feature_names
    )


# ==========================================================
# LOAD E7 CALIBRATOR
# ==========================================================

def load_e7_calibrator():

    if not os.path.exists(
        E7_CALIBRATION_PATH
    ):

        raise FileNotFoundError(
            "E7 calibration artifact not found:\n"
            f"{E7_CALIBRATION_PATH}\n\n"
            "Run E7 first."
        )

    artifact = joblib.load(
        E7_CALIBRATION_PATH
    )

    if not isinstance(
        artifact,
        dict
    ):

        raise ValueError(
            "Invalid E7 calibration artifact."
        )

    if "calibrator" not in artifact:

        raise ValueError(
            "E7 artifact missing calibrator."
        )

    calibrator = artifact[
        "calibrator"
    ]

    if not hasattr(
        calibrator,
        "predict_proba"
    ):

        raise ValueError(
            "E7 calibrator does not support predict_proba()."
        )

    return (
        calibrator,
        artifact
    )


# ==========================================================
# BUILD INFERENCE FEATURES
# ==========================================================

def build_prediction_features(
    patient_context,
    treatment_id,
    feature_names
):
    """
    Construct the exact feature representation expected by E6.

    This mirrors the E6 inference interface so E8 can work with
    the same patient-context representation.
    """

    row = {}

    # ------------------------------------------------------
    # Numerical features
    # ------------------------------------------------------

    numerical_features = [
        "age",
        "temperature",
        "heart_rate",
        "respiratory_rate",
        "systolic_bp",
        "diastolic_bp",
        "spo2",
    ]

    for feature in numerical_features:

        row[feature] = patient_context.get(
            feature,
            0
        )

    # ------------------------------------------------------
    # Categorical values
    # ------------------------------------------------------

    categorical_values = {

        "gender": patient_context.get(
            "gender",
            ""
        ),

        "disease_id": patient_context.get(
            "disease_id",
            ""
        ),

        "severity_id": patient_context.get(
            "severity_id",
            ""
        ),

        "treatment_id": treatment_id
    }

    # ------------------------------------------------------
    # Identify symptom columns
    # ------------------------------------------------------

    symptom_columns = [

        column

        for column in feature_names

        if column not in numerical_features

        and not column.startswith(
            "gender_"
        )

        and not column.startswith(
            "disease_id_"
        )

        and not column.startswith(
            "severity_id_"
        )

        and not column.startswith(
            "treatment_id_"
        )
    ]

    # ------------------------------------------------------
    # Patient symptoms
    # ------------------------------------------------------

    patient_symptoms = patient_context.get(
        "symptoms",
        []
    )

    if isinstance(
        patient_symptoms,
        dict
    ):

        active_symptoms = {

            name

            for name, value
            in patient_symptoms.items()

            if value
        }

    elif isinstance(
        patient_symptoms,
        list
    ):

        active_symptoms = set(
            patient_symptoms
        )

    else:

        active_symptoms = set()

    for symptom in symptom_columns:

        row[symptom] = (

            1

            if symptom
            in active_symptoms

            else 0
        )

    # ------------------------------------------------------
    # One-hot categorical features
    # ------------------------------------------------------

    for category, value in (
        categorical_values.items()
    ):

        prefix = (
            f"{category}_"
        )

        for feature in feature_names:

            if feature.startswith(
                prefix
            ):

                row[feature] = (

                    1

                    if str(value)
                    == feature[
                        len(prefix):
                    ]

                    else 0
                )

    # ------------------------------------------------------
    # Exact E6 schema
    # ------------------------------------------------------

    prediction = pd.DataFrame(
        [row]
    )

    prediction = prediction.reindex(
        columns=feature_names,
        fill_value=0
    )

    prediction = prediction.apply(
        pd.to_numeric,
        errors="coerce"
    ).fillna(0)

    return prediction


# ==========================================================
# GET INDIVIDUAL RANDOM FOREST TREE PROBABILITIES
# ==========================================================

def get_tree_probabilities(
    model,
    prediction_features
):
    """
    Generate a treatment-success probability from every
    Random Forest tree.

    Each tree provides its own probability estimate.

    Returns:
        numpy array of tree-level probabilities.
    """

    tree_probabilities = []

    for tree in model.estimators_:

        probability = tree.predict_proba(
            prediction_features
        )[0, 1]

        tree_probabilities.append(
            float(probability)
        )

    if not tree_probabilities:

        raise ValueError(
            "Random Forest contains no estimators."
        )

    return np.asarray(
        tree_probabilities,
        dtype=float
    )


# ==========================================================
# APPLY E7 CALIBRATION TO TREE PROBABILITIES
# ==========================================================

def calibrate_tree_probabilities(
    calibrator,
    tree_probabilities
):
    """
    Apply the E7 sigmoid calibrator independently to each
    Random Forest tree probability.

    This allows E8 uncertainty bounds to remain on the same
    calibrated probability scale used by E7.
    """

    probabilities = np.asarray(
        tree_probabilities,
        dtype=float
    )

    clipped = np.clip(
        probabilities,
        1e-6,
        1 - 1e-6
    )

    logit = np.log(
        clipped / (1 - clipped)
    )

    calibrated = calibrator.predict_proba(
        logit.reshape(-1, 1)
    )[:, 1]

    return np.clip(
        calibrated,
        0.0,
        1.0
    )


# ==========================================================
# CLASSIFY UNCERTAINTY
# ==========================================================

def classify_uncertainty(
    interval_width
):
    """
    Assign a project-defined uncertainty level based on
    model prediction spread.

    This is NOT a clinical threshold.
    """

    if interval_width < (
        LOW_UNCERTAINTY_WIDTH
    ):

        return "LOW"

    if interval_width < (
        MODERATE_UNCERTAINTY_WIDTH
    ):

        return "MODERATE"

    return "HIGH"


# ==========================================================
# CALCULATE UNCERTAINTY
# ==========================================================

def calculate_uncertainty(
    calibrated_tree_probabilities
):
    """
    Calculate model-based uncertainty from the calibrated
    Random Forest tree probability distribution.
    """

    probabilities = np.asarray(
        calibrated_tree_probabilities,
        dtype=float
    )

    if probabilities.size == 0:

        raise ValueError(
            "No tree probabilities available."
        )

    mean_probability = float(
        np.mean(probabilities)
    )

    std_probability = float(
        np.std(
            probabilities,
            ddof=1
        )
        if probabilities.size > 1
        else 0.0
    )

    lower_bound = float(
        np.quantile(
            probabilities,
            LOWER_QUANTILE
        )
    )

    upper_bound = float(
        np.quantile(
            probabilities,
            UPPER_QUANTILE
        )
    )

    interval_width = (
        upper_bound
        - lower_bound
    )

    uncertainty_level = (
        classify_uncertainty(
            interval_width
        )
    )

    return {

        "mean_calibrated_probability": (
            mean_probability
        ),

        "uncertainty_std": (
            std_probability
        ),

        "uncertainty_lower": (
            lower_bound
        ),

        "uncertainty_upper": (
            upper_bound
        ),

        "uncertainty_interval_width": (
            interval_width
        ),

        "uncertainty_level": (
            uncertainty_level
        ),

        "tree_count": int(
            probabilities.size
        )
    }


# ==========================================================
# PREDICT TREATMENT WITH UNCERTAINTY
# ==========================================================

def predict_treatment_with_uncertainty(
    patient_context,
    treatment_id
):
    """
    Produce the E6 + E7 + E8 result for one treatment.

    Output:
        E6 raw probability
        E7 calibrated probability
        E8 uncertainty
    """

    from ML.treatment_advisor.treatment_model import (
        predict_treatment_success
    )

    # ------------------------------------------------------
    # Load E6
    # ------------------------------------------------------

    model, feature_names = (
        load_e6_model()
    )

    # ------------------------------------------------------
    # Load E7
    # ------------------------------------------------------

    calibrator, e7_artifact = (
        load_e7_calibrator()
    )

    # ------------------------------------------------------
    # E6 raw prediction
    # ------------------------------------------------------

    e6_prediction = (
        predict_treatment_success(
            patient_context,
            treatment_id
        )
    )

    raw_probability = float(
        e6_prediction[
            "raw_success_probability"
        ]
    )

    # ------------------------------------------------------
    # Build features
    # ------------------------------------------------------

    prediction_features = (
        build_prediction_features(
            patient_context,
            treatment_id,
            feature_names
        )
    )

    # ------------------------------------------------------
    # Tree probabilities
    # ------------------------------------------------------

    tree_probabilities = (
        get_tree_probabilities(
            model,
            prediction_features
        )
    )

    # ------------------------------------------------------
    # Calibrate each tree
    # ------------------------------------------------------

    calibrated_tree_probabilities = (
        calibrate_tree_probabilities(
            calibrator,
            tree_probabilities
        )
    )

    # ------------------------------------------------------
    # E8 uncertainty
    # ------------------------------------------------------

    uncertainty = (
        calculate_uncertainty(
            calibrated_tree_probabilities
        )
    )

    # ------------------------------------------------------
    # Use E7 calibrated probability as the primary
    # calibrated probability.
    # ------------------------------------------------------

    e7_mean = float(
        calibrator.predict_proba(
            np.asarray([
                np.log(
                    np.clip(
                        raw_probability,
                        1e-6,
                        1 - 1e-6
                    )
                    /
                    (
                        1
                        -
                        np.clip(
                            raw_probability,
                            1e-6,
                            1 - 1e-6
                        )
                    )
                )
            ]).reshape(-1, 1)
        )[0, 1]
    )

    return {

        "treatment_id": treatment_id,

        "raw_success_probability": round(
            raw_probability,
            6
        ),

        "calibrated_success_probability": round(
            e7_mean,
            6
        ),

        "uncertainty_lower": round(
            uncertainty[
                "uncertainty_lower"
            ],
            6
        ),

        "uncertainty_upper": round(
            uncertainty[
                "uncertainty_upper"
            ],
            6
        ),

        "uncertainty_std": round(
            uncertainty[
                "uncertainty_std"
            ],
            6
        ),

        "uncertainty_interval_width": round(
            uncertainty[
                "uncertainty_interval_width"
            ],
            6
        ),

        "uncertainty_level": (
            uncertainty[
                "uncertainty_level"
            ]
        ),

        "tree_count": uncertainty[
            "tree_count"
        ],

        "uncertainty_method": (
            "Random Forest tree-level "
            "predictive spread after E7 calibration"
        ),

        "interval_interpretation": (
            "The lower and upper bounds represent "
            "model-based predictive uncertainty derived "
            "from variation across Random Forest trees. "
            "They are not formal statistical confidence "
            "intervals or clinical guarantees."
        )
    }


# ==========================================================
# TRAIN / VALIDATE E8 UNCERTAINTY BEHAVIOR
# ==========================================================

def evaluate_uncertainty_on_dataset():

    """
    Evaluate E8 model-based uncertainty on an
    encounter-disjoint evaluation set.

    E8 uncertainty is estimated from variation among
    Random Forest trees after applying the E7 calibrator.

    Important:
    - This is a predictive-spread diagnostic.
    - It is NOT a formal statistical confidence interval.
    """

    model, e6_feature_names = load_e6_model()

    calibrator, e7_artifact = (
        load_e7_calibrator()
    )

    # ------------------------------------------------------
    # Load E6-compatible dataset
    # ------------------------------------------------------

    from ML.treatment_advisor.treatment_model import (
        prepare_dataset
    )

    (
        data,
        feature_data,
        y,
        feature_names
    ) = prepare_dataset()

    X = feature_data.reindex(
        columns=e6_feature_names,
        fill_value=0
    )

    X = X.apply(
        pd.to_numeric,
        errors="coerce"
    ).fillna(0)

    # ------------------------------------------------------
    # Encounter-disjoint evaluation split
    # ------------------------------------------------------

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=EVALUATION_TEST_SIZE,
        random_state=RANDOM_STATE
    )

    _, evaluation_idx = next(
        splitter.split(
            X,
            y,
            groups=data["encounter_id"]
        )
    )

    X_evaluation = X.iloc[
        evaluation_idx
    ]

    y_evaluation = y.iloc[
        evaluation_idx
    ]

    evaluation_data = data.iloc[
        evaluation_idx
    ].copy()

    evaluation_encounters = set(
        evaluation_data[
            "encounter_id"
        ]
    )

    if not evaluation_encounters:

        raise ValueError(
            "No evaluation encounters available."
        )

    print(
        f"\nEvaluation records: "
        f"{len(X_evaluation)}"
    )

    print(
        f"Evaluation encounters: "
        f"{len(evaluation_encounters)}"
    )

    # ------------------------------------------------------
    # Convert once to NumPy
    #
    # Individual Random Forest trees were fitted without
    # feature names, so NumPy avoids the sklearn warning.
    # ------------------------------------------------------

    X_array = X_evaluation.to_numpy(
        dtype=float
    )

    # ------------------------------------------------------
    # E6 full-model probabilities
    # ------------------------------------------------------

    print(
        "\nGenerating E6 evaluation probabilities..."
    )

    raw_probabilities = (
        model.predict_proba(
            X_evaluation
        )[:, 1]
    )

    # ------------------------------------------------------
    # E7 calibrated probabilities
    # ------------------------------------------------------

    clipped = np.clip(
        raw_probabilities,
        1e-6,
        1 - 1e-6
    )

    logits = np.log(
        clipped
        /
        (1 - clipped)
    )

    calibrated_probabilities = (
        calibrator.predict_proba(
            logits.reshape(-1, 1)
        )[:, 1]
    )

    # ------------------------------------------------------
    # E8 TREE-LEVEL PROBABILITIES
    #
    # Shape:
    #
    #     rows × trees
    #
    # Example:
    #
    #     36,602 × 200
    #
    # Each tree is evaluated ONCE over the entire
    # evaluation dataset.
    # ------------------------------------------------------

    print(
        "\nGenerating Random Forest tree-level probabilities..."
    )

    tree_probability_matrix = []

    for tree_index, tree in enumerate(
        model.estimators_,
        start=1
    ):

        tree_probabilities = (
            tree.predict_proba(
                X_array
            )[:, 1]
        )

        tree_probability_matrix.append(
            tree_probabilities
        )

        if (
            tree_index == 1
            or tree_index % 50 == 0
            or tree_index
            == len(model.estimators_)
        ):

            print(
                f"  Processed trees: "
                f"{tree_index}/"
                f"{len(model.estimators_)}"
            )

    tree_probability_matrix = np.column_stack(
        tree_probability_matrix
    )

    # ------------------------------------------------------
    # Apply E7 calibration to every tree probability
    # ------------------------------------------------------

    print(
        "\nApplying E7 calibration to tree probabilities..."
    )

    clipped_tree = np.clip(
        tree_probability_matrix,
        1e-6,
        1 - 1e-6
    )

    tree_logits = np.log(
        clipped_tree
        /
        (1 - clipped_tree)
    )

    # Flatten so calibrator receives one probability
    # per tree prediction.

    flattened_logits = (
        tree_logits.reshape(-1, 1)
    )

    calibrated_tree_flat = (
        calibrator.predict_proba(
            flattened_logits
        )[:, 1]
    )

    calibrated_tree_matrix = (
        calibrated_tree_flat.reshape(
            tree_probability_matrix.shape
        )
    )

    # ------------------------------------------------------
    # E8 uncertainty statistics
    # ------------------------------------------------------

    lower_bounds = np.quantile(
        calibrated_tree_matrix,
        LOWER_QUANTILE,
        axis=1
    )

    upper_bounds = np.quantile(
        calibrated_tree_matrix,
        UPPER_QUANTILE,
        axis=1
    )

    std_values = np.std(
        calibrated_tree_matrix,
        axis=1,
        ddof=1
    )

    widths = (
        upper_bounds
        - lower_bounds
    )

    # ------------------------------------------------------
    # Actual outcomes
    # ------------------------------------------------------

    y_values = np.asarray(
        y_evaluation,
        dtype=int
    )

    calibrated_probabilities = (
        np.asarray(
            calibrated_probabilities,
            dtype=float
        )
    )

    # ------------------------------------------------------
    # Metrics
    # ------------------------------------------------------

    brier = brier_score_loss(
        y_values,
        calibrated_probabilities
    )

    auc = roc_auc_score(
        y_values,
        calibrated_probabilities
    )

    # ------------------------------------------------------
    # Descriptive interval coverage
    #
    # This is NOT formal confidence-interval coverage.
    # ------------------------------------------------------

    coverage = np.mean(
        (
            y_values
            >= lower_bounds
        )
        &
        (
            y_values
            <= upper_bounds
        )
    )

    average_width = np.mean(
        widths
    )

    average_std = np.mean(
        std_values
    )

    # ------------------------------------------------------
    # Uncertainty distribution
    # ------------------------------------------------------

    uncertainty_levels = [

        classify_uncertainty(
            width
        )

        for width in widths
    ]

    level_counts = (
        pd.Series(
            uncertainty_levels
        )
        .value_counts()
        .to_dict()
    )

    # ------------------------------------------------------
    # Basic sanity checks
    # ------------------------------------------------------

    if not np.all(
        (lower_bounds >= 0)
        &
        (lower_bounds <= 1)
    ):

        raise ValueError(
            "E8 lower bounds outside [0,1]."
        )

    if not np.all(
        (upper_bounds >= 0)
        &
        (upper_bounds <= 1)
    ):

        raise ValueError(
            "E8 upper bounds outside [0,1]."
        )

    if not np.all(
        lower_bounds <= upper_bounds
    ):

        raise ValueError(
            "E8 lower bounds exceed upper bounds."
        )

    return {

        "evaluation_records": int(
            len(y_values)
        ),

        "evaluation_encounters": int(
            len(evaluation_encounters)
        ),

        "brier_score": float(
            brier
        ),

        "roc_auc": float(
            auc
        ),

        "interval_coverage": float(
            coverage
        ),

        "average_interval_width": float(
            average_width
        ),

        "average_tree_probability_std": float(
            average_std
        ),

        "uncertainty_level_counts": (
            level_counts
        ),

        "tree_count": int(
            len(model.estimators_)
        )
    }


# ==========================================================
# SAVE E8 ARTIFACT
# ==========================================================

def save_uncertainty_artifact(
    metadata
):
    """
    Save E8 configuration and metadata.

    The Random Forest and E7 calibrator remain in their
    original artifacts. E8 stores only its uncertainty
    configuration and evaluation metadata.
    """

    artifact = {

        "method": (
            "Random Forest tree-level "
            "predictive spread after E7 calibration"
        ),

        "lower_quantile": (
            LOWER_QUANTILE
        ),

        "upper_quantile": (
            UPPER_QUANTILE
        ),

        "low_uncertainty_width": (
            LOW_UNCERTAINTY_WIDTH
        ),

        "moderate_uncertainty_width": (
            MODERATE_UNCERTAINTY_WIDTH
        ),

        "metadata": metadata
    }

    joblib.dump(
        artifact,
        E8_UNCERTAINTY_PATH
    )

    print(
        f"\nE8 artifact saved as: "
        f"{E8_UNCERTAINTY_PATH}"
    )


# ==========================================================
# LOAD E8 ARTIFACT
# ==========================================================

def load_uncertainty_artifact():

    if not os.path.exists(
        E8_UNCERTAINTY_PATH
    ):

        raise FileNotFoundError(
            "E8 uncertainty artifact not found:\n"
            f"{E8_UNCERTAINTY_PATH}\n\n"
            "Run E8 first."
        )

    artifact = joblib.load(
        E8_UNCERTAINTY_PATH
    )

    if not isinstance(
        artifact,
        dict
    ):

        raise ValueError(
            "Invalid E8 uncertainty artifact."
        )

    required_keys = [
        "method",
        "lower_quantile",
        "upper_quantile",
        "low_uncertainty_width",
        "moderate_uncertainty_width",
        "metadata"
    ]

    for key in required_keys:

        if key not in artifact:

            raise ValueError(
                f"E8 artifact missing '{key}'."
            )

    return artifact


# ==========================================================
# VALIDATE E8 ARTIFACT
# ==========================================================

def validate_uncertainty_artifact():

    artifact = (
        load_uncertainty_artifact()
    )

    lower = artifact[
        "lower_quantile"
    ]

    upper = artifact[
        "upper_quantile"
    ]

    if not (
        0.0
        <= lower
        < upper
        <= 1.0
    ):

        raise ValueError(
            "Invalid E8 quantile configuration."
        )

    if (
        artifact[
            "low_uncertainty_width"
        ]
        <= 0
    ):

        raise ValueError(
            "Invalid low uncertainty threshold."
        )

    if (
        artifact[
            "moderate_uncertainty_width"
        ]
        <= artifact[
            "low_uncertainty_width"
        ]
    ):

        raise ValueError(
            "Invalid uncertainty threshold ordering."
        )

    return True


# ==========================================================
# E8 PIPELINE TEST
# ==========================================================

def run_e8_pipeline_test():

    """
    Validate complete:

        E1 -> E2 -> E3 -> E4 -> E6 -> E7 -> E8
    """

    from ML.treatment_advisor.candidate_treatments import (
        generate_candidates_for_encounter
    )

    from ML.treatment_advisor.clinical_eligibility import (
        evaluate_candidates,
        load_treatment_master
    )

    from ML.treatment_advisor.e4_configuration import (
        enrich_candidates
    )

    from ML.treatment_advisor.treatment_model import (
        find_valid_test_encounter
    )

    # ------------------------------------------------------
    # Find valid encounter
    # ------------------------------------------------------

    encounter_id, _ = (
        find_valid_test_encounter()
    )

    print(
        f"\nTesting encounter: "
        f"{encounter_id}"
    )

    # ------------------------------------------------------
    # E1 -> E2
    # ------------------------------------------------------

    (
        context,
        candidates,
        candidate_records
    ) = generate_candidates_for_encounter(
        encounter_id
    )

    if candidates.empty:

        raise ValueError(
            "E2 returned no candidates."
        )

    print(
        f"Disease: "
        f"{context['disease_id']}"
    )

    print(
        f"Severity: "
        f"{context['severity_id']}"
    )

    print(
        f"E2 candidates: "
        f"{len(candidates)}"
    )

    # ------------------------------------------------------
    # Hospital
    # ------------------------------------------------------

    engine = get_engine()

    hospital_query = text("""
        SELECT hospital_id
        FROM patient_encounter
        WHERE encounter_id = :encounter_id
    """)

    with engine.connect() as connection:

        hospital_result = pd.read_sql(
            hospital_query,
            connection,
            params={
                "encounter_id": encounter_id
            }
        )

    if hospital_result.empty:

        raise ValueError(
            "Hospital not found."
        )

    hospital_id = str(
        hospital_result.iloc[0][
            "hospital_id"
        ]
    )

    print(
        f"Hospital: {hospital_id}"
    )

    # ------------------------------------------------------
    # E3
    # ------------------------------------------------------

    treatment_master = (
        load_treatment_master()
    )

    eligible_candidates = (
        evaluate_candidates(
            candidates,
            treatment_master
        )
    )

    if eligible_candidates.empty:

        raise ValueError(
            "E3 returned no candidates."
        )

    print(
        f"E3 evaluated candidates: "
        f"{len(eligible_candidates)}"
    )

    # ------------------------------------------------------
    # E4
    # ------------------------------------------------------

    enriched_candidates = (
        enrich_candidates(
            eligible_candidates,
            hospital_id
        )
    )

    if enriched_candidates.empty:

        raise ValueError(
            "E4 returned no candidates."
        )

    print(
        f"E4 enriched candidates: "
        f"{len(enriched_candidates)}"
    )

    # ------------------------------------------------------
    # E6 -> E7 -> E8
    # ------------------------------------------------------

    print(
        "\nE6 -> E7 -> E8 "
        "TREATMENT PREDICTIONS"
    )

    print(
        "-" * 70
    )

    results = []

    for _, candidate in (
        enriched_candidates.iterrows()
    ):

        treatment_id = candidate[
            "treatment_id"
        ]

        treatment_name = candidate[
            "treatment_name"
        ]

        prediction = (
            predict_treatment_with_uncertainty(
                context,
                treatment_id
            )
        )

        result = {

            "treatment_id": (
                treatment_id
            ),

            "treatment_name": (
                treatment_name
            ),

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

            "uncertainty_lower": (
                prediction[
                    "uncertainty_lower"
                ]
            ),

            "uncertainty_upper": (
                prediction[
                    "uncertainty_upper"
                ]
            ),

            "uncertainty_std": (
                prediction[
                    "uncertainty_std"
                ]
            ),

            "uncertainty_interval_width": (
                prediction[
                    "uncertainty_interval_width"
                ]
            ),

            "uncertainty_level": (
                prediction[
                    "uncertainty_level"
                ]
            ),

            "tree_count": (
                prediction[
                    "tree_count"
                ]
            )
        }

        results.append(
            result
        )

        print(
            f"\nTreatment: "
            f"{treatment_name}"
        )

        print(
            f"Treatment ID: "
            f"{treatment_id}"
        )

        print(
            f"E6 raw probability: "
            f"{prediction['raw_success_probability']:.4f}"
        )

        print(
            f"E7 calibrated probability: "
            f"{prediction['calibrated_success_probability']:.4f}"
        )

        print(
            f"E8 uncertainty lower: "
            f"{prediction['uncertainty_lower']:.4f}"
        )

        print(
            f"E8 uncertainty upper: "
            f"{prediction['uncertainty_upper']:.4f}"
        )

        print(
            f"E8 uncertainty std: "
            f"{prediction['uncertainty_std']:.4f}"
        )

        print(
            f"E8 uncertainty level: "
            f"{prediction['uncertainty_level']}"
        )

    # ------------------------------------------------------
    # Validate outputs
    # ------------------------------------------------------

    if not results:

        raise ValueError(
            "E8 generated no treatment predictions."
        )

    for result in results:

        probability = result[
            "calibrated_success_probability"
        ]

        lower = result[
            "uncertainty_lower"
        ]

        upper = result[
            "uncertainty_upper"
        ]

        width = result[
            "uncertainty_interval_width"
        ]

        # Probability range

        if not (
            0.0
            <= probability
            <= 1.0
        ):

            raise ValueError(
                "Calibrated probability is outside [0,1]."
            )

        # Interval range

        if not (
            0.0
            <= lower
            <= upper
            <= 1.0
        ):

            raise ValueError(
                "Uncertainty interval is outside [0,1]."
            )

        # Width consistency

        calculated_width = (
            upper - lower
        )

        if abs(
            calculated_width - width
        ) > 1e-6:

            raise ValueError(
                "Uncertainty interval width is inconsistent."
            )

        # Uncertainty level

        expected_level = (
            classify_uncertainty(
                width
            )
        )

        if (
            result[
                "uncertainty_level"
            ]
            != expected_level
        ):

            raise ValueError(
                "Uncertainty level does not match "
                "configured thresholds."
            )

    return results


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    print("=" * 70)
    print(
        "E8 - UNCERTAINTY ESTIMATION"
    )
    print("=" * 70)

    # ------------------------------------------------------
    # Step 1: Validate E6
    # ------------------------------------------------------

    print(
        "\nLoading E6 model..."
    )

    model, feature_names = (
        load_e6_model()
    )

    print(
        f"E6 model: VALID"
    )

    print(
        f"Random Forest trees: "
        f"{len(model.estimators_)}"
    )

    print(
        f"E6 features: "
        f"{len(feature_names)}"
    )

    # ------------------------------------------------------
    # Step 2: Validate E7
    # ------------------------------------------------------

    print(
        "\nLoading E7 calibration artifact..."
    )

    calibrator, e7_artifact = (
        load_e7_calibrator()
    )

    print(
        "E7 calibration artifact: VALID"
    )

    print(
        f"E7 method: "
        f"{e7_artifact.get('method')}"
    )

    # ------------------------------------------------------
    # Step 3: Evaluate E8 behavior
    # ------------------------------------------------------

    print(
        "\nEvaluating E8 uncertainty behavior..."
    )

    evaluation = (
        evaluate_uncertainty_on_dataset()
    )

    print(
        "\nE8 UNCERTAINTY EVALUATION"
    )

    print(
        "-" * 70
    )

    print(
        f"Evaluation records: "
        f"{evaluation['evaluation_records']}"
    )

    print(
        f"Evaluation encounters: "
        f"{evaluation['evaluation_encounters']}"
    )

    print(
        f"Calibrated Brier score: "
        f"{evaluation['brier_score']:.6f}"
    )

    print(
        f"Calibrated ROC-AUC: "
        f"{evaluation['roc_auc']:.6f}"
    )

    print(
        f"Interval coverage: "
        f"{evaluation['interval_coverage']:.6f}"
    )

    print(
        f"Average interval width: "
        f"{evaluation['average_interval_width']:.6f}"
    )

    print(
        f"Average tree probability std: "
        f"{evaluation['average_tree_probability_std']:.6f}"
    )

    print(
        "\nUncertainty level distribution:"
    )

    for level, count in (
        evaluation[
            "uncertainty_level_counts"
        ].items()
    ):

        print(
            f"  {level}: {count}"
        )

    # ------------------------------------------------------
    # Step 4: Save E8 configuration
    # ------------------------------------------------------

    metadata = {

        "evaluation_records": (
            evaluation[
                "evaluation_records"
            ]
        ),

        "evaluation_encounters": (
            evaluation[
                "evaluation_encounters"
            ]
        ),

        "calibrated_brier_score": (
            evaluation[
                "brier_score"
            ]
        ),

        "calibrated_roc_auc": (
            evaluation[
                "roc_auc"
            ]
        ),

        "interval_coverage": (
            evaluation[
                "interval_coverage"
            ]
        ),

        "average_interval_width": (
            evaluation[
                "average_interval_width"
            ]
        ),

        "average_tree_probability_std": (
            evaluation[
                "average_tree_probability_std"
            ]
        ),

        "uncertainty_level_counts": (
            evaluation[
                "uncertainty_level_counts"
            ]
        ),

        "e6_model_path": (
            E6_MODEL_PATH
        ),

        "e7_calibration_path": (
            E7_CALIBRATION_PATH
        ),

        "interpretation": (
            "E8 uncertainty is based on Random Forest "
            "tree-level predictive spread after E7 "
            "probability calibration. It is not a formal "
            "statistical confidence interval."
        )
    }

    save_uncertainty_artifact(
        metadata
    )

    # ------------------------------------------------------
    # Step 5: Validate E8 artifact
    # ------------------------------------------------------

    print(
        "\nValidating saved E8 artifact..."
    )

    validate_uncertainty_artifact()

    print(
        "E8 uncertainty artifact: VALID"
    )

    # ------------------------------------------------------
    # Step 6: Complete pipeline test
    # ------------------------------------------------------

    results = (
        run_e8_pipeline_test()
    )

    # ------------------------------------------------------
    # Final validation
    # ------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "E8 VALIDATION: PASSED"
    )

    print(
        "=" * 70
    )
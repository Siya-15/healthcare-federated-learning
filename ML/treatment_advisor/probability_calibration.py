"""
E7 - Probability Calibration

Calibrates the raw treatment-success probabilities produced by E6.

Important:
- E6 remains unchanged.
- E7 calibrates probabilities only.
- The calibration split is encounter-disjoint from the E6 training data.
- The calibrated probability is NOT a causal treatment-effect estimate.
- The output is NOT an autonomous prescribing decision.
- E8 will handle uncertainty.
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

from sklearn.ensemble import RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from database import get_engine
from ML.treatment_advisor.clinical_eligibility import (
    evaluate_candidates,
    load_treatment_master
)


# ==========================================================
# ARTIFACT PATHS
# ==========================================================

E6_MODEL_FILENAME = "treatment_success_model.pkl"

E6_MODEL_PATH = os.path.join(
    PROJECT_ROOT,
    E6_MODEL_FILENAME
)

CALIBRATION_FILENAME = (
    "treatment_probability_calibrator.pkl"
)

CALIBRATION_PATH = os.path.join(
    PROJECT_ROOT,
    CALIBRATION_FILENAME
)


# ==========================================================
# CONFIGURATION
# ==========================================================

RANDOM_STATE = 42

# Fraction of the complete dataset reserved for E7.
CALIBRATION_TEST_SIZE = 0.20

# E7 uses sigmoid / Platt calibration.
CALIBRATION_METHOD = "sigmoid"


# ==========================================================
# LOAD E6 MODEL
# ==========================================================

def load_e6_model():
    """
    Load the existing E6 Random Forest artifact.

    E6 artifact format:
        {
            "model": model,
            "feature_names": feature_names
        }
    """

    if not os.path.exists(E6_MODEL_PATH):

        raise FileNotFoundError(
            "E6 model artifact not found:\n"
            f"{E6_MODEL_PATH}\n\n"
            "Run E6 training first."
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

    model = artifact["model"]

    feature_names = artifact[
        "feature_names"
    ]

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
# DATABASE LOADING
# ==========================================================

def load_calibration_data():
    """
    Load the same clinical/treatment feature information
    used by E6.

    E7 does not use treatment outcome fields as predictors.
    The outcome is used only as the calibration target.
    """

    engine = get_engine()

    encounter_query = """
    SELECT
        encounter_id,
        age,
        gender,
        temperature,
        heart_rate,
        respiratory_rate,
        systolic_bp,
        diastolic_bp,
        spo2,
        disease_id,
        severity_id,
        discharge_status
    FROM patient_encounter
    """

    treatment_query = """
    SELECT
        encounter_id,
        treatment_id
    FROM encounter_treatments
    WHERE administered = TRUE
    """

    symptom_query = """
    SELECT
        encounter_id,
        symptom_id
    FROM encounter_symptoms
    """

    symptom_master_query = """
    SELECT
        symptom_id,
        symptom_name
    FROM symptom_master
    """

    with engine.connect() as connection:

        encounters = pd.read_sql(
            text(encounter_query),
            connection
        )

        treatments = pd.read_sql(
            text(treatment_query),
            connection
        )

        symptoms = pd.read_sql(
            text(symptom_query),
            connection
        )

        symptom_master = pd.read_sql(
            text(symptom_master_query),
            connection
        )

    return (
        encounters,
        treatments,
        symptoms,
        symptom_master
    )


# ==========================================================
# SYMPTOM FEATURES
# ==========================================================

def create_symptom_features(
    symptoms,
    symptom_master
):
    """
    Convert encounter-level symptoms into one-hot features.
    """

    symptoms = symptoms.merge(
        symptom_master,
        on="symptom_id",
        how="left"
    )

    symptom_table = (
        symptoms
        .assign(value=1)
        .pivot_table(
            index="encounter_id",
            columns="symptom_name",
            values="value",
            fill_value=0
        )
        .reset_index()
    )

    return symptom_table


# ==========================================================
# PREPARE E7 DATASET
# ==========================================================

def prepare_calibration_dataset():
    """
    Reconstruct the E6 feature representation so that the
    existing E6 model can generate raw probabilities.

    Target:
        treatment_success

    Predictor data:
        age
        vitals
        gender
        disease
        severity
        treatment
        symptoms
    """

    (
        encounters,
        treatments,
        symptoms,
        symptom_master
    ) = load_calibration_data()

    symptom_features = create_symptom_features(
        symptoms,
        symptom_master
    )

    data = encounters.merge(
        symptom_features,
        on="encounter_id",
        how="left"
    )

    data = data.merge(
        treatments,
        on="encounter_id",
        how="inner"
    )

    # ------------------------------------------------------
    # TARGET
    # ------------------------------------------------------

    data["treatment_success"] = (
        data["discharge_status"]
        == "Recovered"
    ).astype(int)

    # ------------------------------------------------------
    # SYMPTOM COLUMNS
    # ------------------------------------------------------

    symptom_names = (
        symptom_master["symptom_name"]
        .dropna()
        .unique()
        .tolist()
    )

    for symptom in symptom_names:

        if symptom not in data.columns:

            data[symptom] = 0

    data[symptom_names] = (
        data[symptom_names]
        .fillna(0)
        .astype(int)
    )

    # ------------------------------------------------------
    # FEATURES
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

    categorical_features = [
        "gender",
        "disease_id",
        "severity_id",
        "treatment_id",
    ]

    feature_data = data[
        numerical_features
        + categorical_features
        + symptom_names
    ].copy()

    feature_data = pd.get_dummies(
        feature_data,
        columns=categorical_features,
        dtype=int
    )

    feature_data = feature_data.fillna(0)

    return (
        data,
        feature_data,
        data["treatment_success"],
        symptom_names
    )


# ==========================================================
# ALIGN FEATURES WITH E6
# ==========================================================

def align_with_e6_features(
    feature_data,
    e6_feature_names
):
    """
    Force the calibration data into exactly the feature
    schema expected by E6.
    """

    aligned = feature_data.reindex(
        columns=e6_feature_names,
        fill_value=0
    )

    aligned = aligned.apply(
        pd.to_numeric,
        errors="coerce"
    ).fillna(0)

    return aligned


# ==========================================================
# CREATE ENCOUNTER-DISJOINT SPLIT
# ==========================================================

def create_calibration_split(
    data,
    X,
    y
):
    """
    Split data into:

        E7 calibration set
        E7 evaluation set

    using encounter_id as the grouping variable.

    Therefore, the same encounter cannot occur in both sets.
    """

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=CALIBRATION_TEST_SIZE,
        random_state=RANDOM_STATE
    )

    calibration_idx, evaluation_idx = next(
        splitter.split(
            X,
            y,
            groups=data["encounter_id"]
        )
    )

    X_calibration = X.iloc[
        calibration_idx
    ]

    X_evaluation = X.iloc[
        evaluation_idx
    ]

    y_calibration = y.iloc[
        calibration_idx
    ]

    y_evaluation = y.iloc[
        evaluation_idx
    ]

    calibration_encounters = set(
        data.iloc[
            calibration_idx
        ]["encounter_id"]
    )

    evaluation_encounters = set(
        data.iloc[
            evaluation_idx
        ]["encounter_id"]
    )

    overlap = (
        calibration_encounters
        .intersection(
            evaluation_encounters
        )
    )

    print(
        f"\nCalibration encounters: "
        f"{len(calibration_encounters)}"
    )

    print(
        f"Evaluation encounters: "
        f"{len(evaluation_encounters)}"
    )

    print(
        f"Calibration/evaluation overlap: "
        f"{len(overlap)}"
    )

    if overlap:

        raise ValueError(
            "Data leakage detected: "
            "encounters occur in both "
            "calibration and evaluation sets."
        )

    return (
        X_calibration,
        X_evaluation,
        y_calibration,
        y_evaluation,
        calibration_encounters,
        evaluation_encounters
    )


# ==========================================================
# GENERATE E6 RAW PROBABILITIES
# ==========================================================

def generate_raw_probabilities(
    model,
    X
):
    """
    Generate raw E6 Random Forest probabilities.
    """

    probabilities = model.predict_proba(
        X
    )[:, 1]

    return np.asarray(
        probabilities,
        dtype=float
    )


# ==========================================================
# FIT SIGMOID CALIBRATOR
# ==========================================================

def fit_sigmoid_calibrator(
    raw_probabilities,
    y_true
):
    """
    Fit Platt-style sigmoid calibration.

    Logistic regression maps the E6 raw probability to
    a calibrated probability.
    """

    raw_probabilities = np.asarray(
        raw_probabilities,
        dtype=float
    )

    y_true = np.asarray(
        y_true,
        dtype=int
    )

    # Avoid logit infinity at exactly 0 or 1.
    clipped = np.clip(
        raw_probabilities,
        1e-6,
        1 - 1e-6
    )

    logit = np.log(
        clipped / (1 - clipped)
    )

    calibrator = LogisticRegression(
        random_state=RANDOM_STATE,
        solver="lbfgs"
    )

    calibrator.fit(
        logit.reshape(-1, 1),
        y_true
    )

    return calibrator


# ==========================================================
# APPLY SIGMOID CALIBRATOR
# ==========================================================

def apply_sigmoid_calibrator(
    calibrator,
    raw_probabilities
):
    """
    Convert raw E6 probabilities into calibrated
    probabilities.
    """

    raw_probabilities = np.asarray(
        raw_probabilities,
        dtype=float
    )

    clipped = np.clip(
        raw_probabilities,
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
# CALIBRATION METRICS
# ==========================================================

def calculate_metrics(
    y_true,
    probabilities
):
    """
    Calculate probability-quality metrics.
    """

    y_true = np.asarray(
        y_true,
        dtype=int
    )

    probabilities = np.asarray(
        probabilities,
        dtype=float
    )

    brier = brier_score_loss(
        y_true,
        probabilities
    )

    unique_classes = np.unique(
        y_true
    )

    if len(unique_classes) == 2:

        auc = roc_auc_score(
            y_true,
            probabilities
        )

    else:

        auc = float("nan")

    return {
        "brier_score": float(brier),
        "roc_auc": float(auc)
    }


# ==========================================================
# CALIBRATION BIN ANALYSIS
# ==========================================================

def calibration_table(
    y_true,
    probabilities,
    n_bins=10
):
    """
    Produce a simple reliability table.

    Each row represents a probability bin.

    mean_predicted:
        mean predicted probability

    observed_success_rate:
        actual success frequency
    """

    frame = pd.DataFrame({
        "actual": np.asarray(
            y_true,
            dtype=int
        ),

        "probability": np.asarray(
            probabilities,
            dtype=float
        )
    })

    frame["bin"] = pd.cut(
        frame["probability"],
        bins=np.linspace(
            0,
            1,
            n_bins + 1
        ),
        include_lowest=True
    )

    table = (
        frame
        .groupby(
            "bin",
            observed=False
        )
        .agg(
            samples=("actual", "size"),
            mean_predicted=(
                "probability",
                "mean"
            ),
            observed_success_rate=(
                "actual",
                "mean"
            )
        )
        .reset_index()
    )

    table["absolute_gap"] = (
        table["mean_predicted"]
        - table["observed_success_rate"]
    ).abs()

    return table


# ==========================================================
# SAVE CALIBRATION ARTIFACT
# ==========================================================

def save_calibration_artifact(
    calibrator,
    metadata
):
    """
    Save E7 calibration artifact.
    """

    artifact = {
        "calibrator": calibrator,
        "method": CALIBRATION_METHOD,
        "metadata": metadata
    }

    joblib.dump(
        artifact,
        CALIBRATION_PATH
    )

    print(
        f"\nCalibration artifact saved as: "
        f"{CALIBRATION_PATH}"
    )


# ==========================================================
# LOAD CALIBRATION ARTIFACT
# ==========================================================

def load_calibration_artifact():
    """
    Load and validate the E7 calibration artifact.
    """

    if not os.path.exists(
        CALIBRATION_PATH
    ):

        raise FileNotFoundError(
            "E7 calibration artifact not found:\n"
            f"{CALIBRATION_PATH}\n\n"
            "Run E7 calibration first."
        )

    artifact = joblib.load(
        CALIBRATION_PATH
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

    if "method" not in artifact:

        raise ValueError(
            "E7 artifact missing calibration method."
        )

    return artifact


# ==========================================================
# CALIBRATE SINGLE PROBABILITY
# ==========================================================

def calibrate_treatment_probability(
    raw_probability
):
    """
    Convert one E6 raw probability into an E7 calibrated
    probability.
    """

    artifact = load_calibration_artifact()

    calibrator = artifact[
        "calibrator"
    ]

    calibrated = apply_sigmoid_calibrator(
        calibrator,
        np.asarray([
            raw_probability
        ])
    )[0]

    return {
        "raw_success_probability": round(
            float(raw_probability),
            6
        ),

        "calibrated_success_probability": round(
            float(calibrated),
            6
        ),

        "calibrated_success_percentage": round(
            float(calibrated) * 100,
            2
        ),

        "calibration_method": artifact[
            "method"
        ],

        "probability_status": (
            "CALIBRATED"
        ),

        "interpretation": (
            "Probability calibrated from the E6 "
            "historical treatment-success model. "
            "This remains an observational outcome "
            "association and is not a causal estimate "
            "or autonomous prescribing decision."
        )
    }


# ==========================================================
# TRAIN E7 CALIBRATION
# ==========================================================

def train_calibration():
    """
    Complete E7 calibration training.

    Uses:
        E6 model
        encounter-disjoint E7 calibration/evaluation split
    """

    print("=" * 70)
    print(
        "OBJECTIVE E - E7 PROBABILITY CALIBRATION"
    )
    print("=" * 70)

    # ------------------------------------------------------
    # Load E6
    # ------------------------------------------------------

    model, e6_feature_names = load_e6_model()

    print(
        f"\nE6 model loaded: {E6_MODEL_PATH}"
    )

    print(
        f"E6 features: {len(e6_feature_names)}"
    )

    # ------------------------------------------------------
    # Prepare data
    # ------------------------------------------------------

    (
        data,
        feature_data,
        y,
        symptom_names
    ) = prepare_calibration_dataset()

    X = align_with_e6_features(
        feature_data,
        e6_feature_names
    )

    print(
        f"\nE7 records available: {len(data)}"
    )

    print(
        f"E7 feature matrix: {X.shape}"
    )

    # ------------------------------------------------------
    # Outcome distribution
    # ------------------------------------------------------

    print(
        "\nOutcome distribution:"
    )

    print(
        y.value_counts()
        .rename({
            0: "Not Success",
            1: "Success"
        })
        .to_string()
    )

    # ------------------------------------------------------
    # Encounter-disjoint split
    # ------------------------------------------------------

    (
        X_calibration,
        X_evaluation,
        y_calibration,
        y_evaluation,
        calibration_encounters,
        evaluation_encounters
    ) = create_calibration_split(
        data,
        X,
        y
    )

    # ------------------------------------------------------
    # E6 raw probabilities
    # ------------------------------------------------------

    print(
        "\nGenerating E6 raw probabilities..."
    )

    calibration_raw = generate_raw_probabilities(
        model,
        X_calibration
    )

    evaluation_raw = generate_raw_probabilities(
        model,
        X_evaluation
    )

    print(
        "Raw probabilities generated successfully."
    )

    # ------------------------------------------------------
    # Fit calibrator
    # ------------------------------------------------------

    print(
        "\nFitting sigmoid calibration..."
    )

    calibrator = fit_sigmoid_calibrator(
        calibration_raw,
        y_calibration
    )

    print(
        "Calibrator trained successfully."
    )

    # ------------------------------------------------------
    # Apply calibrator
    # ------------------------------------------------------

    evaluation_calibrated = (
        apply_sigmoid_calibrator(
            calibrator,
            evaluation_raw
        )
    )

    # ------------------------------------------------------
    # Metrics
    # ------------------------------------------------------

    raw_metrics = calculate_metrics(
        y_evaluation,
        evaluation_raw
    )

    calibrated_metrics = calculate_metrics(
        y_evaluation,
        evaluation_calibrated
    )

    print(
        "\nE7 CALIBRATION EVALUATION"
    )

    print(
        "-" * 70
    )

    print(
        f"Raw Brier score: "
        f"{raw_metrics['brier_score']:.6f}"
    )

    print(
        f"Calibrated Brier score: "
        f"{calibrated_metrics['brier_score']:.6f}"
    )

    print(
        f"Raw ROC-AUC: "
        f"{raw_metrics['roc_auc']:.6f}"
    )

    print(
        f"Calibrated ROC-AUC: "
        f"{calibrated_metrics['roc_auc']:.6f}"
    )

    brier_change = (
        calibrated_metrics["brier_score"]
        - raw_metrics["brier_score"]
    )

    print(
        f"Brier score change: "
        f"{brier_change:+.6f}"
    )

    # ------------------------------------------------------
    # Reliability table
    # ------------------------------------------------------

    print(
        "\nCalibration reliability table:"
    )

    reliability = calibration_table(
        y_evaluation,
        evaluation_calibrated,
        n_bins=10
    )

    print(
        reliability.to_string(
            index=False
        )
    )

    # ------------------------------------------------------
    # Save artifact
    # ------------------------------------------------------

    metadata = {
        "method": CALIBRATION_METHOD,

        "calibration_records": int(
            len(y_calibration)
        ),

        "evaluation_records": int(
            len(y_evaluation)
        ),

        "calibration_encounters": int(
            len(calibration_encounters)
        ),

        "evaluation_encounters": int(
            len(evaluation_encounters)
        ),

        "encounter_overlap": 0,

        "raw_brier_score": (
            raw_metrics["brier_score"]
        ),

        "calibrated_brier_score": (
            calibrated_metrics["brier_score"]
        ),

        "raw_roc_auc": (
            raw_metrics["roc_auc"]
        ),

        "calibrated_roc_auc": (
            calibrated_metrics["roc_auc"]
        ),

        "brier_score_change": (
            brier_change
        ),

        "e6_model_path": E6_MODEL_PATH,

        "e6_feature_count": int(
            len(e6_feature_names)
        )
    }

    save_calibration_artifact(
        calibrator,
        metadata
    )

    return {
        "calibrator": calibrator,
        "metadata": metadata,
        "evaluation_raw": evaluation_raw,
        "evaluation_calibrated": evaluation_calibrated,
        "y_evaluation": y_evaluation
    }


# ==========================================================
# VALIDATE E7 ARTIFACT
# ==========================================================

def validate_calibration_artifact():
    """
    Validate the saved E7 calibration artifact.
    """

    artifact = load_calibration_artifact()

    calibrator = artifact[
        "calibrator"
    ]

    if not hasattr(
        calibrator,
        "predict_proba"
    ):

        raise ValueError(
            "Calibration artifact does not "
            "support predict_proba()."
        )

    metadata = artifact.get(
        "metadata",
        {}
    )

    if metadata.get(
        "encounter_overlap"
    ) != 0:

        raise ValueError(
            "Calibration artifact indicates "
            "encounter overlap."
        )

    return True


# ==========================================================
# E6 -> E7 PIPELINE TEST
# ==========================================================

def run_e7_pipeline_test():
    """
    Validate:

        E1
         ↓
        E2
         ↓
        E3
         ↓
        E4
         ↓
        E6 raw probability
         ↓
        E7 calibrated probability
    """

    from ML.treatment_advisor.candidate_treatments import (
        generate_candidates_for_encounter
    )

    from ML.treatment_advisor.e4_configuration import (
        enrich_candidates
    )

    from ML.treatment_advisor.treatment_model import (
        predict_treatment_success,
        find_valid_test_encounter
    )

    # ------------------------------------------------------
    # Find valid encounter
    # ------------------------------------------------------

    encounter_id, context = (
        find_valid_test_encounter()
    )

    print(
        f"\nTesting encounter: "
        f"{encounter_id}"
    )

    # ------------------------------------------------------
    # E2
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

    # ------------------------------------------------------
    # Retrieve hospital
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
            "Hospital not found for test encounter."
        )

    hospital_id = str(
        hospital_result.iloc[0][
            "hospital_id"
        ]
    )

    print(
        f"Hospital: {hospital_id}"
    )

    print(
        f"Disease: {context['disease_id']}"
    )

    print(
        f"Severity: {context['severity_id']}"
    )

    print(
        f"E2 candidates: {len(candidates)}"
    )

    # ------------------------------------------------------
    # E3
    # ------------------------------------------------------

    treatment_master = load_treatment_master()

    eligible_candidates = evaluate_candidates(
        candidates,
        treatment_master
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

    enriched_candidates = enrich_candidates(
        eligible_candidates,
        hospital_id
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
    # E6 -> E7
    # ------------------------------------------------------

    print(
        "\nE6 -> E7 CALIBRATED PREDICTIONS"
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

        # --------------------------------------------------
        # E6 raw prediction
        # --------------------------------------------------

        e6_prediction = (
            predict_treatment_success(
                context,
                treatment_id
            )
        )

        raw_probability = (
            e6_prediction[
                "raw_success_probability"
            ]
        )

        # --------------------------------------------------
        # E7 calibration
        # --------------------------------------------------

        e7_prediction = (
            calibrate_treatment_probability(
                raw_probability
            )
        )

        result = {
            "treatment_id": treatment_id,

            "treatment_name": treatment_name,

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
        }

        results.append(
            result
        )

        print(
            f"\nTreatment: {treatment_name}"
        )

        print(
            f"Treatment ID: {treatment_id}"
        )

        print(
            f"E6 raw probability: "
            f"{raw_probability:.4f}"
        )

        print(
            f"E7 calibrated probability: "
            f"{e7_prediction['calibrated_success_probability']:.4f}"
        )

    # ------------------------------------------------------
    # Final check
    # ------------------------------------------------------

    if not results:

        raise ValueError(
            "E7 generated no calibrated predictions."
        )

    for result in results:

        probability = result[
            "calibrated_success_probability"
        ]

        if not (
            0.0
            <= probability
            <= 1.0
        ):

            raise ValueError(
                "E7 generated probability outside "
                "the valid [0,1] range."
            )

    return results


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    print("=" * 70)
    print(
        "E7 - PROBABILITY CALIBRATION"
    )
    print("=" * 70)

    # ------------------------------------------------------
    # Step 1: Train calibrator
    # ------------------------------------------------------

    calibration_results = (
        train_calibration()
    )

    # ------------------------------------------------------
    # Step 2: Validate artifact
    # ------------------------------------------------------

    print(
        "\nValidating saved E7 artifact..."
    )

    validate_calibration_artifact()

    print(
        "E7 calibration artifact: VALID"
    )

    # ------------------------------------------------------
    # Step 3: Test E6 -> E7
    # ------------------------------------------------------

    results = (
        run_e7_pipeline_test()
    )

    # ------------------------------------------------------
    # Final validation
    # ------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "E7 VALIDATION: PASSED"
    )

    print(
        "=" * 70
    )
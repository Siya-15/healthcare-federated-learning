"""
E9 - Recovery Time Estimation + Prediction Interval

Purpose
-------
Estimate expected recovery duration for a patient-treatment combination.

E9 is intentionally separated from:
    E6 - Treatment success prediction
    E7 - Probability calibration
    E8 - Treatment probability uncertainty

The model predicts recovery_days using historical encounter data.

Important interpretation
------------------------
This is an observational machine-learning estimate.

It is NOT:
    - a causal treatment effect estimate
    - a guaranteed recovery time
    - a clinical prognosis
    - a prescribing decision

The prediction interval is an empirical model-prediction range derived
from Random Forest tree predictions. It is not a formal statistical
confidence interval.
"""

from pathlib import Path
import pickle
import warnings

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "recovery_time_model.pkl"


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_STATE = 42

N_ESTIMATORS = 200
MAX_DEPTH = 12
MIN_SAMPLES_SPLIT = 5

TEST_SIZE = 0.20

LOWER_QUANTILE = 0.10
UPPER_QUANTILE = 0.90


# ============================================================
# DATABASE IMPORT
# ============================================================

def get_database_engine():
    """
    Import the project's existing database engine.

    Adjust this import only if the project database module has
    a different location/name.
    """
    try:
        from database import get_engine
        return get_engine()
    except ImportError:
        try:
            from database import get_engine
            return get_engine()
        except ImportError:
            raise ImportError(
                "Could not import project database engine. "
                "Use the same database import used by treatment_model.py."
            )


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_dataset():
    """
    Build the E9 regression dataset.

    Each row represents an administered treatment within an encounter.

    Target:
        recovery_days

    Features:
        - age
        - gender
        - temperature
        - heart rate
        - respiratory rate
        - systolic BP
        - diastolic BP
        - SpO2
        - disease
        - severity
        - treatment
        - symptom indicators
    """

    engine = get_database_engine()

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
            recovery_days
        FROM patient_encounter
        WHERE recovery_days IS NOT NULL
          AND recovery_days >= 0
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
            es.encounter_id,
            sm.symptom_name
        FROM encounter_symptoms es
        JOIN symptom_master sm
            ON es.symptom_id = sm.symptom_id
    """

    encounters = pd.read_sql(encounter_query, engine)
    treatments = pd.read_sql(treatment_query, engine)
    symptoms = pd.read_sql(symptom_query, engine)

    if encounters.empty:
        raise ValueError("No encounter records with recovery_days found.")

    if treatments.empty:
        raise ValueError("No administered treatment records found.")

    # --------------------------------------------------------
    # One row per administered treatment
    # --------------------------------------------------------

    df = encounters.merge(
        treatments,
        on="encounter_id",
        how="inner"
    )

    if df.empty:
        raise ValueError(
            "No overlap between encounters and administered treatments."
        )

    # --------------------------------------------------------
    # Symptom one-hot encoding
    # --------------------------------------------------------

    if not symptoms.empty:

        symptom_counts = (
            symptoms
            .drop_duplicates(["encounter_id", "symptom_name"])
            .assign(value=1)
            .pivot_table(
                index="encounter_id",
                columns="symptom_name",
                values="value",
                fill_value=0
            )
            .reset_index()
        )

        symptom_counts.columns.name = None

        df = df.merge(
            symptom_counts,
            on="encounter_id",
            how="left"
        )

    # --------------------------------------------------------
    # Identify symptom columns
    # --------------------------------------------------------

    base_columns = {
        "encounter_id",
        "age",
        "gender",
        "temperature",
        "heart_rate",
        "respiratory_rate",
        "systolic_bp",
        "diastolic_bp",
        "spo2",
        "disease_id",
        "severity_id",
        "treatment_id",
        "recovery_days"
    }

    symptom_columns = [
        c for c in df.columns
        if c not in base_columns
    ]

    # --------------------------------------------------------
    # Numerical columns
    # --------------------------------------------------------

    numerical_columns = [
        "age",
        "temperature",
        "heart_rate",
        "respiratory_rate",
        "systolic_bp",
        "diastolic_bp",
        "spo2"
    ]

    for column in numerical_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # --------------------------------------------------------
    # Categorical columns
    # --------------------------------------------------------

    categorical_columns = [
        "gender",
        "disease_id",
        "severity_id",
        "treatment_id"
    ]

    for column in categorical_columns:
        if column in df.columns:
            df[column] = df[column].fillna("UNKNOWN").astype(str)

    # --------------------------------------------------------
    # Numeric missing values
    # --------------------------------------------------------

    for column in numerical_columns:
        if column in df.columns:
            df[column] = df[column].fillna(
                df[column].median()
            )

    # --------------------------------------------------------
    # Symptom missing values
    # --------------------------------------------------------

    for column in symptom_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # Build feature matrix
    # --------------------------------------------------------

    feature_columns = (
        numerical_columns
        + categorical_columns
        + symptom_columns
    )

    feature_columns = [
        c for c in feature_columns
        if c in df.columns
    ]

    X = df[feature_columns].copy()

    X = pd.get_dummies(
        X,
        columns=[
            c for c in categorical_columns
            if c in X.columns
        ],
        dtype=float
    )

    X = X.fillna(0)

    y = pd.to_numeric(
        df["recovery_days"],
        errors="coerce"
    )

    valid_rows = y.notna()

    X = X.loc[valid_rows].reset_index(drop=True)
    y = y.loc[valid_rows].reset_index(drop=True)

    groups = (
        df.loc[valid_rows, "encounter_id"]
        .reset_index(drop=True)
    )

    metadata = df.loc[
        valid_rows,
        [
            "encounter_id",
            "treatment_id",
            "disease_id",
            "severity_id"
        ]
    ].reset_index(drop=True)

    return X, y, groups, metadata


# ============================================================
# TRAINING
# ============================================================

def train_recovery_model():
    """
    Train the E9 Random Forest regression model.
    """

    print("=" * 70)
    print("E9 - RECOVERY TIME MODEL TRAINING")
    print("=" * 70)

    X, y, groups, metadata = prepare_dataset()

    print(f"Training records : {len(X):,}")
    print(f"Features         : {X.shape[1]}")
    print(f"Unique encounters: {groups.nunique():,}")

    print()
    print("Recovery statistics:")
    print(f"Mean   : {y.mean():.2f} days")
    print(f"Median : {y.median():.2f} days")
    print(f"Minimum: {y.min():.2f} days")
    print(f"Maximum: {y.max():.2f} days")

    # --------------------------------------------------------
    # Encounter-disjoint split
    # --------------------------------------------------------

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE
    )

    train_idx, test_idx = next(
        splitter.split(
            X,
            y,
            groups=groups
        )
    )

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    train_groups = groups.iloc[train_idx]
    test_groups = groups.iloc[test_idx]

    overlap = set(train_groups).intersection(
        set(test_groups)
    )

    print()
    print(f"Train encounters : {train_groups.nunique():,}")
    print(f"Test encounters  : {test_groups.nunique():,}")
    print(f"Encounter overlap: {len(overlap)}")

    if len(overlap) != 0:
        raise RuntimeError(
            "E9 split contains encounter overlap."
        )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    model = RandomForestRegressor(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        min_samples_split=MIN_SAMPLES_SPLIT,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    print()
    print("Training Random Forest Regressor...")

    model.fit(X_train, y_train)

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    predictions = model.predict(X_test)

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions
        )
    )

    r2 = r2_score(
        y_test,
        predictions
    )

    print()
    print("E9 MODEL METRICS")
    print("-" * 70)
    print(f"MAE     : {mae:.4f} days")
    print(f"RMSE    : {rmse:.4f} days")
    print(f"R²      : {r2:.4f}")

    # --------------------------------------------------------
    # Feature importance
    # --------------------------------------------------------

    importance = pd.DataFrame({
        "feature": X.columns,
        "importance": model.feature_importances_
    }).sort_values(
        "importance",
        ascending=False
    )

    print()
    print("TOP FEATURES")
    print("-" * 70)

    print(
        importance.head(15).to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Artifact
    # --------------------------------------------------------

    artifact = {
        "model": model,
        "feature_names": list(X.columns),
        "metrics": {
            "mae": float(mae),
            "rmse": float(rmse),
            "r2": float(r2)
        },
        "config": {
            "n_estimators": N_ESTIMATORS,
            "max_depth": MAX_DEPTH,
            "min_samples_split": MIN_SAMPLES_SPLIT,
            "random_state": RANDOM_STATE
        },
        "target": "recovery_days",
        "interval_method": "Random Forest tree prediction quantiles",
        "lower_quantile": LOWER_QUANTILE,
        "upper_quantile": UPPER_QUANTILE,
        "interpretation": (
            "Observational model-based recovery estimate; "
            "not causal and not a guaranteed clinical prognosis."
        )
    }

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(
            artifact,
            f
        )

    print()
    print(f"Artifact saved: {MODEL_PATH}")

    return artifact


# ============================================================
# LOAD MODEL
# ============================================================

def load_recovery_model():
    """
    Load the trained E9 artifact.
    """

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"E9 model artifact not found: {MODEL_PATH}"
        )

    with open(MODEL_PATH, "rb") as f:
        artifact = pickle.load(f)

    if "model" not in artifact:
        raise ValueError(
            "Invalid E9 artifact: model missing."
        )

    if "feature_names" not in artifact:
        raise ValueError(
            "Invalid E9 artifact: feature_names missing."
        )

    return artifact


# ============================================================
# VALIDATE ARTIFACT
# ============================================================

def validate_model_artifact():
    """
    Validate that the E9 model artifact is usable.
    """

    artifact = load_recovery_model()

    model = artifact["model"]
    feature_names = artifact["feature_names"]

    if not hasattr(model, "estimators_"):
        raise ValueError(
            "E9 model does not contain Random Forest estimators."
        )

    if len(feature_names) == 0:
        raise ValueError(
            "E9 feature list is empty."
        )

    if len(model.estimators_) != N_ESTIMATORS:
        warnings.warn(
            "Artifact estimator count differs from current configuration."
        )

    print()
    print("=" * 70)
    print("E9 ARTIFACT VALIDATION")
    print("=" * 70)
    print(f"Model type      : {type(model).__name__}")
    print(f"Feature count   : {len(feature_names)}")
    print(f"Tree count      : {len(model.estimators_)}")
    print(f"Target          : {artifact.get('target')}")
    print("Artifact status : VALID")


# ============================================================
# FEATURE CONSTRUCTION FOR INFERENCE
# ============================================================

def build_prediction_features(
    patient_context,
    treatment_id,
    feature_names
):
    """
    Convert the canonical patient context + treatment into
    exactly the feature representation expected by E9.
    """

    row = {}

    # --------------------------------------------------------
    # Numerical features
    # --------------------------------------------------------

    row["age"] = patient_context.get("age", 0)
    row["temperature"] = patient_context.get(
        "vitals", {}
    ).get("temperature", 0)

    row["heart_rate"] = patient_context.get(
        "vitals", {}
    ).get("heart_rate", 0)

    row["respiratory_rate"] = patient_context.get(
        "vitals", {}
    ).get("respiratory_rate", 0)

    row["systolic_bp"] = patient_context.get(
        "vitals", {}
    ).get("systolic_bp", 0)

    row["diastolic_bp"] = patient_context.get(
        "vitals", {}
    ).get("diastolic_bp", 0)

    row["spo2"] = patient_context.get(
        "vitals", {}
    ).get("spo2", 0)

    # --------------------------------------------------------
    # Categorical features
    # --------------------------------------------------------

    row["gender"] = str(
        patient_context.get(
            "gender",
            "UNKNOWN"
        )
    )

    row["disease_id"] = str(
        patient_context.get(
            "disease_id",
            "UNKNOWN"
        )
    )

    row["severity_id"] = str(
        patient_context.get(
            "severity_id",
            "UNKNOWN"
        )
    )

    row["treatment_id"] = str(
        treatment_id
    )

    # --------------------------------------------------------
    # Symptoms
    # --------------------------------------------------------

    symptom_vector = patient_context.get(
        "symptom_vector",
        {}
    )

    for symptom_name, value in symptom_vector.items():
        row[symptom_name] = value

    X = pd.DataFrame([row])

    # --------------------------------------------------------
    # Same categorical encoding used during training
    # --------------------------------------------------------

    X = pd.get_dummies(
        X,
        columns=[
            c for c in [
                "gender",
                "disease_id",
                "severity_id",
                "treatment_id"
            ]
            if c in X.columns
        ],
        dtype=float
    )

    # --------------------------------------------------------
    # Align exactly to training features
    # --------------------------------------------------------

    X = X.reindex(
        columns=feature_names,
        fill_value=0
    )

    X = X.fillna(0)

    return X


# ============================================================
# TREE-LEVEL RECOVERY PREDICTIONS
# ============================================================

def get_tree_recovery_predictions(
    model,
    X
):
    """
    Return one recovery prediction from every Random Forest tree.
    """

    X_array = X.to_numpy(
        dtype=float
    )

    predictions = np.column_stack([
        tree.predict(X_array)
        for tree in model.estimators_
    ])

    return predictions


# ============================================================
# RECOVERY ESTIMATION
# ============================================================

def predict_recovery(
    patient_context,
    treatment_id
):
    """
    Predict expected recovery duration and empirical interval.
    """

    artifact = load_recovery_model()

    model = artifact["model"]
    feature_names = artifact["feature_names"]

    X = build_prediction_features(
        patient_context,
        treatment_id,
        feature_names
    )

    tree_predictions = get_tree_recovery_predictions(
        model,
        X
    )

    tree_predictions = np.maximum(
        tree_predictions,
        0
    )

    expected_days = float(
        np.mean(tree_predictions)
    )

    lower_days = float(
        np.quantile(
            tree_predictions,
            LOWER_QUANTILE
        )
    )

    upper_days = float(
        np.quantile(
            tree_predictions,
            UPPER_QUANTILE
        )
    )

    std_days = float(
        np.std(
            tree_predictions
        )
    )

    interval_width = float(
        upper_days - lower_days
    )

    # --------------------------------------------------------
    # Project-defined uncertainty label
    # --------------------------------------------------------

    if interval_width < 2.0:
        uncertainty_level = "LOW"

    elif interval_width < 5.0:
        uncertainty_level = "MODERATE"

    else:
        uncertainty_level = "HIGH"

    return {
        "treatment_id": treatment_id,
        "expected_recovery_days": expected_days,
        "recovery_lower_days": lower_days,
        "recovery_upper_days": upper_days,
        "recovery_std_days": std_days,
        "recovery_interval_width_days": interval_width,
        "recovery_uncertainty_level": uncertainty_level,
        "tree_count": len(model.estimators_),
        "interval_method": (
            "Random Forest tree prediction "
            "10th-90th percentiles"
        ),
        "interpretation": (
            "Observational model-based recovery estimate. "
            "Not causal, not guaranteed, and not a clinical prognosis."
        )
    }


# ============================================================
# MULTIPLE TREATMENTS
# ============================================================

def predict_recovery_for_treatments(
    patient_context,
    treatment_ids
):
    """
    Estimate recovery time for multiple treatments.
    """

    results = []

    for treatment_id in treatment_ids:

        result = predict_recovery(
            patient_context,
            treatment_id
        )

        results.append(result)

    return results


# ============================================================
# FIND VALID TEST ENCOUNTER
# ============================================================

def find_valid_test_encounter(limit=500):
    """
    Find a valid encounter for E9 inference testing.

    The encounter must:
        - have recovery_days
        - successfully build E1 patient context
        - successfully generate E2 treatment candidates
        - contain at least one candidate treatment
    """

    from ML.treatment_advisor.candidate_treatments import (
        generate_candidates_for_encounter
    )

    engine = get_database_engine()

    query = f"""
        SELECT
            encounter_id
        FROM patient_encounter
        WHERE recovery_days IS NOT NULL
          AND recovery_days >= 0
        ORDER BY visit_timestamp
        LIMIT {int(limit)}
    """

    encounters = pd.read_sql(
        query,
        engine
    )

    if encounters.empty:
        raise RuntimeError(
            "No encounters with recovery_days were found."
        )

    last_error = None

    for encounter_id in encounters[
        "encounter_id"
    ].tolist():

        try:

            # ------------------------------------------------
            # E1 -> E2
            #
            # E2 returns:
            #   context
            #   candidates
            #   candidate_records
            # ------------------------------------------------

            (
                context,
                candidates,
                candidate_records
            ) = generate_candidates_for_encounter(
                encounter_id
            )

            # ------------------------------------------------
            # Validate context
            # ------------------------------------------------

            if context is None:
                continue

            if not context.get("disease_id"):
                continue

            if not context.get("severity_id"):
                continue

            # ------------------------------------------------
            # Validate candidates
            # ------------------------------------------------

            if candidates is None:
                continue

            if candidates.empty:
                continue

            return (
                encounter_id,
                context,
                candidates
            )

        except Exception as e:

            last_error = e
            continue

    if last_error is not None:
        raise RuntimeError(
            "Could not find a valid E9 test encounter. "
            f"Last encountered error: {last_error}"
        )

    raise RuntimeError(
        "Could not find a valid E9 test encounter."
    )

# ============================================================
# E9 PIPELINE TEST
# ============================================================

def run_e9_pipeline_test():
    """
    Test canonical E1 -> E2 -> E3 -> E4 -> E9 flow.

    E1:
        Patient context

    E2:
        Candidate treatment generation

    E3:
        Clinical eligibility

    E4:
        Guideline + availability + resource enrichment

    E9:
        Recovery time estimation
    """

    print()
    print("=" * 70)
    print("E9 PIPELINE TEST")
    print("=" * 70)

    # ========================================================
    # PROJECT MODULES
    # ========================================================

    from ML.treatment_advisor.clinical_eligibility import (
        load_treatment_master,
        evaluate_candidates
    )

    from ML.treatment_advisor.candidate_treatments import (
        generate_candidates_for_encounter
    )

    from ML.treatment_advisor.e4_configuration import (
        enrich_candidates
    )

    from ML.treatment_advisor.patient_context import (
        build_patient_context
    )

    # ========================================================
    # FIND VALID TEST ENCOUNTER
    # ========================================================

    encounter_id, context, candidates = (
        find_valid_test_encounter()
    )

    print()
    print(f"Encounter ID : {encounter_id}")
    print(f"Disease      : {context.get('disease_id')}")
    print(f"Severity     : {context.get('severity_id')}")

    # ========================================================
    # VERIFY PATIENT CONTEXT
    # ========================================================

    if not context:
        raise RuntimeError(
            "E1 patient context is empty."
        )

    if not context.get("disease_id"):
        raise RuntimeError(
            "Disease ID missing from patient context."
        )

    if not context.get("severity_id"):
        raise RuntimeError(
            "Severity ID missing from patient context."
        )

    print("E1 context: VALID")

    # ========================================================
    # E2 - CANDIDATE TREATMENTS
    # ========================================================

    # E2 was already executed inside
    # find_valid_test_encounter().
    #
    # generate_candidates_for_encounter() returns:
    #     context
    #     candidates
    #     candidate_records
    #
    # The candidates DataFrame returned by that call
    # is already available here.

    if candidates is None or candidates.empty:
        raise RuntimeError(
            "E2 produced no candidate treatments."
        )

    print(
        f"E2 candidates: {len(candidates)}"
    )

    # ========================================================
    # E3 - CLINICAL ELIGIBILITY
    # ========================================================

    treatment_master = load_treatment_master()

    if treatment_master is None or treatment_master.empty:
        raise RuntimeError(
            "Treatment master is empty."
        )

    eligible = evaluate_candidates(
        candidates,
        treatment_master
    )

    if eligible is None or eligible.empty:
        raise RuntimeError(
            "E3 produced no eligible treatment records."
        )

    print(
        f"E3 candidates: {len(eligible)}"
    )

    # ========================================================
    # GET REAL HOSPITAL ID
    # ========================================================

    # E1 canonical context does not contain hospital_id.
    # Therefore retrieve it directly from patient_encounter,
    # exactly as done in the working E6/E7/E8 pipeline.

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
            f"Hospital not found for encounter {encounter_id}."
        )

    hospital_id = hospital_df.iloc[0]["hospital_id"]

    if pd.isna(hospital_id):
        raise RuntimeError(
            f"Hospital ID is NULL for encounter {encounter_id}."
        )

    hospital_id = str(hospital_id)

    print(
        f"Hospital      : {hospital_id}"
    )

    # ========================================================
    # E4 - CONFIGURATION ENRICHMENT
    # ========================================================

    enriched = enrich_candidates(
        eligible,
        hospital_id
    )

    if enriched is None or enriched.empty:
        raise RuntimeError(
            "E4 produced no enriched treatment candidates."
        )

    print(
        f"E4 candidates: {len(enriched)}"
    )

    # ========================================================
    # E9 - RECOVERY ESTIMATION
    # ========================================================

    if "treatment_id" not in enriched.columns:
        raise RuntimeError(
            "E4 output does not contain treatment_id."
        )

    treatment_ids = (
        enriched["treatment_id"]
        .dropna()
        .astype(str)
        .tolist()
    )

    if len(treatment_ids) == 0:
        raise RuntimeError(
            "No treatment IDs available for E9."
        )

    results = predict_recovery_for_treatments(
        context,
        treatment_ids
    )

    if results is None or len(results) == 0:
        raise RuntimeError(
            "E9 produced no recovery predictions."
        )

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    print()
    print("-" * 70)
    print("E9 RECOVERY ESTIMATES")
    print("-" * 70)

    for result in results:

        print()

        print(
            f"Treatment ID: "
            f"{result['treatment_id']}"
        )

        print(
            f"Expected recovery: "
            f"{result['expected_recovery_days']:.2f} days"
        )

        print(
            f"Recovery interval: "
            f"{result['recovery_lower_days']:.2f} - "
            f"{result['recovery_upper_days']:.2f} days"
        )

        print(
            f"Recovery std: "
            f"{result['recovery_std_days']:.2f} days"
        )

        print(
            f"Interval width: "
            f"{result['recovery_interval_width_days']:.2f} days"
        )

        print(
            f"Uncertainty: "
            f"{result['recovery_uncertainty_level']}"
        )

        print(
            f"Trees: "
            f"{result['tree_count']}"
        )

    # ========================================================
    # E9 OUTPUT VALIDATION
    # ========================================================

    valid_uncertainty_levels = {
        "LOW",
        "MODERATE",
        "HIGH"
    }

    for result in results:

        # ----------------------------------------------------
        # Required fields
        # ----------------------------------------------------

        required_fields = [
            "treatment_id",
            "expected_recovery_days",
            "recovery_lower_days",
            "recovery_upper_days",
            "recovery_std_days",
            "recovery_interval_width_days",
            "recovery_uncertainty_level",
            "tree_count"
        ]

        for field in required_fields:

            if field not in result:
                raise RuntimeError(
                    f"E9 output missing field: {field}"
                )

        # ----------------------------------------------------
        # Numeric sanity checks
        # ----------------------------------------------------

        expected = result[
            "expected_recovery_days"
        ]

        lower = result[
            "recovery_lower_days"
        ]

        upper = result[
            "recovery_upper_days"
        ]

        std = result[
            "recovery_std_days"
        ]

        width = result[
            "recovery_interval_width_days"
        ]

        if not np.isfinite(expected):
            raise RuntimeError(
                "E9 produced non-finite expected recovery."
            )

        if not np.isfinite(lower):
            raise RuntimeError(
                "E9 produced non-finite lower bound."
            )

        if not np.isfinite(upper):
            raise RuntimeError(
                "E9 produced non-finite upper bound."
            )

        if not np.isfinite(std):
            raise RuntimeError(
                "E9 produced non-finite recovery std."
            )

        if not np.isfinite(width):
            raise RuntimeError(
                "E9 produced non-finite interval width."
            )

        # ----------------------------------------------------
        # Non-negative recovery time
        # ----------------------------------------------------

        if expected < 0:
            raise RuntimeError(
                "E9 produced negative expected recovery duration."
            )

        if lower < 0:
            raise RuntimeError(
                "E9 produced negative lower recovery bound."
            )

        if upper < 0:
            raise RuntimeError(
                "E9 produced negative upper recovery bound."
            )

        # ----------------------------------------------------
        # Interval ordering
        # ----------------------------------------------------

        if lower > expected:
            raise RuntimeError(
                "E9 lower bound exceeds expected recovery."
            )

        if upper < expected:
            raise RuntimeError(
                "E9 upper bound is below expected recovery."
            )

        if lower > upper:
            raise RuntimeError(
                "E9 recovery interval is invalid."
            )

        # ----------------------------------------------------
        # Standard deviation
        # ----------------------------------------------------

        if std < 0:
            raise RuntimeError(
                "E9 recovery standard deviation is negative."
            )

        # ----------------------------------------------------
        # Interval width
        # ----------------------------------------------------

        calculated_width = upper - lower

        if not np.isclose(
            width,
            calculated_width,
            atol=1e-6
        ):
            raise RuntimeError(
                "E9 interval width does not match "
                "upper - lower."
            )

        # ----------------------------------------------------
        # Uncertainty classification
        # ----------------------------------------------------

        if (
            result["recovery_uncertainty_level"]
            not in valid_uncertainty_levels
        ):
            raise RuntimeError(
                "E9 returned an invalid uncertainty level."
            )

        # ----------------------------------------------------
        # Tree count
        # ----------------------------------------------------

        if result["tree_count"] <= 0:
            raise RuntimeError(
                "E9 tree count must be greater than zero."
            )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    print()
    print("=" * 70)
    print("E9 VALIDATION: PASSED")
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("E9 - RECOVERY ESTIMATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Train
    # --------------------------------------------------------

    train_recovery_model()

    # --------------------------------------------------------
    # Validate artifact
    # --------------------------------------------------------

    validate_model_artifact()

    # --------------------------------------------------------
    # Pipeline test
    # --------------------------------------------------------

    run_e9_pipeline_test()


if __name__ == "__main__":
    main()
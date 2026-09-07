"""
B8 - OBJECTIVE A INTEGRATION
============================

Connects Objective A emerging / atypical symptom intelligence
with Objective B epidemiological surveillance.

Objective A:
    A1-A9 emerging / atypical symptom detection
    -> emerging_signal_fusion.csv

Objective B:
    B2 - symptom surveillance
    B3 - historical baseline
    B5 - temporal acceleration
    B6 - persistence
    B7 - spatial propagation

B8 asks:

    Is an Objective A atypical/emerging symptom pattern
    also receiving epidemiological support from Objective B?

Important:
    This module does NOT declare a confirmed outbreak.

It produces an integrated surveillance signal that can later
be consumed by B10.

Output:
    objective_a_integration.csv
    objective_a_integration_latest.csv
"""


from pathlib import Path
import re

import pandas as pd


# ============================================================
# PATHS
# ============================================================

CURRENT_DIR = Path(__file__).resolve().parent

EMERGING_DIR = (
    CURRENT_DIR / "../../emerging_symptoms"
).resolve()

# Objective A
A6_FILE = (
    EMERGING_DIR / "emerging_signal_fusion.csv"
)

# Objective B
B2_FILE = (
    CURRENT_DIR / "symptom_weekly_surveillance.csv"
)

B3_FILE = (
    CURRENT_DIR / "symptom_historical_baseline.csv"
)

B5_FILE = (
    CURRENT_DIR / "temporal_acceleration.csv"
)

B6_FILE = (
    CURRENT_DIR / "symptom_persistence_detection.csv"
)

B7_FILE = (
    CURRENT_DIR / "spatial_propagation.csv"
)

# Outputs
OUTPUT_FILE = (
    CURRENT_DIR / "objective_a_integration.csv"
)

LATEST_OUTPUT_FILE = (
    CURRENT_DIR / "objective_a_integration_latest.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

# Objective A minimum score to be considered a meaningful
# emerging / atypical candidate.

MIN_OBJECTIVE_A_SCORE = 35.0


# Maximum amount by which epidemiological corroboration
# can strengthen the Objective A signal.

MAX_EPIDEMIOLOGICAL_BOOST = 40.0


# Evidence weights inside the epidemiological corroboration
# score.

WEIGHT_INCIDENCE = 0.25
WEIGHT_BASELINE = 0.25
WEIGHT_TEMPORAL = 0.20
WEIGHT_PERSISTENCE = 0.15
WEIGHT_SPATIAL = 0.15


# Alert thresholds.

YELLOW_THRESHOLD = 35.0
ORANGE_THRESHOLD = 55.0
RED_THRESHOLD = 75.0


# Objective A category boosts.

UNEXPLAINED_BOOST = 15.0
ATYPICAL_BOOST = 10.0
EMERGING_BOOST = 5.0


# ============================================================
# HELPERS
# ============================================================

def safe_float(
    value,
    default=0.0,
):
    try:

        if pd.isna(value):
            return default

        return float(value)

    except (
        ValueError,
        TypeError,
    ):

        return default


def safe_int(
    value,
    default=0,
):
    try:

        if pd.isna(value):
            return default

        return int(
            float(value)
        )

    except (
        ValueError,
        TypeError,
    ):

        return default


def clip_score(value):

    return max(
        0.0,
        min(
            100.0,
            safe_float(value),
        ),
    )


def normalize_text(value):

    if pd.isna(value):

        return ""

    value = str(
        value
    ).strip().lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


def load_csv(
    path,
    name,
):

    if not path.exists():

        raise FileNotFoundError(
            f"\n{name} file not found:\n"
            f"{path}\n"
        )

    df = pd.read_csv(
        path,
        keep_default_na=False,
    )

    print(
        f"{name} rows: {len(df)}"
    )

    return df


def require_columns(
    df,
    columns,
    name,
):

    missing = [
        column
        for column in columns
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            f"\n{name} is missing required columns:\n"
            + "\n".join(missing)
            + "\n\nAvailable columns:\n"
            + ", ".join(df.columns)
        )


# ============================================================
# PATTERN PARSING
# ============================================================

def pattern_symptoms(
    pattern,
):
    """
    Convert:

        Fever + Headache + Rash

    into:

        {"fever", "headache", "rash"}
    """

    if not pattern:

        return set()

    return {
        normalize_text(part)
        for part in str(
            pattern
        ).split("+")
        if normalize_text(part)
    }

def category_boost(category):
    """
    Small Objective A category-specific adjustment.

    The boost is intentionally modest because the actual
    Objective A evidence is already represented by
    final_emerging_score.
    """

    category = str(
        category
    ).upper().strip()

    if "UNEXPLAINED" in category:
        return UNEXPLAINED_BOOST

    if "ATYPICAL" in category:
        return ATYPICAL_BOOST

    if "EMERGING" in category:
        return EMERGING_BOOST

    return 0.0

# ============================================================
# OBJECTIVE A
# ============================================================

def load_objective_a():

    df = load_csv(
        A6_FILE,
        "Objective A / A6",
    )

    require_columns(
        df,
        [
            "symptom_pattern",
            "inference_category",
        ],
        "emerging_signal_fusion.csv",
    )

    numeric_columns = [

        "hospitals_affected",

        "hospital_coverage_pct",

        "total_anomalous_occurrences",

        "mean_prevalence_growth",

        "mean_persistence_weeks",

        "cross_hospital_score",

        "known_disease_emerging_score",

        "novelty_score",

        "emergence_evidence_score",

        "disease_inference_signal",

        "clinical_evidence_score",

        "lab_support_score",

        "vital_support_score",

        "imaging_support_score",

        "disease_specific_test_support",

        "temporal_emergence_score",

        "final_emerging_score",

        "confidence_score",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    df["inference_category"] = (
        df["inference_category"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # --------------------------------------------------------
    # Final Objective A score
    # --------------------------------------------------------

    if "final_emerging_score" in df.columns:

        df["objective_a_score"] = (
            df["final_emerging_score"]
            .apply(clip_score)
        )

    elif "emergence_evidence_score" in df.columns:

        df["objective_a_score"] = (
            df["emergence_evidence_score"]
            .apply(clip_score)
        )

    else:

        df["objective_a_score"] = 0.0

    # --------------------------------------------------------
    # One strongest row per pattern
    # --------------------------------------------------------

    df = (
        df
        .sort_values(
            "objective_a_score",
            ascending=False,
        )
        .drop_duplicates(
            subset=[
                "symptom_pattern"
            ],
            keep="first",
        )
        .reset_index(
            drop=True
        )
    )

    return df


# ============================================================
# B2 - SYMPTOM SURVEILLANCE
# ============================================================

def load_b2():

    df = load_csv(
        B2_FILE,
        "B2 symptom surveillance",
    )

    require_columns(
        df,
        [
            "week",
            "hospital_id",
            "symptom_id",
            "symptom_name",
            "case_count",
        ],
        "symptom_weekly_surveillance.csv",
    )

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce",
    )

    df["case_count"] = pd.to_numeric(
        df["case_count"],
        errors="coerce",
    ).fillna(0)

    if "growth_rate" in df.columns:

        df["growth_rate"] = pd.to_numeric(
            df["growth_rate"],
            errors="coerce",
        ).fillna(0)

    else:

        df["growth_rate"] = 0.0

    if "incidence_proportion" in df.columns:

        df["incidence_proportion"] = pd.to_numeric(
            df["incidence_proportion"],
            errors="coerce",
        ).fillna(0)

    else:

        df["incidence_proportion"] = 0.0

    df["_symptom_norm"] = (
        df["symptom_name"]
        .astype(str)
        .map(normalize_text)
    )

    return df


def latest_b2_per_symptom(
    b2,
):
    """
    B2 contains hospital × symptom × week.

    For pattern-level integration, retain the latest
    hospital-level observations and then aggregate.
    """

    latest_week = b2["week"].max()

    return b2[
        b2["week"] == latest_week
    ].copy()


# ============================================================
# B3 - HISTORICAL BASELINE
# ============================================================

def load_b3(
    b2,
):

    df = load_csv(
        B3_FILE,
        "B3 historical baseline",
    )

    require_columns(
        df,
        [
            "week",
            "hospital_id",
            "symptom_id",
        ],
        "symptom_historical_baseline.csv",
    )

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Attach symptom names.
    # --------------------------------------------------------

    if "symptom_name" not in df.columns:

        mapping = (
            b2[
                [
                    "symptom_id",
                    "symptom_name",
                ]
            ]
            .drop_duplicates(
                "symptom_id"
            )
        )

        df = df.merge(
            mapping,
            on="symptom_id",
            how="left",
        )

    df["_symptom_norm"] = (
        df["symptom_name"]
        .astype(str)
        .map(normalize_text)
    )

    numeric_columns = [

        "case_count",

        "historical_mean",

        "historical_std",

        "deviation_from_baseline",

        "deviation_percent",

        "z_score",

        "historical_weeks",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    return df


def latest_b3_per_hospital_symptom(
    b3,
):
    """
    IMPORTANT:

    B3 is hospital × symptom × week.

    We therefore retain:

        latest week
        for every hospital × symptom

    rather than collapsing B3 to one row per symptom.
    """

    latest_week = b3["week"].max()

    return b3[
        b3["week"] == latest_week
    ].copy()


# ============================================================
# B5 - TEMPORAL ACCELERATION
# ============================================================

def load_b5(
    b2,
):

    df = load_csv(
        B5_FILE,
        "B5 temporal acceleration",
    )

    require_columns(
        df,
        [
            "week",
            "symptom_id",
        ],
        "temporal_acceleration.csv",
    )

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce",
    )

    numeric_columns = [

        "current_cases",

        "average_growth_rate",

        "avg_growth_rate",

        "growth_acceleration",

        "max_growth_acceleration",

        "change_points",

        "recent_change_points",

        "exponential_growth_detections",

        "temporal_acceleration_score",

        "score",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    # --------------------------------------------------------
    # Attach symptom name if required.
    # --------------------------------------------------------

    if "symptom_name" not in df.columns:

        mapping = (
            b2[
                [
                    "symptom_id",
                    "symptom_name",
                ]
            ]
            .drop_duplicates(
                "symptom_id"
            )
        )

        df = df.merge(
            mapping,
            on="symptom_id",
            how="left",
        )

    df["_symptom_norm"] = (
        df["symptom_name"]
        .astype(str)
        .map(normalize_text)
    )

    return df


def latest_b5_per_symptom(
    b5,
):

    latest_week = b5["week"].max()

    return b5[
        b5["week"] == latest_week
    ].copy()


# ============================================================
# B6 - PERSISTENCE
# ============================================================

def load_b6():

    df = load_csv(
        B6_FILE,
        "B6 persistence",
    )

    require_columns(
        df,
        [
            "week",
            "symptom_id",
            "symptom_name",
            "persistence_score",
        ],
        "symptom_persistence_detection.csv",
    )

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce",
    )

    numeric_columns = [

        "current_cases",

        "hospitals_observed",

        "persistent_hospitals",

        "maximum_consecutive_abnormal_weeks",

        "maximum_total_abnormal_weeks",

        "average_z_score",

        "maximum_z_score",

        "average_deviation_percent",

        "elevated_hospitals",

        "temporal_acceleration_score",

        "cross_hospital_consecutive_weeks",

        "persistence_score",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    df["_symptom_norm"] = (
        df["symptom_name"]
        .astype(str)
        .map(normalize_text)
    )

    return df


def latest_b6_per_symptom(
    b6,
):

    latest_week = b6["week"].max()

    return b6[
        b6["week"] == latest_week
    ].copy()


# ============================================================
# B7 - SPATIAL PROPAGATION
# ============================================================

def load_b7():

    df = load_csv(
        B7_FILE,
        "B7 spatial propagation",
    )

    require_columns(
        df,
        [
            "week",
            "symptom_id",
            "symptom_name",
            "affected_hospitals",
            "hospital_coverage",
            "newly_affected_hospitals",
            "propagation_edges",
            "spatial_propagation_score",
        ],
        "spatial_propagation.csv",
    )

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce",
    )

    numeric_columns = [

        "affected_hospitals",

        "total_hospitals",

        "total_cases",

        "hospital_coverage",

        "affected_regions",

        "geographic_cases",

        "affected_cities",

        "newly_affected_hospitals",

        "propagation_edges",

        "source_hospitals",

        "target_hospitals",

        "same_city_edges",

        "same_region_edges",

        "cross_region_edges",

        "spatial_propagation_score",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    df["_symptom_norm"] = (
        df["symptom_name"]
        .astype(str)
        .map(normalize_text)
    )

    return df


def latest_b7_per_symptom(
    b7,
):

    latest_week = b7["week"].max()

    return b7[
        b7["week"] == latest_week
    ].copy()


# ============================================================
# B2 EVIDENCE
# ============================================================

def calculate_b2_evidence(
    pattern,
    b2_latest,
):
    """
    Determine whether component symptoms are showing
    epidemiological activity.

    We use the strongest component symptom.

    Cases are NOT summed.
    """

    symptoms = pattern_symptoms(
        pattern
    )

    matching = b2_latest[
        b2_latest["_symptom_norm"]
        .isin(symptoms)
    ].copy()

    if matching.empty:

        return {
            "b2_current_cases": 0.0,
            "b2_growth_rate": 0.0,
            "b2_incidence_proportion": 0.0,
            "b2_hospitals_observed": 0,
            "b2_component_symptoms_observed": 0,
            "b2_incidence_score": 0.0,
        }

    # Aggregate current cases by component symptom.

    component = (
        matching
        .groupby(
            "symptom_name",
            as_index=False,
        )
        .agg(
            current_cases=(
                "case_count",
                "sum",
            ),
            growth_rate=(
                "growth_rate",
                "mean",
            ),
            incidence_proportion=(
                "incidence_proportion",
                "mean",
            ),
            hospitals=(
                "hospital_id",
                "nunique",
            ),
        )
    )

    strongest = (
        component
        .sort_values(
            "current_cases",
            ascending=False,
        )
        .iloc[0]
    )

    current_cases = safe_float(
        strongest[
            "current_cases"
        ]
    )

    growth = safe_float(
        strongest[
            "growth_rate"
        ]
    )

    incidence = safe_float(
        strongest[
            "incidence_proportion"
        ]
    )

    # B2 growth can be stored as decimal or percentage.

    growth_pct = (
        growth * 100
        if abs(growth) <= 5
        else growth
    )

    growth_component = min(
        1.0,
        max(
            0.0,
            growth_pct / 100.0,
        ),
    )

    volume_component = min(
        1.0,
        current_cases / 100.0,
    )

    score = (
        0.60 * growth_component
        +
        0.40 * volume_component
    ) * 100

    return {
        "b2_current_cases": current_cases,
        "b2_growth_rate": growth,
        "b2_incidence_proportion": incidence,
        "b2_hospitals_observed": int(
            matching[
                "hospital_id"
            ].nunique()
        ),
        "b2_component_symptoms_observed": len(
            component
        ),
        "b2_incidence_score": clip_score(
            score
        ),
    }


# ============================================================
# B3 EVIDENCE
# ============================================================

def calculate_b3_evidence(
    pattern,
    b3_latest,
):
    """
    Calculate baseline evidence using ALL hospitals.

    This is the key B3 correction.

    For every component symptom we inspect all hospitals
    in the latest B3 week and retain the strongest abnormal
    observation.

    This prevents a single arbitrary hospital row from
    representing the entire national signal.
    """

    symptoms = pattern_symptoms(
        pattern
    )

    matching = b3_latest[
        b3_latest["_symptom_norm"]
        .isin(symptoms)
    ].copy()

    if matching.empty:

        return {
            "b3_max_z_score": 0.0,
            "b3_max_deviation_percent": 0.0,
            "b3_elevated_hospitals": 0,
            "b3_abnormal_hospitals": 0,
            "b3_baseline_score": 0.0,
        }

    z = pd.to_numeric(
        matching.get(
            "z_score",
            pd.Series(
                0,
                index=matching.index,
            ),
        ),
        errors="coerce",
    ).fillna(0)

    deviation = pd.to_numeric(
        matching.get(
            "deviation_percent",
            pd.Series(
                0,
                index=matching.index,
            ),
        ),
        errors="coerce",
    ).fillna(0)

    max_z = safe_float(
        z.max()
    )

    max_deviation = safe_float(
        deviation.max()
    )

    # Elevated = z >= 1.5, matching the existing B3 logic.

    elevated = int(
        (
            z >= 1.5
        ).sum()
    )

    # Abnormal = z >= 1.

    abnormal = int(
        (
            z >= 1.0
        ).sum()
    )

    z_component = min(
        1.0,
        max(
            0.0,
            max_z / 3.0,
        ),
    )

    deviation_component = min(
        1.0,
        max(
            0.0,
            max_deviation / 100.0,
        ),
    )

    # Small coverage contribution.

    coverage_component = min(
        1.0,
        elevated / 5.0,
    )

    score = (
        0.55 * z_component
        +
        0.30 * deviation_component
        +
        0.15 * coverage_component
    ) * 100

    return {
        "b3_max_z_score": max_z,
        "b3_max_deviation_percent": max_deviation,
        "b3_elevated_hospitals": elevated,
        "b3_abnormal_hospitals": abnormal,
        "b3_baseline_score": clip_score(
            score
        ),
    }


# ============================================================
# B5 EVIDENCE
# ============================================================

def calculate_b5_evidence(
    pattern,
    b5_latest,
):
    """
    Use the strongest temporal evidence among the component
    symptoms.
    """

    symptoms = pattern_symptoms(
        pattern
    )

    matching = b5_latest[
        b5_latest["_symptom_norm"]
        .isin(symptoms)
    ].copy()

    if matching.empty:

        return {
            "b5_growth_acceleration": 0.0,
            "b5_change_points": 0.0,
            "b5_exponential_growth": 0.0,
            "b5_temporal_score": 0.0,
        }

    acceleration_column = (
        "max_growth_acceleration"
        if "max_growth_acceleration"
        in matching.columns
        else "growth_acceleration"
    )

    if acceleration_column not in matching.columns:

        acceleration_column = None

    change_column = None

    if "recent_change_points" in matching.columns:

        change_column = (
            "recent_change_points"
        )

    elif "change_points" in matching.columns:

        change_column = (
            "change_points"
        )

    exponential_column = (
        "exponential_growth_detections"
        if "exponential_growth_detections"
        in matching.columns
        else None
    )

    if acceleration_column:

        acceleration = pd.to_numeric(
            matching[
                acceleration_column
            ],
            errors="coerce",
        ).fillna(0)

    else:

        acceleration = pd.Series(
            0,
            index=matching.index,
        )

    if change_column:

        change_points = pd.to_numeric(
            matching[
                change_column
            ],
            errors="coerce",
        ).fillna(0)

    else:

        change_points = pd.Series(
            0,
            index=matching.index,
        )

    if exponential_column:

        exponential = pd.to_numeric(
            matching[
                exponential_column
            ],
            errors="coerce",
        ).fillna(0)

    else:

        exponential = pd.Series(
            0,
            index=matching.index,
        )

    max_acceleration = safe_float(
        acceleration.max()
    )

    max_change_points = safe_float(
        change_points.max()
    )

    max_exponential = safe_float(
        exponential.max()
    )

    acceleration_component = min(
        1.0,
        max(
            0.0,
            max_acceleration / 50.0,
        ),
    )

    change_component = min(
        1.0,
        max(
            0.0,
            max_change_points / 3.0,
        ),
    )

    exponential_component = min(
        1.0,
        max_exponential,
    )

    score = (
        0.50 * acceleration_component
        +
        0.30 * change_component
        +
        0.20 * exponential_component
    ) * 100

    return {
        "b5_growth_acceleration":
            max_acceleration,

        "b5_change_points":
            max_change_points,

        "b5_exponential_growth":
            max_exponential,

        "b5_temporal_score":
            clip_score(
                score
            ),
    }


# ============================================================
# B6 EVIDENCE
# ============================================================

def calculate_b6_evidence(
    pattern,
    b6_latest,
):
    """
    Use the strongest persistence evidence among the
    component symptoms.
    """

    symptoms = pattern_symptoms(
        pattern
    )

    matching = b6_latest[
        b6_latest["_symptom_norm"]
        .isin(symptoms)
    ].copy()

    if matching.empty:

        return {
            "b6_max_consecutive_weeks": 0.0,
            "b6_cross_hospital_consecutive_weeks": 0.0,
            "b6_elevated_hospitals": 0.0,
            "b6_persistence_score": 0.0,
        }

    max_consecutive = safe_float(
        matching[
            "maximum_consecutive_abnormal_weeks"
        ].max()
    )

    max_cross_hospital = safe_float(
        matching[
            "cross_hospital_consecutive_weeks"
        ].max()
    )

    max_elevated = safe_float(
        matching[
            "elevated_hospitals"
        ].max()
    )

    max_score = safe_float(
        matching[
            "persistence_score"
        ].max()
    )

    return {
        "b6_max_consecutive_weeks":
            max_consecutive,

        "b6_cross_hospital_consecutive_weeks":
            max_cross_hospital,

        "b6_elevated_hospitals":
            max_elevated,

        "b6_persistence_score":
            clip_score(
                max_score
            ),
    }


# ============================================================
# B7 EVIDENCE
# ============================================================

def calculate_b7_evidence(
    pattern,
    b7_latest,
):
    """
    Use the strongest spatial propagation evidence among
    component symptoms.
    """

    symptoms = pattern_symptoms(
        pattern
    )

    matching = b7_latest[
        b7_latest["_symptom_norm"]
        .isin(symptoms)
    ].copy()

    if matching.empty:

        return {
            "b7_affected_hospitals": 0.0,
            "b7_newly_affected_hospitals": 0.0,
            "b7_propagation_edges": 0.0,
            "b7_affected_regions": 0.0,
            "b7_spatial_score": 0.0,
        }

    strongest = (
        matching
        .sort_values(
            "spatial_propagation_score",
            ascending=False,
        )
        .iloc[0]
    )

    return {
        "b7_affected_hospitals":
            safe_float(
                strongest[
                    "affected_hospitals"
                ]
            ),

        "b7_newly_affected_hospitals":
            safe_float(
                strongest[
                    "newly_affected_hospitals"
                ]
            ),

        "b7_propagation_edges":
            safe_float(
                strongest[
                    "propagation_edges"
                ]
            ),

        "b7_affected_regions":
            safe_float(
                strongest[
                    "affected_regions"
                ]
            ),

        "b7_spatial_score":
            clip_score(
                strongest[
                    "spatial_propagation_score"
                ]
            ),
    }


# ============================================================
# EPIDEMIOLOGICAL CORROBORATION
# ============================================================

def calculate_epidemiological_score(
    b2_score,
    b3_score,
    b5_score,
    b6_score,
    b7_score,
):
    """
    Produce a single epidemiological corroboration score.

    This is deliberately SEPARATE from the Objective A score.

    Objective A:
        "Is this pattern unusual/emerging?"

    Epidemiological evidence:
        "Is there evidence that it is actually behaving
         abnormally in the population?"

    B8 combines these two concepts afterwards.
    """

    score = (

        WEIGHT_INCIDENCE
        * clip_score(
            b2_score
        )

        +

        WEIGHT_BASELINE
        * clip_score(
            b3_score
        )

        +

        WEIGHT_TEMPORAL
        * clip_score(
            b5_score
        )

        +

        WEIGHT_PERSISTENCE
        * clip_score(
            b6_score
        )

        +

        WEIGHT_SPATIAL
        * clip_score(
            b7_score
        )
    )

    return clip_score(
        score
    )


# ============================================================
# B8 INTEGRATION SCORE
# ============================================================

def calculate_b8_score(
    objective_a_score,
    epidemiological_score,
):
    """
    Combine Objective A and epidemiological corroboration.

    Important design:

        B8 starts from Objective A.

        Objective B evidence then adds corroboration.

    This means:

        HIGH Objective A
        + LOW Objective B

    remains visible as a meaningful surveillance signal,
    instead of being mathematically diluted into GREEN.

    Maximum epidemiological contribution is capped.
    """

    objective_a_score = clip_score(
        objective_a_score
    )

    epidemiological_score = clip_score(
        epidemiological_score
    )

    if (
        objective_a_score
        < MIN_OBJECTIVE_A_SCORE
    ):

        # Weak Objective A signals cannot become strong
        # merely because common symptoms have epidemiological
        # activity.

        return clip_score(
            objective_a_score
            * 0.50
            +
            epidemiological_score
            * 0.20
        )

    # --------------------------------------------------------
    # Corroboration boost
    # --------------------------------------------------------

    boost = (
        epidemiological_score
        / 100.0
        * MAX_EPIDEMIOLOGICAL_BOOST
    )

    return clip_score(
        objective_a_score
        + boost
    )


# ============================================================
# ALERT
# ============================================================

def determine_b8_alert(
    b8_score,
    objective_a_score,
    epidemiological_score,
    b2_score,
    b3_score,
    b5_score,
    b6_score,
    b7_score,
):
    """
    B8 alert classification.

    The logic deliberately distinguishes:

        unusual pattern
        from
        corroborated epidemiological event.
    """

    b8_score = clip_score(
        b8_score
    )

    objective_a_score = clip_score(
        objective_a_score
    )

    epidemiological_score = clip_score(
        epidemiological_score
    )

    # --------------------------------------------------------
    # RED
    #
    # Very strong Objective A signal + strong epi evidence.
    # --------------------------------------------------------

    if (
        b8_score >= RED_THRESHOLD
        and objective_a_score >= 55
        and epidemiological_score >= 55
        and (
            b6_score >= 40
            or b7_score >= 40
            or b3_score >= 55
        )
    ):

        return "RED"

    # --------------------------------------------------------
    # ORANGE
    #
    # Strong Objective A signal with meaningful
    # epidemiological corroboration.
    # --------------------------------------------------------

    if (
        b8_score >= ORANGE_THRESHOLD
        and objective_a_score >= 45
        and epidemiological_score >= 30
        and (
            b2_score >= 30
            or b3_score >= 30
            or b5_score >= 30
            or b6_score >= 30
            or b7_score >= 30
        )
    ):

        return "ORANGE"

    # --------------------------------------------------------
    # YELLOW
    #
    # Objective A itself is meaningful.
    #
    # Some epidemiological evidence is enough to promote
    # it to a watch signal.
    #
    # We intentionally allow Objective A-only YELLOW when
    # the signal is strong enough.
    # --------------------------------------------------------

    if (
        b8_score >= YELLOW_THRESHOLD
        and objective_a_score >= 45
    ):

        return "YELLOW"

    return "GREEN"


# ============================================================
# EXPLANATION
# ============================================================

def build_explanation(
    row,
):
    """
    Explain exactly how Objective A and Objective B
    contributed to the B8 result.
    """

    parts = []

    category = str(
        row.get(
            "inference_category",
            "",
        )
    ).upper()

    if "UNEXPLAINED" in category:

        parts.append(
            "Objective A identified an unexplained "
            "emerging symptom pattern"
        )

    elif "ATYPICAL" in category:

        parts.append(
            "Objective A identified an atypical "
            "clinical presentation"
        )

    elif "EMERGING" in category:

        parts.append(
            "Objective A identified emerging behaviour "
            "within a known disease pattern"
        )

    else:

        parts.append(
            "Objective A identified an unusual "
            "symptom pattern"
        )

    # --------------------------------------------------------
    # Objective A score
    # --------------------------------------------------------

    a_score = safe_float(
        row.get(
            "objective_a_component_score",
            0,
        )
    )

    parts.append(
        f"Objective A evidence score is "
        f"{a_score:.1f}"
    )

    # --------------------------------------------------------
    # B2
    # --------------------------------------------------------

    cases = safe_float(
        row.get(
            "b2_current_cases",
            0,
        )
    )

    growth = safe_float(
        row.get(
            "b2_growth_rate",
            0,
        )
    )

    growth_pct = (
        growth * 100
        if abs(growth) <= 5
        else growth
    )

    if cases > 0:

        parts.append(
            f"the strongest component symptom has "
            f"{cases:.0f} current cases"
        )

    if abs(growth_pct) >= 5:

        parts.append(
            f"with {growth_pct:.1f}% recent growth"
        )

    # --------------------------------------------------------
    # B3
    # --------------------------------------------------------

    z = safe_float(
        row.get(
            "b3_max_z_score",
            0,
        )
    )

    deviation = safe_float(
        row.get(
            "b3_max_deviation_percent",
            0,
        )
    )

    elevated = safe_int(
        row.get(
            "b3_elevated_hospitals",
            0,
        )
    )

    if z > 0:

        parts.append(
            f"baseline evidence reaches "
            f"z={z:.2f}"
        )

    if deviation > 0:

        parts.append(
            f"with a maximum deviation of "
            f"{deviation:.1f}%"
        )

    if elevated > 0:

        parts.append(
            f"{elevated} hospital-level baseline "
            f"observation(s) are elevated"
        )

    # --------------------------------------------------------
    # B5
    # --------------------------------------------------------

    acceleration = safe_float(
        row.get(
            "b5_growth_acceleration",
            0,
        )
    )

    change_points = safe_float(
        row.get(
            "b5_change_points",
            0,
        )
    )

    if acceleration > 0:

        parts.append(
            f"temporal acceleration reaches "
            f"{acceleration:.1f}"
        )

    if change_points > 0:

        parts.append(
            f"{change_points:.0f} change-point "
            f"detection(s) are present"
        )

    # --------------------------------------------------------
    # B6
    # --------------------------------------------------------

    consecutive = safe_float(
        row.get(
            "b6_max_consecutive_weeks",
            0,
        )
    )

    if consecutive > 0:

        parts.append(
            f"persistence reaches "
            f"{consecutive:.0f} consecutive abnormal weeks"
        )

    # --------------------------------------------------------
    # B7
    # --------------------------------------------------------

    affected = safe_float(
        row.get(
            "b7_affected_hospitals",
            0,
        )
    )

    newly = safe_float(
        row.get(
            "b7_newly_affected_hospitals",
            0,
        )
    )

    edges = safe_float(
        row.get(
            "b7_propagation_edges",
            0,
        )
    )

    if affected > 0:

        parts.append(
            f"{affected:.0f} hospital(s) show "
            f"spatial evidence"
        )

    if newly > 0:

        parts.append(
            f"{newly:.0f} hospital(s) are newly affected"
        )

    if edges > 0:

        parts.append(
            f"{edges:.0f} propagation edge(s) are present"
        )

    # --------------------------------------------------------
    # Final interpretation
    # --------------------------------------------------------

    epi = safe_float(
        row.get(
            "epidemiological_evidence_score",
            0,
        )
    )

    alert = str(
        row.get(
            "b8_alert",
            "GREEN",
        )
    )

    parts.append(
        f"combined epidemiological corroboration "
        f"score is {epi:.1f}"
    )

    if alert == "GREEN":

        parts.append(
            "the available evidence does not currently "
            "support an elevated integrated surveillance alert"
        )

    elif alert == "YELLOW":

        parts.append(
            "the pattern warrants continued surveillance"
        )

    elif alert == "ORANGE":

        parts.append(
            "multiple epidemiological indicators support "
            "an elevated surveillance signal"
        )

    elif alert == "RED":

        parts.append(
            "multiple independent indicators support "
            "a high-risk integrated outbreak signal"
        )

    return (
        ". ".join(parts)
        + "."
    )


# ============================================================
# BUILD B8
# ============================================================

def build_b8(
    objective_a,
    b2,
    b3,
    b5,
    b6,
    b7,
):
    """
    Build one integrated row per Objective A pattern.
    """

    # --------------------------------------------------------
    # Latest observations
    # --------------------------------------------------------

    b2_latest = latest_b2_per_symptom(
        b2
    )

    b3_latest = latest_b3_per_hospital_symptom(
        b3
    )

    b5_latest = latest_b5_per_symptom(
        b5
    )

    b6_latest = latest_b6_per_symptom(
        b6
    )

    b7_latest = latest_b7_per_symptom(
        b7
    )

    rows = []

    # --------------------------------------------------------
    # Objective A patterns
    # --------------------------------------------------------

    for _, a_row in objective_a.iterrows():

        pattern = str(
            a_row[
                "symptom_pattern"
            ]
        ).strip()

        if not pattern:
            continue

        # ====================================================
        # OBJECTIVE A
        # ====================================================

        raw_a_score = safe_float(
            a_row.get(
                "objective_a_score",
                0,
            )
        )

        boost = category_boost(
            a_row.get(
                "inference_category",
                "",
            )
        )

        objective_a_component = clip_score(
            raw_a_score + boost
        )

        # ====================================================
        # B2
        # ====================================================

        b2_evidence = calculate_b2_evidence(
            pattern,
            b2_latest,
        )

        # ====================================================
        # B3
        # ====================================================

        b3_evidence = calculate_b3_evidence(
            pattern,
            b3_latest,
        )

        # ====================================================
        # B5
        # ====================================================

        b5_evidence = calculate_b5_evidence(
            pattern,
            b5_latest,
        )

        # ====================================================
        # B6
        # ====================================================

        b6_evidence = calculate_b6_evidence(
            pattern,
            b6_latest,
        )

        # ====================================================
        # B7
        # ====================================================

        b7_evidence = calculate_b7_evidence(
            pattern,
            b7_latest,
        )

        # ====================================================
        # Epidemiological corroboration
        # ====================================================

        epidemiological_score = (
            calculate_epidemiological_score(

                b2_evidence[
                    "b2_incidence_score"
                ],

                b3_evidence[
                    "b3_baseline_score"
                ],

                b5_evidence[
                    "b5_temporal_score"
                ],

                b6_evidence[
                    "b6_persistence_score"
                ],

                b7_evidence[
                    "b7_spatial_score"
                ],
            )
        )

        # ====================================================
        # B8 SCORE
        # ====================================================

        b8_score = calculate_b8_score(

            objective_a_score=(
                objective_a_component
            ),

            epidemiological_score=(
                epidemiological_score
            ),
        )

        # ====================================================
        # ALERT
        # ====================================================

        alert = determine_b8_alert(

            b8_score=b8_score,

            objective_a_score=(
                objective_a_component
            ),

            epidemiological_score=(
                epidemiological_score
            ),

            b2_score=(
                b2_evidence[
                    "b2_incidence_score"
                ]
            ),

            b3_score=(
                b3_evidence[
                    "b3_baseline_score"
                ]
            ),

            b5_score=(
                b5_evidence[
                    "b5_temporal_score"
                ]
            ),

            b6_score=(
                b6_evidence[
                    "b6_persistence_score"
                ]
            ),

            b7_score=(
                b7_evidence[
                    "b7_spatial_score"
                ]
            ),
        )

        # ====================================================
        # SIGNAL
        # ====================================================

        integration_signal = (
            alert
            in {
                "YELLOW",
                "ORANGE",
                "RED",
            }
        )

        # ====================================================
        # ROW
        # ====================================================

        row = {

            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "symptom_pattern":
                pattern,

            "best_matching_disease_id":
                a_row.get(
                    "best_matching_disease_id",
                    "",
                ),

            "best_matching_disease":
                a_row.get(
                    "best_matching_disease",
                    "",
                ),

            "pathogen_type":
                a_row.get(
                    "pathogen_type",
                    "",
                ),

            "inference_category":
                a_row.get(
                    "inference_category",
                    "",
                ),

            "signal_type":
                a_row.get(
                    "signal_type",
                    "",
                ),

            # ------------------------------------------------
            # Objective A
            # ------------------------------------------------

            "objective_a_score":
                round(
                    raw_a_score,
                    2,
                ),

            "objective_a_category_boost":
                round(
                    boost,
                    2,
                ),

            "objective_a_component_score":
                round(
                    objective_a_component,
                    2,
                ),

            "objective_a_confidence":
                round(
                    safe_float(
                        a_row.get(
                            "confidence_score",
                            0,
                        )
                    ),
                    2,
                ),

            "objective_a_alert":
                a_row.get(
                    "final_alert_level",
                    "",
                ),

            # ------------------------------------------------
            # B2
            # ------------------------------------------------

            "b2_current_cases":
                round(
                    b2_evidence[
                        "b2_current_cases"
                    ],
                    2,
                ),

            "b2_growth_rate":
                round(
                    b2_evidence[
                        "b2_growth_rate"
                    ],
                    4,
                ),

            "b2_incidence_proportion":
                round(
                    b2_evidence[
                        "b2_incidence_proportion"
                    ],
                    6,
                ),

            "b2_hospitals_observed":
                b2_evidence[
                    "b2_hospitals_observed"
                ],

            "b2_component_symptoms_observed":
                b2_evidence[
                    "b2_component_symptoms_observed"
                ],

            "b2_incidence_score":
                round(
                    b2_evidence[
                        "b2_incidence_score"
                    ],
                    2,
                ),

            # ------------------------------------------------
            # B3
            # ------------------------------------------------

            "b3_max_z_score":
                round(
                    b3_evidence[
                        "b3_max_z_score"
                    ],
                    3,
                ),

            "b3_max_deviation_percent":
                round(
                    b3_evidence[
                        "b3_max_deviation_percent"
                    ],
                    2,
                ),

            "b3_elevated_hospitals":
                b3_evidence[
                    "b3_elevated_hospitals"
                ],

            "b3_abnormal_hospitals":
                b3_evidence[
                    "b3_abnormal_hospitals"
                ],

            "b3_baseline_score":
                round(
                    b3_evidence[
                        "b3_baseline_score"
                    ],
                    2,
                ),

            # ------------------------------------------------
            # B5
            # ------------------------------------------------

            "b5_growth_acceleration":
                round(
                    b5_evidence[
                        "b5_growth_acceleration"
                    ],
                    2,
                ),

            "b5_change_points":
                round(
                    b5_evidence[
                        "b5_change_points"
                    ],
                    2,
                ),

            "b5_exponential_growth":
                round(
                    b5_evidence[
                        "b5_exponential_growth"
                    ],
                    2,
                ),

            "b5_temporal_score":
                round(
                    b5_evidence[
                        "b5_temporal_score"
                    ],
                    2,
                ),

            # ------------------------------------------------
            # B6
            # ------------------------------------------------

            "b6_max_consecutive_weeks":
                round(
                    b6_evidence[
                        "b6_max_consecutive_weeks"
                    ],
                    2,
                ),

            "b6_cross_hospital_consecutive_weeks":
                round(
                    b6_evidence[
                        "b6_cross_hospital_consecutive_weeks"
                    ],
                    2,
                ),

            "b6_elevated_hospitals":
                round(
                    b6_evidence[
                        "b6_elevated_hospitals"
                    ],
                    2,
                ),

            "b6_persistence_score":
                round(
                    b6_evidence[
                        "b6_persistence_score"
                    ],
                    2,
                ),

            # ------------------------------------------------
            # B7
            # ------------------------------------------------

            "b7_affected_hospitals":
                round(
                    b7_evidence[
                        "b7_affected_hospitals"
                    ],
                    2,
                ),

            "b7_newly_affected_hospitals":
                round(
                    b7_evidence[
                        "b7_newly_affected_hospitals"
                    ],
                    2,
                ),

            "b7_propagation_edges":
                round(
                    b7_evidence[
                        "b7_propagation_edges"
                    ],
                    2,
                ),

            "b7_affected_regions":
                round(
                    b7_evidence[
                        "b7_affected_regions"
                    ],
                    2,
                ),

            "b7_spatial_score":
                round(
                    b7_evidence[
                        "b7_spatial_score"
                    ],
                    2,
                ),

            # ------------------------------------------------
            # B8
            # ------------------------------------------------

            "epidemiological_evidence_score":
                round(
                    epidemiological_score,
                    2,
                ),

            "b8_integration_score":
                round(
                    b8_score,
                    2,
                ),

            "b8_alert":
                alert,

            "b8_integration_signal":
                integration_signal,

            # ------------------------------------------------
            # Objective A explanation
            # ------------------------------------------------

            "objective_a_explanation":
                a_row.get(
                    "final_explanation",
                    "",
                ),
        }

        rows.append(
            row
        )

    result = pd.DataFrame(
        rows
    )

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    if not result.empty:

        result[
            "b8_explanation"
        ] = result.apply(
            build_explanation,
            axis=1,
        )

        result = (
            result
            .sort_values(
                [
                    "b8_integration_score",
                    "objective_a_component_score",
                ],
                ascending=False,
            )
            .reset_index(
                drop=True
            )
        )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("B8 - OBJECTIVE A INTEGRATION")
    print("=" * 80)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    print()
    print("Loading Objective A...")

    objective_a = (
        load_objective_a()
    )

    print()
    print("Loading Objective B...")

    b2 = load_b2()

    b3 = load_b3(
        b2
    )

    b5 = load_b5(
        b2
    )

    b6 = load_b6()

    b7 = load_b7()

    # --------------------------------------------------------
    # Build
    # --------------------------------------------------------

    print()
    print(
        "Integrating Objective A with "
        "Objective B..."
    )

    result = build_b8(

        objective_a=objective_a,

        b2=b2,

        b3=b3,

        b5=b5,

        b6=b6,

        b7=b7,
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if result.empty:

        print()
        print(
            "ERROR: B8 produced no rows."
        )

        return

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    result.to_csv(
        LATEST_OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("B8 COMPLETE")
    print("=" * 80)

    print(
        f"Objective A patterns: "
        f"{len(objective_a)}"
    )

    print(
        f"Integrated patterns: "
        f"{len(result)}"
    )

    print()

    print(
        "B8 alert summary:"
    )

    print(
        result[
            "b8_alert"
        ]
        .value_counts()
        .to_string()
    )

    print()

    print(
        "B8 integration signals: "
        f"{int(result['b8_integration_signal'].sum())}"
    )

    # --------------------------------------------------------
    # Strongest signals
    # --------------------------------------------------------

    print()
    print(
        "Strongest integrated signals:"
    )

    display_columns = [

        "symptom_pattern",

        "best_matching_disease",

        "inference_category",

        "objective_a_component_score",

        "b2_incidence_score",

        "b3_baseline_score",

        "b5_temporal_score",

        "b6_persistence_score",

        "b7_spatial_score",

        "epidemiological_evidence_score",

        "b8_integration_score",

        "b8_alert",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in result.columns
    ]

    print(
        result[
            display_columns
        ]
        .head(15)
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    print()
    print(
        "Top integrated signal explanation:"
    )

    print(
        result.iloc[0][
            "b8_explanation"
        ]
    )

    # --------------------------------------------------------
    # Output paths
    # --------------------------------------------------------

    print()

    print(
        f"Main output: "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Latest output: "
        f"{LATEST_OUTPUT_FILE}"
    )

    print()
    print("=" * 80)
    print("B8 READY FOR VALIDATION")
    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
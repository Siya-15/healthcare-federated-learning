from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# PATHS
# ============================================================

ML_DIR = Path(__file__).resolve().parents[1]
EMERGING_DIR = ML_DIR / "emerging_symptoms"

A3_FILE = (
    EMERGING_DIR
    / "cross_hospital_symptom_patterns.csv"
)

A4_FILE = (
    EMERGING_DIR
    / "emerging_disease_inference.csv"
)

A5_FILE = (
    EMERGING_DIR
    / "clinical_evidence_signals.csv"
)

OUTPUT_FILE = (
    EMERGING_DIR
    / "emerging_signal_fusion.csv"
)


# ============================================================
# SCORE WEIGHTS
# ============================================================

# Epidemiological emergence
A3_WEIGHT = 0.30

# Disease inference / novelty
A4_WEIGHT = 0.25

# Clinical evidence
A5_WEIGHT = 0.25

# Temporal / persistence evidence
TEMPORAL_WEIGHT = 0.20


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_numeric(series, default=0.0):
    """
    Convert a pandas series to numeric safely.
    """
    return pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(default)


def clip_score(value):
    """
    Keep a score between 0 and 100.
    """
    return float(
        max(
            0.0,
            min(
                100.0,
                value
            )
        )
    )


def normalize_coverage(value):
    """
    Convert hospital coverage into percentage.

    A3 may store:
        0.9  -> 90
        90   -> 90
    """

    value = float(value)

    if value <= 1.0:
        return value * 100.0

    return value


# ============================================================
# LOAD INPUTS
# ============================================================

def load_inputs():

    for file_path in [
        A3_FILE,
        A4_FILE,
        A5_FILE,
    ]:

        if not file_path.exists():

            raise FileNotFoundError(
                f"Required input not found:\n"
                f"{file_path}"
            )

    a3 = pd.read_csv(
        A3_FILE
    )

    a4 = pd.read_csv(
        A4_FILE
    )

    a5 = pd.read_csv(
        A5_FILE
    )

    print(
        f"A3 patterns loaded: {len(a3)}"
    )

    print(
        f"A4 patterns loaded: {len(a4)}"
    )

    print(
        f"A5 patterns loaded: {len(a5)}"
    )

    return a3, a4, a5


# ============================================================
# VALIDATE INPUTS
# ============================================================

def validate_inputs(
    a3,
    a4,
    a5
):

    required_a3 = [
        "symptom_pattern",
        "hospitals_affected",
        "hospital_coverage",
        "total_anomalous_occurrences",
        "mean_prevalence_growth",
        "mean_persistence_weeks",
        "cross_hospital_score",
        "alert_level",
    ]

    required_a4 = [
        "symptom_pattern",
        "best_matching_disease_id",
        "best_matching_disease",
        "inference_category",
        "known_disease_emerging_score",
        "novelty_score",
    ]

    required_a5 = [
        "symptom_pattern",
        "clinical_evidence_score",
        "lab_support_score",
        "vital_support_score",
        "imaging_support_score",
        "disease_specific_test_support",
        "combined_surveillance_score",
        "clinical_support_category",
        "final_interpretation",
    ]

    for column in required_a3:

        if column not in a3.columns:

            raise ValueError(
                f"A3 is missing column: "
                f"{column}"
            )

    for column in required_a4:

        if column not in a4.columns:

            raise ValueError(
                f"A4 is missing column: "
                f"{column}"
            )

    for column in required_a5:

        if column not in a5.columns:

            raise ValueError(
                f"A5 is missing column: "
                f"{column}"
            )


# ============================================================
# PREPARE A3
# ============================================================

def prepare_a3(a3):

    columns = [
        "symptom_pattern",
        "hospitals_affected",
        "hospital_coverage",
        "total_anomalous_occurrences",
        "mean_prevalence_growth",
        "mean_persistence_weeks",
        "cross_hospital_score",
        "spread_level",
        "alert_level",
    ]

    result = a3[
        [
            c
            for c in columns
            if c in a3.columns
        ]
    ].copy()

    result = result.drop_duplicates(
        subset=["symptom_pattern"]
    )

    result[
        "hospitals_affected"
    ] = safe_numeric(
        result[
            "hospitals_affected"
        ]
    )

    result[
        "hospital_coverage_pct"
    ] = result[
        "hospital_coverage"
    ].apply(
        normalize_coverage
    )

    result[
        "total_anomalous_occurrences"
    ] = safe_numeric(
        result[
            "total_anomalous_occurrences"
        ]
    )

    result[
        "mean_prevalence_growth"
    ] = safe_numeric(
        result[
            "mean_prevalence_growth"
        ]
    )

    result[
        "mean_persistence_weeks"
    ] = safe_numeric(
        result[
            "mean_persistence_weeks"
        ]
    )

    result[
        "cross_hospital_score"
    ] = safe_numeric(
        result[
            "cross_hospital_score"
        ]
    )

    # --------------------------------------------------------
    # Temporal score
    # --------------------------------------------------------

    # Positive prevalence growth
    growth_component = (
        result[
            "mean_prevalence_growth"
        ]
        .clip(
            lower=0,
            upper=3
        )
        / 3
        * 100
    )

    # Persistence
    persistence_component = (
        result[
            "mean_persistence_weeks"
        ]
        .clip(
            lower=0,
            upper=6
        )
        / 6
        * 100
    )

    # Anomaly volume
    anomaly_component = (
        np.log1p(
            result[
                "total_anomalous_occurrences"
            ]
        )
        /
        np.log1p(
            result[
                "total_anomalous_occurrences"
            ].max()
        )
        * 100
    )

    result[
        "temporal_emergence_score"
    ] = (
        growth_component * 0.45
        +
        persistence_component * 0.35
        +
        anomaly_component * 0.20
    ).clip(
        0,
        100
    )

    return result


# ============================================================
# PREPARE A4
# ============================================================

def prepare_a4(a4):

    columns = [
        "symptom_pattern",
        "best_matching_disease_id",
        "best_matching_disease",
        "pathogen_type",
        "inference_category",
        "known_disease_emerging_score",
        "novelty_score",
        "emergence_evidence_score",
        "compatibility_score",
        "atypical_fraction",
        "explanation",
    ]

    available = [
        c
        for c in columns
        if c in a4.columns
    ]

    result = a4[
        available
    ].copy()

    result = result.drop_duplicates(
        subset=["symptom_pattern"]
    )

    # Missing optional columns
    for column in [
        "pathogen_type",
        "explanation",
    ]:

        if column not in result.columns:

            result[column] = ""

    # Numeric columns
    numeric_columns = [
        "known_disease_emerging_score",
        "novelty_score",
        "emergence_evidence_score",
        "compatibility_score",
        "atypical_fraction",
    ]

    for column in numeric_columns:

        if column in result.columns:

            result[column] = safe_numeric(
                result[column]
            )

    return result


# ============================================================
# PREPARE A5
# ============================================================

def prepare_a5(a5):

    columns = [
        "symptom_pattern",
        "clinical_evidence_score",
        "lab_support_score",
        "vital_support_score",
        "imaging_support_score",
        "disease_specific_test_support",
        "combined_surveillance_score",
        "clinical_support_category",
        "final_interpretation",
        "supporting_lab_tests",
        "supporting_imaging_findings",
        "explanation",
    ]

    available = [
        c
        for c in columns
        if c in a5.columns
    ]

    result = a5[
        available
    ].copy()

    result = result.drop_duplicates(
        subset=["symptom_pattern"]
    )

    numeric_columns = [
        "clinical_evidence_score",
        "lab_support_score",
        "vital_support_score",
        "imaging_support_score",
        "disease_specific_test_support",
        "combined_surveillance_score",
    ]

    for column in numeric_columns:

        if column in result.columns:

            result[column] = safe_numeric(
                result[column]
            )

    return result


# ============================================================
# DISEASE / NOVELTY SCORE
# ============================================================

def calculate_disease_signal(row):

    category = (
        str(
            row[
                "inference_category"
            ]
        )
        .strip()
        .upper()
    )

    known_emerging = float(
        row[
            "known_disease_emerging_score"
        ]
    )

    novelty = float(
        row[
            "novelty_score"
        ]
    )

    emergence = float(
        row[
            "emergence_evidence_score"
        ]
    )

    atypical = float(
        row.get(
            "atypical_fraction",
            0
        )
    )

    # --------------------------------------------------------
    # Unexplained patterns
    # --------------------------------------------------------

    if category == (
        "UNEXPLAINED_EMERGING_PATTERN"
    ):

        return clip_score(
            novelty * 0.55
            +
            emergence * 0.45
        )

    # --------------------------------------------------------
    # Known disease emerging
    # --------------------------------------------------------

    if category == (
        "KNOWN_DISEASE_EMERGING"
    ):

        return clip_score(
            known_emerging * 0.70
            +
            emergence * 0.30
        )

    # --------------------------------------------------------
    # Known disease atypical
    # --------------------------------------------------------

    if category == (
        "KNOWN_DISEASE_ATYPICAL"
    ):

        atypical_score = (
            min(
                atypical,
                100
            )
        )

        return clip_score(
            known_emerging * 0.45
            +
            emergence * 0.25
            +
            atypical_score * 0.30
        )

    # --------------------------------------------------------
    # Expected known disease
    # --------------------------------------------------------

    if category == (
        "KNOWN_DISEASE_EXPECTED"
    ):

        # Expected disease should receive
        # a lower novelty contribution.
        return clip_score(
            known_emerging * 0.50
            +
            emergence * 0.10
        )

    # --------------------------------------------------------
    # Insufficient evidence
    # --------------------------------------------------------

    return clip_score(
        emergence * 0.40
        +
        novelty * 0.60
    )


# ============================================================
# FINAL ALERT CLASSIFICATION
# ============================================================

def classify_alert(row):

    score = float(
        row["final_emerging_score"]
    )

    category = str(
        row["inference_category"]
    ).upper()

    clinical = float(
        row["clinical_evidence_score"]
    )

    hospitals = int(
        row["hospitals_affected"]
    )

    temporal = float(
        row["temporal_emergence_score"]
    )

    novelty = float(
        row["novelty_score"]
    )

    # ========================================================
    # UNEXPLAINED EMERGING PATTERN
    # ========================================================

    if category == "UNEXPLAINED_EMERGING_PATTERN":

        if (
            score >= 75
            and hospitals >= 5
            and clinical >= 40
            and temporal >= 50
        ):
            return "CRITICAL"

        if (
            score >= 60
            and hospitals >= 3
            and clinical >= 30
            and temporal >= 40
        ):
            return "HIGH"

        if score >= 40:
            return "MODERATE"

        return "LOW"

    # ========================================================
    # KNOWN DISEASE EMERGING
    # ========================================================

    if category == "KNOWN_DISEASE_EMERGING":

        if (
            score >= 70
            and hospitals >= 5
            and clinical >= 50
            and temporal >= 55
        ):
            return "HIGH"

        if (
            score >= 50
            and hospitals >= 3
            and temporal >= 40
        ):
            return "MODERATE"

        return "LOW"

    # ========================================================
    # KNOWN DISEASE ATYPICAL
    # ========================================================

    if category == "KNOWN_DISEASE_ATYPICAL":

        if (
            score >= 65
            and clinical >= 50
            and temporal >= 45
        ):
            return "HIGH"

        if (
            score >= 45
            and clinical >= 40
        ):
            return "MODERATE"

        return "LOW"

    # ========================================================
    # EXPECTED KNOWN DISEASE
    # ========================================================
    #
    # A widespread expected disease is NOT automatically
    # an emerging alert.
    #
    # It can still be represented as a surveillance signal,
    # but should remain LOW unless there is unusually strong
    # temporal emergence evidence.
    # ========================================================

    if category == "KNOWN_DISEASE_EXPECTED":

        if (
            temporal >= 75
            and hospitals >= 5
            and score >= 65
        ):
            return "MODERATE"

        return "LOW"

    # ========================================================
    # INSUFFICIENT EVIDENCE
    # ========================================================

    if category == "INSUFFICIENT_EVIDENCE":

        if (
            novelty >= 60
            and temporal >= 50
            and hospitals >= 3
        ):
            return "MODERATE"

        return "LOW"

    return "LOW"


# ============================================================
# SIGNAL TYPE
# ============================================================

def determine_signal_type(row):

    category = str(
        row[
            "inference_category"
        ]
    ).upper()

    temporal = float(
        row[
            "temporal_emergence_score"
        ]
    )

    clinical = float(
        row[
            "clinical_evidence_score"
        ]
    )

    novelty = float(
        row[
            "novelty_score"
        ]
    )

    cross_hospital = float(
        row[
            "cross_hospital_score"
        ]
    )

    # --------------------------------------------------------
    # Novel / unexplained
    # --------------------------------------------------------

    if category == (
        "UNEXPLAINED_EMERGING_PATTERN"
    ):

        if temporal >= 50:

            return (
                "UNEXPLAINED_EMERGING_PATTERN"
            )

        return (
            "UNEXPLAINED_PATTERN"
        )

    # --------------------------------------------------------
    # Known disease but emerging
    # --------------------------------------------------------

    if category == (
        "KNOWN_DISEASE_EMERGING"
    ):

        if clinical >= 50:

            return (
                "KNOWN_DISEASE_WITH_CLINICAL_EMERGENCE"
            )

        return (
            "KNOWN_DISEASE_EPIDE​MIOLOGICAL_EMERGENCE"
        )

    # --------------------------------------------------------
    # Atypical known disease
    # --------------------------------------------------------

    if category == (
        "KNOWN_DISEASE_ATYPICAL"
    ):

        if temporal >= 45:

            return (
                "ATYPICAL_KNOWN_DISEASE_EMERGENCE"
            )

        return (
            "ATYPICAL_KNOWN_DISEASE_PATTERN"
        )

    # --------------------------------------------------------
    # Expected disease
    # --------------------------------------------------------

    if category == (
        "KNOWN_DISEASE_EXPECTED"
    ):

        if cross_hospital >= 55:

            return (
                "WIDESPREAD_KNOWN_DISEASE_PATTERN"
            )

        return (
            "EXPECTED_KNOWN_DISEASE_PATTERN"
        )

    # --------------------------------------------------------
    # Insufficient evidence
    # --------------------------------------------------------

    if novelty >= 50:

        return (
            "POTENTIAL_NOVEL_PATTERN_REQUIRING_EVIDENCE"
        )

    return (
        "INSUFFICIENT_EMERGING_EVIDENCE"
    )


# ============================================================
# CONFIDENCE
# ============================================================

def calculate_confidence(row):

    scores = [
        float(
            row[
                "cross_hospital_score"
            ]
        ),

        float(
            row[
                "clinical_evidence_score"
            ]
        ),

        float(
            row[
                "temporal_emergence_score"
            ]
        ),
    ]

    # --------------------------------------------------------
    # Agreement between evidence sources
    # --------------------------------------------------------

    mean_score = np.mean(
        scores
    )

    dispersion = np.std(
        scores
    )

    agreement = max(
        0,
        100
        - dispersion * 2
    )

    # --------------------------------------------------------
    # Evidence coverage
    # --------------------------------------------------------

    evidence_sources = 0

    if row[
        "cross_hospital_score"
    ] > 0:
        evidence_sources += 1

    if row[
        "clinical_evidence_score"
    ] > 0:
        evidence_sources += 1

    if row[
        "temporal_emergence_score"
    ] > 0:
        evidence_sources += 1

    coverage = (
        evidence_sources
        / 3
        * 100
    )

    confidence = (
        agreement * 0.60
        +
        coverage * 0.40
    )

    return clip_score(
        confidence
    )


# ============================================================
# EXPLANATION
# ============================================================

def build_final_explanation(row):

    category = str(
        row[
            "inference_category"
        ]
    )

    disease = str(
        row[
            "best_matching_disease"
        ]
    )

    score = float(
        row[
            "final_emerging_score"
        ]
    )

    clinical = float(
        row[
            "clinical_evidence_score"
        ]
    )

    temporal = float(
        row[
            "temporal_emergence_score"
        ]
    )

    hospitals = int(
        row[
            "hospitals_affected"
        ]
    )

    parts = []

    # --------------------------------------------------------
    # Disease interpretation
    # --------------------------------------------------------

    if category == (
        "UNEXPLAINED_EMERGING_PATTERN"
    ):

        parts.append(
            "The symptom pattern does not "
            "closely match the existing disease "
            "profiles and therefore warrants "
            "novel-pattern surveillance."
        )

    elif category == (
        "KNOWN_DISEASE_EMERGING"
    ):

        parts.append(
            f"The pattern is compatible with "
            f"{disease} and shows evidence of "
            "emerging epidemiological activity."
        )

    elif category == (
        "KNOWN_DISEASE_ATYPICAL"
    ):

        parts.append(
            f"The pattern is associated with "
            f"{disease} but contains atypical "
            "symptom characteristics."
        )

    elif category == (
        "KNOWN_DISEASE_EXPECTED"
    ):

        parts.append(
            f"The pattern is consistent with "
            f"the expected presentation of "
            f"{disease}."
        )

    else:

        parts.append(
            "Available evidence is insufficient "
            "for a strong emerging-disease "
            "interpretation."
        )

    # --------------------------------------------------------
    # Spread
    # --------------------------------------------------------

    if hospitals >= 7:

        parts.append(
            "The pattern is observed across "
            "multiple hospitals."
        )

    elif hospitals >= 3:

        parts.append(
            "The pattern is present across "
            "several hospitals."
        )

    # --------------------------------------------------------
    # Temporal evidence
    # --------------------------------------------------------

    if temporal >= 60:

        parts.append(
            "Temporal analysis indicates strong "
            "evidence of recent emergence or "
            "persistence."
        )

    elif temporal >= 40:

        parts.append(
            "Temporal analysis provides moderate "
            "evidence of emergence."
        )

    # --------------------------------------------------------
    # Clinical evidence
    # --------------------------------------------------------

    if clinical >= 60:

        parts.append(
            "Clinical evidence from laboratory "
            "results, vital signs and/or imaging "
            "strongly supports the surveillance "
            "signal."
        )

    elif clinical >= 40:

        parts.append(
            "Clinical evidence provides moderate "
            "support for the surveillance signal."
        )

    else:

        parts.append(
            "Clinical evidence is currently "
            "limited."
        )

    parts.append(
        f"Final emerging-signal score: "
        f"{score:.1f}/100."
    )

    return " ".join(
        parts
    )


# ============================================================
# MAIN FUSION
# ============================================================

def run_fusion():

    print("=" * 80)
    print("A6 - EMERGING SIGNAL FUSION")
    print("=" * 80)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    print("\nLoading A3, A4 and A5 outputs...")

    a3, a4, a5 = load_inputs()

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    print("\nValidating input schemas...")

    validate_inputs(
        a3,
        a4,
        a5
    )

    # --------------------------------------------------------
    # Prepare
    # --------------------------------------------------------

    print("\nPreparing signals...")

    a3 = prepare_a3(
        a3
    )

    a4 = prepare_a4(
        a4
    )

    a5 = prepare_a5(
        a5
    )

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    print(
        "\nMerging epidemiological, "
        "disease-inference and clinical signals..."
    )

    fused = a3.merge(
        a4,
        on="symptom_pattern",
        how="inner",
        suffixes=(
            "_a3",
            "_a4"
        )
    )

    fused = fused.merge(
        a5,
        on="symptom_pattern",
        how="left",
        suffixes=(
            "",
            "_a5"
        )
    )

    print(
        f"Patterns after fusion: "
        f"{len(fused)}"
    )

    if fused.empty:

        raise ValueError(
            "A3, A4 and A5 contain no "
            "matching symptom patterns."
        )

    # --------------------------------------------------------
    # Fill missing A5 values
    # --------------------------------------------------------

    numeric_a5_columns = [
        "clinical_evidence_score",
        "lab_support_score",
        "vital_support_score",
        "imaging_support_score",
        "disease_specific_test_support",
        "combined_surveillance_score",
    ]

    for column in numeric_a5_columns:

        if column not in fused.columns:

            fused[column] = 0.0

        fused[column] = safe_numeric(
            fused[column]
        )

    # --------------------------------------------------------
    # A4 disease signal
    # --------------------------------------------------------

    print(
        "\nCalculating disease / novelty signals..."
    )

    fused[
        "disease_inference_signal"
    ] = fused.apply(
        calculate_disease_signal,
        axis=1
    )

    # --------------------------------------------------------
    # Temporal score
    # --------------------------------------------------------

    fused[
        "temporal_emergence_score"
    ] = safe_numeric(
        fused[
            "temporal_emergence_score"
        ]
    )

    # --------------------------------------------------------
    # Final score
    # --------------------------------------------------------

    print(
        "\nCalculating final emerging scores..."
    )

    fused[
        "final_emerging_score"
    ] = (
        fused[
            "cross_hospital_score"
        ]
        * A3_WEIGHT

        +

        fused[
            "disease_inference_signal"
        ]
        * A4_WEIGHT

        +

        fused[
            "clinical_evidence_score"
        ]
        * A5_WEIGHT

        +

        fused[
            "temporal_emergence_score"
        ]
        * TEMPORAL_WEIGHT
    )

    fused[
        "final_emerging_score"
    ] = fused[
        "final_emerging_score"
    ].clip(
        0,
        100
    ).round(2)

    # --------------------------------------------------------
    # Signal type
    # --------------------------------------------------------

    fused[
        "signal_type"
    ] = fused.apply(
        determine_signal_type,
        axis=1
    )

    # --------------------------------------------------------
    # Alert
    # --------------------------------------------------------

    fused[
        "final_alert_level"
    ] = fused.apply(
        classify_alert,
        axis=1
    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    fused[
        "confidence_score"
    ] = fused.apply(
        calculate_confidence,
        axis=1
    ).round(2)

    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    fused[
        "final_explanation"
    ] = fused.apply(
        build_final_explanation,
        axis=1
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    fused = fused.sort_values(
        [
            "final_emerging_score",
            "confidence_score",
        ],
        ascending=False
    )

    # --------------------------------------------------------
    # Select final columns
    # --------------------------------------------------------

    output_columns = [
        # Pattern
        "symptom_pattern",

        # Disease inference
        "best_matching_disease_id",
        "best_matching_disease",
        "pathogen_type",
        "inference_category",

        # A3
        "hospitals_affected",
        "hospital_coverage_pct",
        "total_anomalous_occurrences",
        "mean_prevalence_growth",
        "mean_persistence_weeks",
        "cross_hospital_score",
        "spread_level",

        # A4
        "known_disease_emerging_score",
        "novelty_score",
        "emergence_evidence_score",
        "compatibility_score",
        "atypical_fraction",
        "disease_inference_signal",

        # A5
        "clinical_evidence_score",
        "lab_support_score",
        "vital_support_score",
        "imaging_support_score",
        "disease_specific_test_support",
        "abnormal_lab_rate",
        "clinical_support_category",

        # A6
        "temporal_emergence_score",
        "final_emerging_score",
        "confidence_score",
        "signal_type",
        "final_alert_level",

        # Explanation
        "supporting_lab_tests",
        "supporting_imaging_findings",
        "final_explanation",
    ]

    output_columns = [
        c
        for c in output_columns
        if c in fused.columns
    ]

    final_df = fused[
        output_columns
    ].copy()

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    final_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        "\n" + "=" * 80
    )

    print(
        "A6 COMPLETE"
    )

    print(
        "=" * 80
    )

    print(
        f"Patterns analyzed : "
        f"{len(final_df)}"
    )

    print(
        f"Output            : "
        f"{OUTPUT_FILE}"
    )

    # --------------------------------------------------------
    # Signal types
    # --------------------------------------------------------

    print(
        "\nSignal types:"
    )

    print(
        final_df[
            "signal_type"
        ].value_counts().to_string()
    )

    # --------------------------------------------------------
    # Alerts
    # --------------------------------------------------------

    print(
        "\nFinal alert levels:"
    )

    print(
        final_df[
            "final_alert_level"
        ].value_counts().to_string()
    )

    # --------------------------------------------------------
    # Inference categories
    # --------------------------------------------------------

    print(
        "\nInference categories:"
    )

    print(
        final_df[
            "inference_category"
        ].value_counts().to_string()
    )

    # --------------------------------------------------------
    # Top signals
    # --------------------------------------------------------

    print(
        "\nTop A6 emerging signals:"
    )

    display_columns = [
        "symptom_pattern",
        "best_matching_disease",
        "inference_category",
        "cross_hospital_score",
        "disease_inference_signal",
        "clinical_evidence_score",
        "temporal_emergence_score",
        "final_emerging_score",
        "confidence_score",
        "signal_type",
        "final_alert_level",
    ]

    print(
        final_df[
            display_columns
        ].head(15).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    run_fusion()
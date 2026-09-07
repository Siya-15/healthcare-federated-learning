"""
A4 - Emerging Disease / Pathogen Inference

Objective A:

    A1 -> Anomalous encounters
    A2 -> Temporal symptom patterns
    A3 -> Cross-hospital symptom patterns
    A4 -> Disease compatibility + atypical/emerging inference

IMPORTANT
---------
This module does NOT diagnose a disease or confirm a new pathogen.

It evaluates whether an emerging symptom pattern:

    1. resembles an expected presentation of a known disease,
    2. resembles a known disease but shows atypical/emerging behavior,
    3. is poorly explained by known disease profiles and warrants
       investigation as an unexplained emerging surveillance signal.

INPUT
-----
ML/emerging_symptoms/cross_hospital_symptom_patterns.csv

KNOWLEDGE TABLES
----------------
datasets/knowledge_tables/
    disease_master.csv
    disease_symptom_mapping.csv
    symptom_master.csv

OUTPUT
------
ML/emerging_symptoms/emerging_disease_inference.csv
"""

from pathlib import Path
import re

import pandas as pd


# ============================================================
# PATHS
# ============================================================

# Current file:
#
# ML/emerging_symptoms/emerging_disease_inference.py
#
# parents[0] = emerging_symptoms
# parents[1] = ML
# parents[2] = project root

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ML_DIR = PROJECT_ROOT / "ML"

EMERGING_DIR = ML_DIR / "emerging_symptoms"

KNOWLEDGE_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "knowledge_tables"
)

A3_FILE = (
    EMERGING_DIR
    / "cross_hospital_symptom_patterns.csv"
)

OUTPUT_FILE = (
    EMERGING_DIR
    / "emerging_disease_inference.csv"
)

DISEASE_MASTER_FILE = (
    KNOWLEDGE_DIR
    / "disease_master.csv"
)

DISEASE_SYMPTOM_MAPPING_FILE = (
    KNOWLEDGE_DIR
    / "disease_symptom_mapping.csv"
)

SYMPTOM_MASTER_FILE = (
    KNOWLEDGE_DIR
    / "symptom_master.csv"
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """Normalize simple text values."""

    if pd.isna(value):
        return ""

    value = str(value).strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def normalize_name(value):
    """Normalize a name for comparison."""

    value = clean_text(value).lower()

    value = value.replace(
        "_",
        " "
    )

    value = value.replace(
        "-",
        " "
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def safe_float(
    value,
    default=0.0
):
    """Safely convert value to float."""

    try:

        if pd.isna(value):
            return default

        return float(value)

    except (
        ValueError,
        TypeError
    ):

        return default


def clamp(
    value,
    low=0.0,
    high=100.0
):
    """Clamp value to range."""

    return max(
        low,
        min(high, value)
    )


# ============================================================
# FREQUENCY WEIGHTS
# ============================================================

# These weights represent how expected a symptom is for a disease.
#
# Very Common -> strongly expected
# Common      -> expected
# Occasional  -> less expected
# Rare        -> atypical
#
# These are used for surveillance classification, not clinical
# probability.

FREQUENCY_WEIGHTS = {
    "very common": 1.00,
    "common": 0.85,
    "occasional": 0.55,
    "rare": 0.30
}


def get_frequency_weight(
    frequency
):
    """Return normalized frequency weight."""

    frequency = normalize_name(
        frequency
    )

    return FREQUENCY_WEIGHTS.get(
        frequency,
        0.60
    )


# ============================================================
# PARSE A3 PATTERN
# ============================================================

def parse_symptom_pattern(
    pattern
):
    """
    Convert:

        Fever + Headache + Muscle Pain

    into:

        ["Fever", "Headache", "Muscle Pain"]
    """

    if pd.isna(pattern):

        return []

    symptoms = []

    for part in str(pattern).split("+"):

        symptom = clean_text(
            part
        )

        if symptom:

            symptoms.append(
                symptom
            )

    return symptoms


# ============================================================
# LOAD KNOWLEDGE TABLES
# ============================================================

def load_knowledge_tables():

    print()
    print("-" * 80)
    print("LOADING KNOWLEDGE TABLES")
    print("-" * 80)

    # --------------------------------------------------------
    # Validate paths
    # --------------------------------------------------------

    required_files = [

        DISEASE_MASTER_FILE,

        DISEASE_SYMPTOM_MAPPING_FILE,

        SYMPTOM_MASTER_FILE
    ]

    for file_path in required_files:

        if not file_path.exists():

            raise FileNotFoundError(
                f"Required knowledge table not found:\n"
                f"{file_path}"
            )

    # --------------------------------------------------------
    # Disease master
    # --------------------------------------------------------

    disease_master = pd.read_csv(
        DISEASE_MASTER_FILE,
        keep_default_na=False
    )

    required_disease_columns = {
        "disease_id",
        "disease_name",
        "pathogen_type"
    }

    missing = (
        required_disease_columns
        - set(
            disease_master.columns
        )
    )

    if missing:

        raise ValueError(
            "disease_master.csv is missing "
            f"columns: {missing}"
        )

    # --------------------------------------------------------
    # Disease-symptom mapping
    # --------------------------------------------------------

    disease_symptom_mapping = pd.read_csv(
        DISEASE_SYMPTOM_MAPPING_FILE,
        keep_default_na=False
    )

    required_mapping_columns = {
        "mapping_id",
        "disease_id",
        "symptom_id",
        "frequency",
        "mandatory",
        "onset_stage"
    }

    missing = (
        required_mapping_columns
        - set(
            disease_symptom_mapping.columns
        )
    )

    if missing:

        raise ValueError(
            "disease_symptom_mapping.csv is missing "
            f"columns: {missing}"
        )

    # --------------------------------------------------------
    # Symptom master
    # --------------------------------------------------------

    symptom_master = pd.read_csv(
        SYMPTOM_MASTER_FILE,
        keep_default_na=False
    )

    required_symptom_columns = {
        "symptom_id",
        "symptom_name"
    }

    missing = (
        required_symptom_columns
        - set(
            symptom_master.columns
        )
    )

    if missing:

        raise ValueError(
            "symptom_master.csv is missing "
            f"columns: {missing}"
        )

    print(
        f"Disease master records   : "
        f"{len(disease_master)}"
    )

    print(
        f"Disease-symptom mappings : "
        f"{len(disease_symptom_mapping)}"
    )

    print(
        f"Symptom master records   : "
        f"{len(symptom_master)}"
    )

    return (
        disease_master,
        disease_symptom_mapping,
        symptom_master
    )


# ============================================================
# BUILD DISEASE PROFILES
# ============================================================

def build_disease_profiles(
    disease_master,
    disease_symptom_mapping,
    symptom_master
):
    """
    Build complete disease profiles.

    Each disease contains:

        disease name
        pathogen type
        category
        transmission
        outbreak potential
        symptom set
        mandatory symptoms
        symptom frequency
        onset stage
    """

    # --------------------------------------------------------
    # Symptom lookup
    # --------------------------------------------------------

    symptom_lookup = {}

    for _, row in symptom_master.iterrows():

        symptom_id = clean_text(
            row["symptom_id"]
        )

        symptom_name = clean_text(
            row["symptom_name"]
        )

        if (
            symptom_id
            and symptom_name
        ):

            symptom_lookup[
                symptom_id
            ] = symptom_name

    # --------------------------------------------------------
    # Disease lookup
    # --------------------------------------------------------

    disease_lookup = {}

    for _, row in disease_master.iterrows():

        disease_id = clean_text(
            row["disease_id"]
        )

        if not disease_id:

            continue

        disease_lookup[
            disease_id
        ] = {

            "disease_name":
                clean_text(
                    row["disease_name"]
                ),

            "pathogen_type":
                clean_text(
                    row["pathogen_type"]
                ),

            "disease_category":
                clean_text(
                    row.get(
                        "disease_category",
                        ""
                    )
                ),

            "communicable":
                clean_text(
                    row.get(
                        "communicable",
                        ""
                    )
                ),

            "transmission_mode":
                clean_text(
                    row.get(
                        "transmission_mode",
                        ""
                    )
                ),

            "outbreak_potential":
                clean_text(
                    row.get(
                        "outbreak_potential",
                        ""
                    )
                ),

            "seasonality_india":
                clean_text(
                    row.get(
                        "seasonality_india",
                        ""
                    )
                ),

            "priority_level":
                clean_text(
                    row.get(
                        "priority_level",
                        ""
                    )
                )
        }

    # --------------------------------------------------------
    # Construct disease profiles
    # --------------------------------------------------------

    profiles = {}

    for _, row in disease_symptom_mapping.iterrows():

        disease_id = clean_text(
            row["disease_id"]
        )

        symptom_id = clean_text(
            row["symptom_id"]
        )

        if (
            not disease_id
            or not symptom_id
        ):

            continue

        symptom_name = symptom_lookup.get(
            symptom_id,
            symptom_id
        )

        symptom_name = clean_text(
            symptom_name
        )

        normalized_symptom = normalize_name(
            symptom_name
        )

        # ----------------------------------------------------
        # Initialize disease
        # ----------------------------------------------------

        if disease_id not in profiles:

            disease_info = disease_lookup.get(
                disease_id,
                {}
            )

            profiles[disease_id] = {

                "disease_id":
                    disease_id,

                "disease_name":
                    disease_info.get(
                        "disease_name",
                        disease_id
                    ),

                "pathogen_type":
                    disease_info.get(
                        "pathogen_type",
                        ""
                    ),

                "disease_category":
                    disease_info.get(
                        "disease_category",
                        ""
                    ),

                "communicable":
                    disease_info.get(
                        "communicable",
                        ""
                    ),

                "transmission_mode":
                    disease_info.get(
                        "transmission_mode",
                        ""
                    ),

                "outbreak_potential":
                    disease_info.get(
                        "outbreak_potential",
                        ""
                    ),

                "seasonality_india":
                    disease_info.get(
                        "seasonality_india",
                        ""
                    ),

                "priority_level":
                    disease_info.get(
                        "priority_level",
                        ""
                    ),

                "symptoms":
                    set(),

                "mandatory_symptoms":
                    set(),

                "frequency":
                    {},

                "onset_stage":
                    {}
            }

        # ----------------------------------------------------
        # Add symptom
        # ----------------------------------------------------

        profiles[
            disease_id
        ][
            "symptoms"
        ].add(
            normalized_symptom
        )

        # ----------------------------------------------------
        # Frequency
        # ----------------------------------------------------

        frequency = clean_text(
            row["frequency"]
        )

        profiles[
            disease_id
        ][
            "frequency"
        ][
            normalized_symptom
        ] = frequency

        # ----------------------------------------------------
        # Mandatory
        # ----------------------------------------------------

        mandatory = normalize_name(
            row["mandatory"]
        )

        if mandatory in {
            "yes",
            "true",
            "1",
            "y"
        }:

            profiles[
                disease_id
            ][
                "mandatory_symptoms"
            ].add(
                normalized_symptom
            )

        # ----------------------------------------------------
        # Onset stage
        # ----------------------------------------------------

        onset_stage = clean_text(
            row["onset_stage"]
        )

        profiles[
            disease_id
        ][
            "onset_stage"
        ][
            normalized_symptom
        ] = onset_stage

    return profiles


# ============================================================
# DISEASE COMPATIBILITY
# ============================================================

def calculate_disease_compatibility(
    observed_symptoms,
    disease_profile
):
    """
    Calculate disease compatibility.

    Components:

        35% observed symptom coverage
        25% frequency-adjusted coverage
        20% Jaccard similarity
        10% disease profile coverage
        10% mandatory symptom coverage

    Also calculates:

        expected symptoms
        atypical symptoms
        unexplained symptoms
    """

    observed = {
        normalize_name(symptom)
        for symptom in observed_symptoms
        if clean_text(symptom)
    }

    known = disease_profile[
        "symptoms"
    ]

    mandatory = disease_profile[
        "mandatory_symptoms"
    ]

    frequency_map = disease_profile[
        "frequency"
    ]

    if (
        not observed
        or not known
    ):

        return {

            "compatibility_score":
                0.0,

            "symptom_coverage":
                0.0,

            "frequency_adjusted_coverage":
                0.0,

            "profile_coverage":
                0.0,

            "jaccard_similarity":
                0.0,

            "mandatory_coverage":
                0.0,

            "expected_symptom_fraction":
                0.0,

            "atypical_symptom_fraction":
                100.0,

            "unexplained_symptom_fraction":
                100.0,

            "matched_symptoms":
                [],

            "expected_symptoms":
                [],

            "atypical_symptoms":
                [],

            "unexplained_symptoms":
                []
        }

    # --------------------------------------------------------
    # Set intersection
    # --------------------------------------------------------

    matched = observed.intersection(
        known
    )

    unexplained = observed - known

    # --------------------------------------------------------
    # Categorize matched symptoms
    # --------------------------------------------------------

    expected_symptoms = []

    atypical_symptoms = []

    frequency_scores = []

    for symptom in matched:

        frequency = frequency_map.get(
            symptom,
            ""
        )

        weight = get_frequency_weight(
            frequency
        )

        frequency_scores.append(
            weight
        )

        if frequency in {
            "Very Common",
            "Common"
        }:

            expected_symptoms.append(
                symptom
            )

        else:

            atypical_symptoms.append(
                symptom
            )

    # --------------------------------------------------------
    # Basic symptom coverage
    # --------------------------------------------------------

    symptom_coverage = (
        len(matched)
        /
        len(observed)
    )

    # --------------------------------------------------------
    # Frequency-adjusted coverage
    #
    # A pattern containing mostly Very Common/Common
    # symptoms receives stronger compatibility than one
    # containing mostly Rare/Occasional symptoms.
    # --------------------------------------------------------

    if frequency_scores:

        frequency_adjusted_coverage = (
            sum(frequency_scores)
            /
            len(observed)
        )

    else:

        frequency_adjusted_coverage = 0.0

    # --------------------------------------------------------
    # Disease profile coverage
    # --------------------------------------------------------

    profile_coverage = (
        len(matched)
        /
        len(known)
    )

    # --------------------------------------------------------
    # Jaccard similarity
    # --------------------------------------------------------

    union = observed.union(
        known
    )

    jaccard = (
        len(matched)
        /
        len(union)
        if union
        else 0.0
    )

    # --------------------------------------------------------
    # Mandatory coverage
    # --------------------------------------------------------

    if mandatory:

        mandatory_coverage = (
            len(
                observed.intersection(
                    mandatory
                )
            )
            /
            len(mandatory)
        )

    else:

        mandatory_coverage = (
            symptom_coverage
        )

    # --------------------------------------------------------
    # Expected symptom fraction
    # --------------------------------------------------------

    expected_fraction = (
        len(expected_symptoms)
        /
        len(observed)
    )

    # --------------------------------------------------------
    # Atypical symptom fraction
    #
    # Occasional + Rare symptoms are atypical
    # relative to the disease profile.
    # --------------------------------------------------------

    atypical_fraction = (
        len(atypical_symptoms)
        /
        len(observed)
    )

    # --------------------------------------------------------
    # Unexplained fraction
    # --------------------------------------------------------

    unexplained_fraction = (
        len(unexplained)
        /
        len(observed)
    )

    # --------------------------------------------------------
    # Compatibility
    #
    # We emphasize:
    #
    #   observed coverage
    #   frequency-adjusted compatibility
    #   similarity
    #
    # This avoids requiring every possible disease symptom
    # to appear in an observed pattern.
    # --------------------------------------------------------

    compatibility = (

        0.35
        * symptom_coverage

        + 0.25
        * frequency_adjusted_coverage

        + 0.20
        * jaccard

        + 0.10
        * profile_coverage

        + 0.10
        * mandatory_coverage
    )

    compatibility_score = round(
        clamp(
            compatibility * 100
        ),
        2
    )

    return {

        "compatibility_score":
            compatibility_score,

        "symptom_coverage":
            round(
                symptom_coverage * 100,
                2
            ),

        "frequency_adjusted_coverage":
            round(
                frequency_adjusted_coverage * 100,
                2
            ),

        "profile_coverage":
            round(
                profile_coverage * 100,
                2
            ),

        "jaccard_similarity":
            round(
                jaccard * 100,
                2
            ),

        "mandatory_coverage":
            round(
                mandatory_coverage * 100,
                2
            ),

        "expected_symptom_fraction":
            round(
                expected_fraction * 100,
                2
            ),

        "atypical_symptom_fraction":
            round(
                atypical_fraction * 100,
                2
            ),

        "unexplained_symptom_fraction":
            round(
                unexplained_fraction * 100,
                2
            ),

        "matched_symptoms":
            sorted(
                matched
            ),

        "expected_symptoms":
            sorted(
                expected_symptoms
            ),

        "atypical_symptoms":
            sorted(
                atypical_symptoms
            ),

        "unexplained_symptoms":
            sorted(
                unexplained
            )
    }


# ============================================================
# EMERGENCE EVIDENCE
# ============================================================

def calculate_emergence_evidence(
    row
):
    """
    Calculate overall emergence evidence from A3.

    Components:

        40% cross-hospital score
        20% positive prevalence growth
        20% persistence
        10% anomaly volume
        10% hospital coverage

    IMPORTANT:
        A3 hospital_coverage is a fraction.

        Example:
            0.9 = 90%

        Therefore it is explicitly multiplied by 100 here.
    """

    cross_hospital_score = safe_float(
        row.get(
            "cross_hospital_score",
            0
        )
    )

    prevalence_growth = safe_float(
        row.get(
            "mean_prevalence_growth",
            0
        )
    )

    persistence = safe_float(
        row.get(
            "mean_persistence_weeks",
            0
        )
    )

    anomalies = safe_float(
        row.get(
            "total_anomalous_occurrences",
            0
        )
    )

    hospital_coverage_fraction = safe_float(
        row.get(
            "hospital_coverage",
            0
        )
    )

    # --------------------------------------------------------
    # Growth
    #
    # 100% growth or greater = maximum.
    # Negative growth = zero emergence contribution.
    # --------------------------------------------------------

    positive_growth = max(
        0.0,
        prevalence_growth
    )

    growth_score = clamp(
        positive_growth * 100,
        0,
        100
    )

    # --------------------------------------------------------
    # Persistence
    #
    # 6+ weeks = maximum.
    # --------------------------------------------------------

    persistence_score = clamp(
        persistence / 6.0 * 100,
        0,
        100
    )

    # --------------------------------------------------------
    # Anomaly volume
    #
    # 100+ anomalous occurrences = maximum.
    # --------------------------------------------------------

    anomaly_score = clamp(
        anomalies / 100.0 * 100,
        0,
        100
    )

    # --------------------------------------------------------
    # Hospital coverage
    #
    # 0.9 -> 90
    # --------------------------------------------------------

    coverage_score = clamp(
        hospital_coverage_fraction * 100,
        0,
        100
    )

    # --------------------------------------------------------
    # Combined emergence evidence
    # --------------------------------------------------------

    emergence_evidence = (

        0.40
        * cross_hospital_score

        + 0.20
        * growth_score

        + 0.20
        * persistence_score

        + 0.10
        * anomaly_score

        + 0.10
        * coverage_score
    )

    return round(
        clamp(
            emergence_evidence
        ),
        2
    )


# ============================================================
# KNOWN-DISEASE EMERGING SCORE
# ============================================================

def calculate_known_disease_emerging_score(
    compatibility_score,
    atypical_fraction,
    emergence_evidence,
    prevalence_growth,
    hospitals_affected,
    persistence_weeks
):
    """
    Calculate how strongly a known disease-compatible pattern
    should be considered an emerging/atypical surveillance signal.

    This is different from novelty.

    A pattern can be:
        highly compatible with Dengue
        AND
        strongly emerging across hospitals.

    That should produce a high known-disease emerging score
    without falsely calling it a novel pathogen.
    """

    # --------------------------------------------------------
    # Atypical component
    # --------------------------------------------------------

    atypical_score = clamp(
        atypical_fraction,
        0,
        100
    )

    # --------------------------------------------------------
    # Growth
    # --------------------------------------------------------

    growth_score = clamp(
        max(
            0.0,
            prevalence_growth
        ) * 100,
        0,
        100
    )

    # --------------------------------------------------------
    # Hospital spread
    #
    # 10 hospitals = maximum.
    # --------------------------------------------------------

    spread_score = clamp(
        hospitals_affected
        / 10.0
        * 100,
        0,
        100
    )

    # --------------------------------------------------------
    # Persistence
    # --------------------------------------------------------

    persistence_score = clamp(
        persistence_weeks
        / 6.0
        * 100,
        0,
        100
    )

    # --------------------------------------------------------
    # Compatibility factor
    #
    # We require the pattern to still reasonably fit a
    # known disease before calling it a known-disease
    # emerging signal.
    # --------------------------------------------------------

    compatibility_factor = clamp(
        compatibility_score,
        0,
        100
    )

    # --------------------------------------------------------
    # Emerging score
    #
    # 35% A3 emergence evidence
    # 20% growth
    # 15% hospital spread
    # 15% persistence
    # 15% atypicality
    #
    # Compatibility acts as a gate/factor rather than
    # directly dominating the emergence score.
    # --------------------------------------------------------

    base_score = (

        0.35
        * emergence_evidence

        + 0.20
        * growth_score

        + 0.15
        * spread_score

        + 0.15
        * persistence_score

        + 0.15
        * atypical_score
    )

    compatibility_factor = (
        0.70
        + 0.30
        * (
            compatibility_factor
            / 100
        )
    )

    score = (
        base_score
        * compatibility_factor
    )

    return round(
        clamp(score),
        2
    )


# ============================================================
# NOVELTY SCORE
# ============================================================

def calculate_novelty_score(
    best_compatibility,
    unexplained_fraction,
    emergence_evidence
):
    """
    Novelty score is reserved for patterns poorly explained
    by known diseases.

    Components:

        45% compatibility gap
        35% unexplained symptoms
        20% emergence evidence
    """

    compatibility_gap = (
        100
        - best_compatibility
    )

    novelty = (

        0.45
        * compatibility_gap

        + 0.35
        * unexplained_fraction

        + 0.20
        * emergence_evidence
    )

    return round(
        clamp(novelty),
        2
    )


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_inference(
    compatibility_score,
    expected_fraction,
    atypical_fraction,
    unexplained_fraction,
    known_disease_emerging_score,
    emergence_evidence,
    hospitals_affected,
    persistence_weeks
):
    """
    Classify A4 signal.

    Hierarchy:

        1. Strong known disease expected pattern
        2. Known disease emerging pattern
        3. Known disease atypical pattern
        4. Unexplained emerging pattern
        5. Insufficient evidence
    """

    # ========================================================
    # Strong expected known-disease presentation
    # ========================================================

    if (
        compatibility_score >= 70
        and expected_fraction >= 60
        and unexplained_fraction <= 10
        and known_disease_emerging_score < 50
    ):

        return (
            "KNOWN_DISEASE_EXPECTED"
        )

    # ========================================================
    # Known disease with strong emerging behavior
    # ========================================================

    if (
        compatibility_score >= 55
        and known_disease_emerging_score >= 55
        and hospitals_affected >= 2
    ):

        return (
            "KNOWN_DISEASE_EMERGING"
        )

    # ========================================================
    # Known disease with atypical symptoms
    # ========================================================

    if (
        compatibility_score >= 55
        and atypical_fraction >= 25
    ):

        return (
            "KNOWN_DISEASE_ATYPICAL"
        )

    # ========================================================
    # Unexplained emerging pattern
    #
    # Requires all of:
    #
    #   low compatibility
    #   strong emergence
    #   multiple hospitals
    #   persistence
    # ========================================================

    if (
        compatibility_score < 45
        and emergence_evidence >= 60
        and hospitals_affected >= 3
        and persistence_weeks >= 2
    ):

        return (
            "UNEXPLAINED_EMERGING_PATTERN"
        )

    # --------------------------------------------------------
    # Secondary unexplained rule
    # --------------------------------------------------------

    if (
        compatibility_score < 55
        and unexplained_fraction >= 30
        and emergence_evidence >= 50
        and hospitals_affected >= 2
    ):

        return (
            "UNEXPLAINED_EMERGING_PATTERN"
        )

    # ========================================================
    # Insufficient evidence
    # ========================================================

    return (
        "INSUFFICIENT_EVIDENCE"
    )


# ============================================================
# ALERT LEVEL
# ============================================================

def determine_alert_level(
    inference_category,
    known_disease_emerging_score,
    novelty_score,
    emergence_evidence,
    hospitals_affected
):
    """
    Determine surveillance alert level.

    This is a public-health surveillance priority,
    NOT clinical severity.
    """

    # --------------------------------------------------------
    # Unexplained emerging
    # --------------------------------------------------------

    if (
        inference_category
        == "UNEXPLAINED_EMERGING_PATTERN"
    ):

        if (
            novelty_score >= 75
            and emergence_evidence >= 70
            and hospitals_affected >= 5
        ):

            return "CRITICAL"

        if (
            novelty_score >= 60
            and emergence_evidence >= 55
            and hospitals_affected >= 3
        ):

            return "HIGH"

        if (
            novelty_score >= 45
            and hospitals_affected >= 2
        ):

            return "MODERATE"

        return "LOW"

    # --------------------------------------------------------
    # Known disease emerging
    # --------------------------------------------------------

    if (
        inference_category
        == "KNOWN_DISEASE_EMERGING"
    ):

        if (
            known_disease_emerging_score >= 70
            and hospitals_affected >= 5
        ):

            return "HIGH"

        if (
            known_disease_emerging_score >= 55
            and hospitals_affected >= 3
        ):

            return "MODERATE"

        return "LOW"

    # --------------------------------------------------------
    # Known disease atypical
    # --------------------------------------------------------

    if (
        inference_category
        == "KNOWN_DISEASE_ATYPICAL"
    ):

        if (
            known_disease_emerging_score >= 65
            and hospitals_affected >= 4
        ):

            return "HIGH"

        if known_disease_emerging_score >= 45:

            return "MODERATE"

        return "LOW"

    # --------------------------------------------------------
    # Expected known disease
    # --------------------------------------------------------

    if (
        inference_category
        == "KNOWN_DISEASE_EXPECTED"
    ):

        if (
            emergence_evidence >= 75
            and hospitals_affected >= 7
        ):

            return "MODERATE"

        return "LOW"

    return "LOW"


# ============================================================
# EXPLANATION
# ============================================================

def generate_explanation(
    disease_name,
    pathogen_type,
    compatibility_score,
    expected_fraction,
    atypical_fraction,
    unexplained_fraction,
    expected_symptoms,
    atypical_symptoms,
    unexplained_symptoms,
    hospitals_affected,
    spread_level,
    emergence_evidence,
    known_disease_emerging_score,
    inference_category
):
    """
    Generate a human-readable surveillance explanation.
    """

    expected_text = ", ".join(
        symptom.title()
        for symptom
        in expected_symptoms[:6]
    )

    atypical_text = ", ".join(
        symptom.title()
        for symptom
        in atypical_symptoms[:6]
    )

    unexplained_text = ", ".join(
        symptom.title()
        for symptom
        in unexplained_symptoms[:6]
    )

    # ========================================================
    # EXPECTED KNOWN DISEASE
    # ========================================================

    if (
        inference_category
        == "KNOWN_DISEASE_EXPECTED"
    ):

        explanation = (
            f"The observed pattern is strongly compatible "
            f"with {disease_name} "
            f"(compatibility {compatibility_score:.1f}%). "
        )

        if pathogen_type:

            explanation += (
                f"The known pathogen type is "
                f"{pathogen_type.lower()}. "
            )

        if expected_text:

            explanation += (
                f"Expected symptoms include "
                f"{expected_text}. "
            )

        explanation += (
            f"The pattern affects "
            f"{hospitals_affected} hospital(s), "
            f"but current evidence does not indicate "
            f"a strong atypical or novel signal."
        )

        return explanation

    # ========================================================
    # KNOWN DISEASE EMERGING
    # ========================================================

    if (
        inference_category
        == "KNOWN_DISEASE_EMERGING"
    ):

        explanation = (
            f"The pattern is compatible with "
            f"{disease_name} "
            f"(compatibility {compatibility_score:.1f}%) "
            f"and also shows meaningful emerging behavior "
            f"across {hospitals_affected} hospital(s). "
            f"The known-disease emerging score is "
            f"{known_disease_emerging_score:.1f}/100 "
            f"and overall emergence evidence is "
            f"{emergence_evidence:.1f}/100. "
        )

        if expected_text:

            explanation += (
                f"Expected components include "
                f"{expected_text}. "
            )

        explanation += (
            "This should be monitored as an emerging "
            "known-disease pattern rather than interpreted "
            "as evidence of a novel pathogen."
        )

        return explanation

    # ========================================================
    # KNOWN DISEASE ATYPICAL
    # ========================================================

    if (
        inference_category
        == "KNOWN_DISEASE_ATYPICAL"
    ):

        explanation = (
            f"The pattern partially matches "
            f"{disease_name} "
            f"(compatibility {compatibility_score:.1f}%), "
            f"but {atypical_fraction:.1f}% of observed "
            f"symptoms are occasional or rare within the "
            f"known disease profile. "
        )

        if atypical_text:

            explanation += (
                f"Atypical components include "
                f"{atypical_text}. "
            )

        explanation += (
            f"The pattern affects "
            f"{hospitals_affected} hospital(s) and has "
            f"emergence evidence of "
            f"{emergence_evidence:.1f}/100. "
            "This warrants continued surveillance but "
            "does not establish a new pathogen."
        )

        return explanation

    # ========================================================
    # UNEXPLAINED EMERGING
    # ========================================================

    if (
        inference_category
        == "UNEXPLAINED_EMERGING_PATTERN"
    ):

        explanation = (
            f"The pattern has limited compatibility with "
            f"the known disease profiles "
            f"(best compatibility "
            f"{compatibility_score:.1f}%) and shows strong "
            f"emergence evidence "
            f"({emergence_evidence:.1f}/100) across "
            f"{hospitals_affected} hospital(s). "
        )

        if unexplained_text:

            explanation += (
                f"Unexplained components include "
                f"{unexplained_text}. "
            )

        explanation += (
            "This represents a potential unexplained "
            "emerging surveillance signal requiring "
            "further clinical, epidemiological and "
            "laboratory investigation. "
            "It is not confirmation of a new pathogen."
        )

        return explanation

    # ========================================================
    # INSUFFICIENT
    # ========================================================

    return (
        f"The pattern has insufficient evidence for a "
        f"strong emerging-disease interpretation. "
        f"The closest known disease is {disease_name} "
        f"with compatibility of "
        f"{compatibility_score:.1f}%, while the pattern "
        f"affects {hospitals_affected} hospital(s). "
        f"Continued monitoring can determine whether "
        f"the signal becomes persistent or widespread."
    )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_emerging_disease_patterns():

    print("=" * 80)
    print("A4 - EMERGING DISEASE / PATHOGEN INFERENCE")
    print("=" * 80)

    # ========================================================
    # LOAD A3
    # ========================================================

    if not A3_FILE.exists():

        raise FileNotFoundError(
            f"\nA3 output not found:\n"
            f"{A3_FILE}\n\n"
            "Run cross_hospital_patterns.py first."
        )

    a3 = pd.read_csv(
        A3_FILE,
        keep_default_na=False
    )

    if a3.empty:

        print(
            "\nA3 output is empty."
        )

        return pd.DataFrame()

    print()
    print(
        f"A3 patterns loaded: "
        f"{len(a3)}"
    )

    # ========================================================
    # VALIDATE A3
    # ========================================================

    required_a3_columns = {

        "symptom_pattern",

        "hospitals_affected",

        "hospital_coverage",

        "total_anomalous_occurrences",

        "mean_current_prevalence",

        "max_current_prevalence",

        "mean_prevalence_growth",

        "max_prevalence_growth",

        "mean_persistence_weeks",

        "max_persistence_weeks",

        "mean_emergence_score",

        "max_emergence_score",

        "spread_level",

        "cross_hospital_score",

        "alert_level"
    }

    missing = (
        required_a3_columns
        - set(a3.columns)
    )

    if missing:

        raise ValueError(
            "A3 output is missing required "
            f"columns: {missing}"
        )

    # ========================================================
    # LOAD KNOWLEDGE
    # ========================================================

    (
        disease_master,
        disease_symptom_mapping,
        symptom_master
    ) = load_knowledge_tables()

    # ========================================================
    # BUILD PROFILES
    # ========================================================

    disease_profiles = (
        build_disease_profiles(
            disease_master,
            disease_symptom_mapping,
            symptom_master
        )
    )

    if not disease_profiles:

        raise ValueError(
            "No disease profiles were constructed."
        )

    print()
    print(
        f"Known disease profiles: "
        f"{len(disease_profiles)}"
    )

    # ========================================================
    # ANALYZE EACH PATTERN
    # ========================================================

    results = []

    for _, row in a3.iterrows():

        pattern = clean_text(
            row["symptom_pattern"]
        )

        observed_symptoms = (
            parse_symptom_pattern(
                pattern
            )
        )

        if not observed_symptoms:

            continue

        # ----------------------------------------------------
        # Compare with every known disease
        # ----------------------------------------------------

        disease_results = []

        for (
            disease_id,
            profile
        ) in disease_profiles.items():

            compatibility = (
                calculate_disease_compatibility(
                    observed_symptoms,
                    profile
                )
            )

            disease_results.append({

                "disease_id":
                    disease_id,

                "disease_name":
                    profile[
                        "disease_name"
                    ],

                "pathogen_type":
                    profile[
                        "pathogen_type"
                    ],

                "disease_category":
                    profile[
                        "disease_category"
                    ],

                "outbreak_potential":
                    profile[
                        "outbreak_potential"
                    ],

                **compatibility
            })

        # ----------------------------------------------------
        # Rank diseases
        # ----------------------------------------------------

        disease_results.sort(
            key=lambda x: (

                x[
                    "compatibility_score"
                ],

                x[
                    "frequency_adjusted_coverage"
                ],

                x[
                    "symptom_coverage"
                ],

                x[
                    "jaccard_similarity"
                ]
            ),
            reverse=True
        )

        best = disease_results[0]

        second_best = (
            disease_results[1]
            if len(disease_results) > 1
            else None
        )

        # ====================================================
        # A3 METRICS
        # ====================================================

        hospitals_affected = int(
            safe_float(
                row[
                    "hospitals_affected"
                ]
            )
        )

        hospital_coverage_fraction = (
            safe_float(
                row[
                    "hospital_coverage"
                ]
            )
        )

        total_anomalies = int(
            safe_float(
                row[
                    "total_anomalous_occurrences"
                ]
            )
        )

        mean_current_prevalence = safe_float(
            row[
                "mean_current_prevalence"
            ]
        )

        max_current_prevalence = safe_float(
            row[
                "max_current_prevalence"
            ]
        )

        mean_prevalence_growth = safe_float(
            row[
                "mean_prevalence_growth"
            ]
        )

        max_prevalence_growth = safe_float(
            row[
                "max_prevalence_growth"
            ]
        )

        mean_persistence_weeks = safe_float(
            row[
                "mean_persistence_weeks"
            ]
        )

        max_persistence_weeks = safe_float(
            row[
                "max_persistence_weeks"
            ]
        )

        mean_emergence_score = safe_float(
            row[
                "mean_emergence_score"
            ]
        )

        max_emergence_score = safe_float(
            row[
                "max_emergence_score"
            ]
        )

        spread_level = clean_text(
            row[
                "spread_level"
            ]
        )

        cross_hospital_score = safe_float(
            row[
                "cross_hospital_score"
            ]
        )

        # ====================================================
        # EMERGENCE EVIDENCE
        # ====================================================

        emergence_evidence = (
            calculate_emergence_evidence(
                row
            )
        )

        # ====================================================
        # KNOWN DISEASE EMERGING SCORE
        # ====================================================

        known_disease_emerging_score = (
            calculate_known_disease_emerging_score(

                compatibility_score=
                    best[
                        "compatibility_score"
                    ],

                atypical_fraction=
                    best[
                        "atypical_symptom_fraction"
                    ],

                emergence_evidence=
                    emergence_evidence,

                prevalence_growth=
                    mean_prevalence_growth,

                hospitals_affected=
                    hospitals_affected,

                persistence_weeks=
                    mean_persistence_weeks
            )
        )

        # ====================================================
        # NOVELTY
        # ====================================================

        novelty_score = (
            calculate_novelty_score(

                best_compatibility=
                    best[
                        "compatibility_score"
                    ],

                unexplained_fraction=
                    best[
                        "unexplained_symptom_fraction"
                    ],

                emergence_evidence=
                    emergence_evidence
            )
        )

        # ====================================================
        # CLASSIFICATION
        # ====================================================

        inference_category = (
            classify_inference(

                compatibility_score=
                    best[
                        "compatibility_score"
                    ],

                expected_fraction=
                    best[
                        "expected_symptom_fraction"
                    ],

                atypical_fraction=
                    best[
                        "atypical_symptom_fraction"
                    ],

                unexplained_fraction=
                    best[
                        "unexplained_symptom_fraction"
                    ],

                known_disease_emerging_score=
                    known_disease_emerging_score,

                emergence_evidence=
                    emergence_evidence,

                hospitals_affected=
                    hospitals_affected,

                persistence_weeks=
                    mean_persistence_weeks
            )
        )

        # ====================================================
        # ALERT
        # ====================================================

        alert_level = (
            determine_alert_level(

                inference_category=
                    inference_category,

                known_disease_emerging_score=
                    known_disease_emerging_score,

                novelty_score=
                    novelty_score,

                emergence_evidence=
                    emergence_evidence,

                hospitals_affected=
                    hospitals_affected
            )
        )

        # ====================================================
        # EXPLANATION
        # ====================================================

        explanation = (
            generate_explanation(

                disease_name=
                    best[
                        "disease_name"
                    ],

                pathogen_type=
                    best[
                        "pathogen_type"
                    ],

                compatibility_score=
                    best[
                        "compatibility_score"
                    ],

                expected_fraction=
                    best[
                        "expected_symptom_fraction"
                    ],

                atypical_fraction=
                    best[
                        "atypical_symptom_fraction"
                    ],

                unexplained_fraction=
                    best[
                        "unexplained_symptom_fraction"
                    ],

                expected_symptoms=
                    best[
                        "expected_symptoms"
                    ],

                atypical_symptoms=
                    best[
                        "atypical_symptoms"
                    ],

                unexplained_symptoms=
                    best[
                        "unexplained_symptoms"
                    ],

                hospitals_affected=
                    hospitals_affected,

                spread_level=
                    spread_level,

                emergence_evidence=
                    emergence_evidence,

                known_disease_emerging_score=
                    known_disease_emerging_score,

                inference_category=
                    inference_category
            )
        )

        # ====================================================
        # STORE RESULT
        # ====================================================

        results.append({

            # ------------------------------------------------
            # Pattern
            # ------------------------------------------------

            "symptom_pattern":
                pattern,

            # ------------------------------------------------
            # A3 cross-hospital evidence
            # ------------------------------------------------

            "hospitals_affected":
                hospitals_affected,

            "hospital_coverage":
                round(
                    hospital_coverage_fraction,
                    4
                ),

            "total_anomalous_occurrences":
                total_anomalies,

            "spread_level":
                spread_level,

            "cross_hospital_score":
                round(
                    cross_hospital_score,
                    2
                ),

            # ------------------------------------------------
            # A3 prevalence
            # ------------------------------------------------

            "mean_current_prevalence":
                round(
                    mean_current_prevalence,
                    6
                ),

            "max_current_prevalence":
                round(
                    max_current_prevalence,
                    6
                ),

            "mean_prevalence_growth":
                round(
                    mean_prevalence_growth,
                    4
                ),

            "max_prevalence_growth":
                round(
                    max_prevalence_growth,
                    4
                ),

            # ------------------------------------------------
            # Persistence
            # ------------------------------------------------

            "mean_persistence_weeks":
                round(
                    mean_persistence_weeks,
                    2
                ),

            "max_persistence_weeks":
                round(
                    max_persistence_weeks,
                    2
                ),

            # ------------------------------------------------
            # Emergence
            # ------------------------------------------------

            "mean_emergence_score":
                round(
                    mean_emergence_score,
                    2
                ),

            "max_emergence_score":
                round(
                    max_emergence_score,
                    2
                ),

            "emergence_evidence_score":
                emergence_evidence,

            # ------------------------------------------------
            # Best disease
            # ------------------------------------------------

            "best_matching_disease_id":
                best[
                    "disease_id"
                ],

            "best_matching_disease":
                best[
                    "disease_name"
                ],

            "best_matching_pathogen_type":
                best[
                    "pathogen_type"
                ],

            "best_matching_disease_category":
                best[
                    "disease_category"
                ],

            "best_matching_outbreak_potential":
                best[
                    "outbreak_potential"
                ],

            # ------------------------------------------------
            # Compatibility
            # ------------------------------------------------

            "disease_compatibility_score":
                best[
                    "compatibility_score"
                ],

            "symptom_coverage":
                best[
                    "symptom_coverage"
                ],

            "frequency_adjusted_coverage":
                best[
                    "frequency_adjusted_coverage"
                ],

            "disease_profile_coverage":
                best[
                    "profile_coverage"
                ],

            "jaccard_similarity":
                best[
                    "jaccard_similarity"
                ],

            "mandatory_symptom_coverage":
                best[
                    "mandatory_coverage"
                ],

            # ------------------------------------------------
            # Expected / atypical
            # ------------------------------------------------

            "expected_symptom_fraction":
                best[
                    "expected_symptom_fraction"
                ],

            "atypical_symptom_fraction":
                best[
                    "atypical_symptom_fraction"
                ],

            "unexplained_symptom_fraction":
                best[
                    "unexplained_symptom_fraction"
                ],

            # ------------------------------------------------
            # Explainability
            # ------------------------------------------------

            "matched_symptoms":
                " + ".join(
                    best[
                        "matched_symptoms"
                    ]
                ),

            "expected_symptoms":
                " + ".join(
                    best[
                        "expected_symptoms"
                    ]
                ),

            "atypical_symptoms":
                " + ".join(
                    best[
                        "atypical_symptoms"
                    ]
                ),

            "unexplained_symptoms":
                " + ".join(
                    best[
                        "unexplained_symptoms"
                    ]
                ),

            # ------------------------------------------------
            # Second-best disease
            # ------------------------------------------------

            "second_matching_disease":
                (
                    second_best[
                        "disease_name"
                    ]
                    if second_best
                    else ""
                ),

            "second_matching_pathogen_type":
                (
                    second_best[
                        "pathogen_type"
                    ]
                    if second_best
                    else ""
                ),

            "second_disease_compatibility_score":
                (
                    second_best[
                        "compatibility_score"
                    ]
                    if second_best
                    else 0.0
                ),

            # ------------------------------------------------
            # Final A4 scores
            # ------------------------------------------------

            "known_disease_emerging_score":
                known_disease_emerging_score,

            "novelty_score":
                novelty_score,

            # ------------------------------------------------
            # Final interpretation
            # ------------------------------------------------

            "inference_category":
                inference_category,

            "alert_level":
                alert_level,

            "explanation":
                explanation
        })

    # ========================================================
    # DATAFRAME
    # ========================================================

    result_df = pd.DataFrame(
        results
    )

    if result_df.empty:

        print()
        print(
            "No A4 results generated."
        )

        return result_df

    # ========================================================
    # SORT
    # ========================================================

    # Known-disease emerging patterns should be easy to find,
    # while unexplained high-novelty signals remain prominent.

    result_df = (
        result_df
        .sort_values(
            by=[
                "known_disease_emerging_score",
                "novelty_score",
                "cross_hospital_score"
            ],
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

    # ========================================================
    # SAVE
    # ========================================================

    EMERGING_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print("A4 COMPLETE")
    print("=" * 80)

    print()
    print(
        f"Patterns analyzed: "
        f"{len(result_df)}"
    )

    # --------------------------------------------------------
    # Categories
    # --------------------------------------------------------

    print()
    print(
        "Inference categories:"
    )

    print(
        result_df[
            "inference_category"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Alerts
    # --------------------------------------------------------

    print()
    print(
        "Alert levels:"
    )

    print(
        result_df[
            "alert_level"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Diseases
    # --------------------------------------------------------

    print()
    print(
        "Best matching diseases:"
    )

    print(
        result_df[
            "best_matching_disease"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Pathogens
    # --------------------------------------------------------

    print()
    print(
        "Best matching pathogen types:"
    )

    print(
        result_df[
            "best_matching_pathogen_type"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Top known-disease emerging signals
    # --------------------------------------------------------

    print()
    print(
        "Top known-disease emerging signals:"
    )

    print()

    top_columns = [

        "symptom_pattern",

        "best_matching_disease",

        "disease_compatibility_score",

        "atypical_symptom_fraction",

        "hospitals_affected",

        "mean_prevalence_growth",

        "mean_persistence_weeks",

        "emergence_evidence_score",

        "known_disease_emerging_score",

        "inference_category",

        "alert_level"
    ]

    print(
        result_df[
            top_columns
        ]
        .head(15)
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Potential unexplained signals
    # --------------------------------------------------------

    unexplained = result_df[
        result_df[
            "inference_category"
        ]
        == "UNEXPLAINED_EMERGING_PATTERN"
    ]

    print()
    print(
        "Potential unexplained emerging patterns:"
    )

    if unexplained.empty:

        print(
            "None identified under current thresholds."
        )

    else:

        unexplained_columns = [

            "symptom_pattern",

            "best_matching_disease",

            "disease_compatibility_score",

            "unexplained_symptom_fraction",

            "hospitals_affected",

            "emergence_evidence_score",

            "novelty_score",

            "alert_level"
        ]

        print(
            unexplained[
                unexplained_columns
            ]
            .head(10)
            .to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print()
    print(
        f"Output saved to:\n"
        f"{OUTPUT_FILE}"
    )

    return result_df


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    analyze_emerging_disease_patterns()
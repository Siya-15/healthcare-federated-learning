from pathlib import Path
import sys

import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import KernelDensity
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# PATHS
# ============================================================

ML_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ML_DIR.parent

EMERGING_DIR = ML_DIR / "emerging_symptoms"

A6_FILE = (
    EMERGING_DIR
    / "emerging_signal_fusion.csv"
)

OUTPUT_FILE = (
    EMERGING_DIR
    / "advanced_symptom_novelty.csv"
)

DATA_DIR = ML_DIR


# ============================================================
# KNOWLEDGE TABLES
# ============================================================

KNOWLEDGE_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "knowledge_tables"
)

DISEASE_MASTER = (
    KNOWLEDGE_DIR
    / "disease_master.csv"
)

DISEASE_SYMPTOM_MAPPING = (
    KNOWLEDGE_DIR
    / "disease_symptom_mapping.csv"
)

SYMPTOM_MASTER = (
    KNOWLEDGE_DIR
    / "symptom_master.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

# Maximum number of PCA components.
MAX_COMPONENTS = 10

# KMeans cluster count.
MIN_CLUSTERS = 2
MAX_CLUSTERS = 8

# KDE bandwidth.
KDE_BANDWIDTH = 0.8

# Novelty thresholds.
LOW_NOVELTY = 35
MODERATE_NOVELTY = 55
HIGH_NOVELTY = 75

# ============================================================
# DISEASE-AWARE NOVELTY CONFIGURATION
# ============================================================

# Expected known-disease patterns should require stronger
# representation novelty before being considered noteworthy.
EXPECTED_PATTERN_FACTOR = 0.45

# Widespread known-disease patterns receive a moderate reduction.
WIDESPREAD_PATTERN_FACTOR = 0.65

# Atypical known-disease patterns retain most representation
# novelty because they are relevant to Objective A.
ATYPICAL_PATTERN_FACTOR = 0.90

# Unexplained emerging patterns retain the full novelty signal.
UNEXPLAINED_PATTERN_FACTOR = 1.00

# Minimum disease-profile similarity considered a strong match.
STRONG_DISEASE_MATCH = 75


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value):

    if pd.isna(value):
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


def clip_score(value):

    return float(
        max(
            0.0,
            min(
                100.0,
                value
            )
        )
    )


# ============================================================
# LOAD DISEASE KNOWLEDGE
# ============================================================

def load_knowledge():

    for path in [
        DISEASE_MASTER,
        DISEASE_SYMPTOM_MAPPING,
        SYMPTOM_MASTER,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Knowledge table not found:\n{path}"
            )

    disease_master = pd.read_csv(
        DISEASE_MASTER,
        keep_default_na=False
    )

    mapping = pd.read_csv(
        DISEASE_SYMPTOM_MAPPING,
        keep_default_na=False
    )

    symptom_master = pd.read_csv(
        SYMPTOM_MASTER,
        keep_default_na=False
    )

    return (
        disease_master,
        mapping,
        symptom_master
    )


# ============================================================
# LOAD A6
# ============================================================

def load_a6():

    if not A6_FILE.exists():

        raise FileNotFoundError(
            f"A6 output not found:\n{A6_FILE}"
        )

    a6 = pd.read_csv(
        A6_FILE,
        keep_default_na=False
    )

    required = [
        "symptom_pattern",
        "best_matching_disease_id",
        "best_matching_disease",
        "inference_category",
    ]

    missing = [
        column
        for column in required
        if column not in a6.columns
    ]

    if missing:

        raise ValueError(
            "A6 is missing required columns:\n"
            + "\n".join(missing)
        )

    return a6


# ============================================================
# LOAD LOCAL HOSPITAL SYMPTOM DATA
# ============================================================

def load_symptom_data():

    files = sorted(
        DATA_DIR.glob(
            "ml_data_H*.csv"
        )
    )

    if not files:

        raise FileNotFoundError(
            f"No hospital ML files found in:\n"
            f"{DATA_DIR}"
        )

    frames = []

    for file in files:

        df = pd.read_csv(
            file,
            keep_default_na=False
        )

        required = [
            "encounter_id",
            "hospital_id",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:

            raise ValueError(
                f"{file.name} is missing:\n"
                + "\n".join(missing)
            )

        frames.append(
            df
        )

    combined = pd.concat(
        frames,
        ignore_index=True
    )

    return combined


# ============================================================
# IDENTIFY SYMPTOM COLUMNS
# ============================================================

def get_symptom_columns(
    df,
    symptom_master
):

    known_symptoms = set(
        symptom_master[
            "symptom_name"
        ]
        .astype(str)
        .tolist()
    )

    columns = [
        column
        for column in df.columns
        if column in known_symptoms
    ]

    if not columns:

        # Fallback:
        # identify binary symptom columns.
        excluded = {
            "encounter_id",
            "hospital_id",
            "patient_id",
            "visit_timestamp",
            "disease_id",
            "severity_id",
        }

        for column in df.columns:

            if column in excluded:
                continue

            values = set(
                pd.to_numeric(
                    df[column],
                    errors="coerce"
                )
                .dropna()
                .unique()
            )

            if values.issubset(
                {0, 1}
            ) and len(values) > 1:

                columns.append(
                    column
                )

    if not columns:

        raise ValueError(
            "No symptom columns could be identified."
        )

    return columns


# ============================================================
# CREATE DISEASE PROFILES
# ============================================================

def build_disease_profiles(
    mapping,
    symptom_master,
    symptom_columns
):

    symptom_id_to_name = dict(
        zip(
            symptom_master[
                "symptom_id"
            ],
            symptom_master[
                "symptom_name"
            ]
        )
    )

    disease_profiles = {}

    for disease_id, group in mapping.groupby(
        "disease_id"
    ):

        profile = np.zeros(
            len(symptom_columns),
            dtype=float
        )

        mapped_symptoms = set()

        for _, row in group.iterrows():

            symptom_name = (
                symptom_id_to_name.get(
                    row["symptom_id"]
                )
            )

            if not symptom_name:
                continue

            mapped_symptoms.add(
                symptom_name
            )

        for index, symptom in enumerate(
            symptom_columns
        ):

            if symptom in mapped_symptoms:

                profile[index] = 1.0

        disease_profiles[
            disease_id
        ] = profile

    return disease_profiles


# ============================================================
# REPRESENTATION
# ============================================================

def create_representation(
    symptom_matrix
):

    # --------------------------------------------------------
    # Remove zero-variance columns
    # --------------------------------------------------------

    variances = np.var(
        symptom_matrix,
        axis=0
    )

    valid_columns = (
        variances > 0
    )

    matrix = symptom_matrix[
        :,
        valid_columns
    ]

    if matrix.shape[1] < 2:

        return matrix, None

    # --------------------------------------------------------
    # Standardization
    # --------------------------------------------------------

    scaler = StandardScaler()

    scaled = scaler.fit_transform(
        matrix
    )

    # --------------------------------------------------------
    # PCA latent representation
    # --------------------------------------------------------

    n_components = min(
        MAX_COMPONENTS,
        scaled.shape[0] - 1,
        scaled.shape[1]
    )

    if n_components < 2:

        return scaled, None

    pca = PCA(
        n_components=n_components,
        random_state=42
    )

    latent = pca.fit_transform(
        scaled
    )

    return latent, pca


# ============================================================
# CLUSTERING
# ============================================================

# Maximum number of samples used for silhouette evaluation.
# This keeps A7 computationally practical while preserving
# clustering over the complete dataset.
SILHOUETTE_SAMPLE_SIZE = 10000


def find_best_kmeans(
    latent
):

    if len(latent) < 10:

        return (
            None,
            None,
            None
        )

    max_k = min(
        MAX_CLUSTERS,
        len(latent) - 1
    )

    if max_k < MIN_CLUSTERS:

        return (
            None,
            None,
            None
        )

    # --------------------------------------------------------
    # Use a representative sample for model selection
    # --------------------------------------------------------

    rng = np.random.default_rng(42)

    sample_size = min(
        SILHOUETTE_SAMPLE_SIZE,
        len(latent)
    )

    sample_indices = rng.choice(
        len(latent),
        size=sample_size,
        replace=False
    )

    silhouette_sample = latent[
        sample_indices
    ]

    print(
        f"Silhouette evaluation sample: "
        f"{sample_size:,} / {len(latent):,}"
    )

    # --------------------------------------------------------
    # Search for best K
    # --------------------------------------------------------

    best_k = None
    best_score = -1

    for k in range(
        MIN_CLUSTERS,
        max_k + 1
    ):

        print(
            f"  Evaluating k={k}..."
        )

        # Fit KMeans on the representative sample.
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10
        )

        sample_labels = model.fit_predict(
            silhouette_sample
        )

        if len(
            np.unique(sample_labels)
        ) < 2:

            continue

        score = silhouette_score(
            silhouette_sample,
            sample_labels
        )

        print(
            f"    Silhouette: {score:.4f}"
        )

        if score > best_score:

            best_score = score
            best_k = k

    # --------------------------------------------------------
    # Refit final model on ALL encounters
    # --------------------------------------------------------

    if best_k is None:

        return (
            None,
            None,
            None
        )

    print(
        f"\nBest k selected: {best_k}"
    )

    print(
        "Fitting final KMeans on all encounters..."
    )

    final_model = KMeans(
        n_clusters=best_k,
        random_state=42,
        n_init=10
    )

    final_model.fit(
        latent
    )

    return (
        final_model,
        best_k,
        best_score
    )


# ============================================================
# DISEASE PROFILE SIMILARITY
# ============================================================

def calculate_disease_similarity(
    symptom_matrix,
    disease_profiles,
    disease_ids
):

    if not disease_profiles:

        return (
            np.zeros(
                len(symptom_matrix)
            ),
            [""] * len(symptom_matrix)
        )

    profile_matrix = np.vstack(
        [
            disease_profiles[
                disease_id
            ]
            for disease_id in disease_ids
        ]
    )

    similarity = cosine_similarity(
        symptom_matrix,
        profile_matrix
    )

    best_indices = np.argmax(
        similarity,
        axis=1
    )

    best_scores = np.max(
        similarity,
        axis=1
    )

    best_diseases = [
        disease_ids[index]
        for index in best_indices
    ]

    return (
        best_scores,
        best_diseases
    )


# ============================================================
# KDE DENSITY
# ============================================================

KDE_SAMPLE_SIZE = 10000


def calculate_density(
    latent
):

    if len(latent) < 5:

        return np.ones(
            len(latent)
        )

    # --------------------------------------------------------
    # Use a representative sample to fit KDE
    # --------------------------------------------------------

    rng = np.random.default_rng(42)

    sample_size = min(
        KDE_SAMPLE_SIZE,
        len(latent)
    )

    sample_indices = rng.choice(
        len(latent),
        size=sample_size,
        replace=False
    )

    kde_sample = latent[
        sample_indices
    ]

    print(
        f"KDE training sample: "
        f"{sample_size:,} / {len(latent):,}"
    )

    # --------------------------------------------------------
    # Fit KDE on representative sample
    # --------------------------------------------------------

    kde = KernelDensity(
        bandwidth=KDE_BANDWIDTH,
        kernel="gaussian"
    )

    kde.fit(
        kde_sample
    )

    # --------------------------------------------------------
    # Score all encounters
    # --------------------------------------------------------

    print(
        "Scoring all encounters with KDE..."
    )

    log_density = kde.score_samples(
        latent
    )

    density = np.exp(
        log_density
    )

    return density


# ============================================================
# NORMALIZE DENSITY
# ============================================================

def density_novelty_score(
    density
):

    if len(density) == 0:

        return np.array([])

    low = np.percentile(
        density,
        5
    )

    high = np.percentile(
        density,
        95
    )

    if high <= low:

        return np.zeros(
            len(density)
        )

    # Lower density = more novel.
    score = (
        1
        -
        (
            density - low
        )
        /
        (
            high - low
        )
    ) * 100

    return np.clip(
        score,
        0,
        100
    )


# ============================================================
# CLUSTER NOVELTY
# ============================================================

def calculate_cluster_novelty(
    latent,
    cluster_model
):

    if cluster_model is None:

        return np.zeros(
            len(latent)
        )

    labels = cluster_model.predict(
        latent
    )

    distances = (
        cluster_model.transform(
            latent
        )
        .min(
            axis=1
        )
    )

    low = np.percentile(
        distances,
        5
    )

    high = np.percentile(
        distances,
        95
    )

    if high <= low:

        return np.zeros(
            len(latent)
        )

    score = (
        distances - low
    ) / (
        high - low
    ) * 100

    return np.clip(
        score,
        0,
        100
    )


# ============================================================
# NOVELTY CLASSIFICATION
# ============================================================

def classify_novelty(
    score
):

    if score >= HIGH_NOVELTY:
        return "HIGH"

    if score >= MODERATE_NOVELTY:
        return "MODERATE"

    if score >= LOW_NOVELTY:
        return "LOW"

    return "MINIMAL"


# ============================================================
# DISEASE-AWARE NOVELTY ADJUSTMENT
# ============================================================

def calculate_disease_aware_novelty(
    representation_novelty,
    disease_similarity,
    inference_category
):

    if pd.isna(representation_novelty):

        return np.nan

    if pd.isna(disease_similarity):

        disease_similarity = 0.0

    disease_similarity = (
        float(disease_similarity)
        * 100
    )

    inference = str(
        inference_category
    ).strip().upper()

    # --------------------------------------------------------
    # Determine contextual factor
    # --------------------------------------------------------

    if inference == "UNEXPLAINED_EMERGING_PATTERN":

        factor = (
            UNEXPLAINED_PATTERN_FACTOR
        )

    elif inference == "KNOWN_DISEASE_ATYPICAL":

        factor = (
            ATYPICAL_PATTERN_FACTOR
        )

    elif inference == "WIDESPREAD_KNOWN_DISEASE_PATTERN":

        factor = (
            WIDESPREAD_PATTERN_FACTOR
        )

    elif inference == "KNOWN_DISEASE_EXPECTED":

        factor = (
            EXPECTED_PATTERN_FACTOR
        )

    else:

        factor = 0.75

    # --------------------------------------------------------
    # Disease mismatch component
    # --------------------------------------------------------

    disease_mismatch = (
        100
        -
        disease_similarity
    )

    # --------------------------------------------------------
    # Combine representation novelty and
    # disease-profile mismatch.
    #
    # Representation novelty remains the primary signal.
    # Disease mismatch provides contextual support.
    # --------------------------------------------------------

    adjusted = (
        representation_novelty
        * 0.70
        +
        disease_mismatch
        * 0.30
    )

    adjusted *= factor

    return clip_score(
        adjusted
    )

# ============================================================
# PATTERN-LEVEL AGGREGATION
# ============================================================

def aggregate_to_patterns(
    encounter_df,
    a6
):

    # --------------------------------------------------------
    # Build lookup for encounter symptom vectors
    # --------------------------------------------------------

    symptom_columns = encounter_df[
        "symptom_columns"
    ].iloc[0]

    # --------------------------------------------------------
    # Match EACH A6 pattern against encounters
    # --------------------------------------------------------

    grouped = []

    for _, a6_row in a6.iterrows():

        pattern = str(
            a6_row["symptom_pattern"]
        ).strip()

        if not pattern:
            continue

        pattern_symptoms = [
            symptom.strip()
            for symptom in pattern.split("+")
        ]

        # Keep only symptoms that actually exist
        # in the current feature matrix.
        pattern_symptoms = [
            symptom
            for symptom in pattern_symptoms
            if symptom in symptom_columns
        ]

        if not pattern_symptoms:
            continue

        # ----------------------------------------------------
        # Find encounters containing ALL symptoms
        # ----------------------------------------------------

        mask = np.ones(
            len(encounter_df),
            dtype=bool
        )

        for symptom in pattern_symptoms:

            mask &= (
                pd.to_numeric(
                    encounter_df[symptom],
                    errors="coerce"
                ).fillna(0).values == 1
            )

        matched = encounter_df.loc[
            mask
        ].copy()

        encounter_count = len(
            matched
        )

        # ----------------------------------------------------
        # Insufficient evidence
        # ----------------------------------------------------

        if encounter_count == 0:

            grouped.append({
                "symptom_pattern":
                    pattern,

                "encounter_count":
                    0,

                "mean_disease_similarity":
                    np.nan,

                "mean_density_novelty":
                    np.nan,

                "mean_cluster_novelty":
                    np.nan,

                "mean_representation_novelty":
                    np.nan,

                "max_representation_novelty":
                    np.nan,

                "best_matching_disease_id":
                    "",

                "high_novelty_encounters":
                    0,

                "moderate_or_high_novelty_encounters":
                    0,

                "a7_evidence_status":
                    "NO_MATCHING_ENCOUNTERS",
            })

            continue

        # ----------------------------------------------------
        # Aggregate representation evidence
        # ----------------------------------------------------

        best_disease_counts = (
            matched[
                "representation_best_disease_id"
            ]
            .value_counts()
        )

        if best_disease_counts.empty:

            best_disease_id = ""

        else:

            best_disease_id = (
                best_disease_counts.index[0]
            )

        grouped.append({
            "symptom_pattern":
                pattern,

            "encounter_count":
                encounter_count,

            "mean_disease_similarity":
                matched[
                    "disease_similarity"
                ].mean(),

            "mean_density_novelty":
                matched[
                    "density_novelty"
                ].mean(),

            "mean_cluster_novelty":
                matched[
                    "cluster_novelty"
                ].mean(),

            "mean_representation_novelty":
                matched[
                    "representation_novelty"
                ].mean(),

            "max_representation_novelty":
                matched[
                    "representation_novelty"
                ].max(),

            "best_matching_disease_id":
                best_disease_id,

            "high_novelty_encounters":
                int(
                    (
                        matched[
                            "representation_novelty"
                        ] >= HIGH_NOVELTY
                    ).sum()
                ),

            "moderate_or_high_novelty_encounters":
                int(
                    (
                        matched[
                            "representation_novelty"
                        ] >= MODERATE_NOVELTY
                    ).sum()
                ),

            "a7_evidence_status":
                "SUFFICIENT_MATCHING_ENCOUNTERS",
        })

    result = pd.DataFrame(
        grouped
    )

    # --------------------------------------------------------
    # Merge A6 information
    # --------------------------------------------------------

    result = result.merge(
        a6,
        on="symptom_pattern",
        how="left",
        suffixes=(
            "",
            "_a6"
        )
    )

        # --------------------------------------------------------
    # Raw representation novelty
    # --------------------------------------------------------

    result[
        "a7_raw_novelty_score"
    ] = np.nan

    valid = (
        result[
            "a7_evidence_status"
        ]
        ==
        "SUFFICIENT_MATCHING_ENCOUNTERS"
    )

    result.loc[
        valid,
        "a7_raw_novelty_score"
    ] = (
        result.loc[
            valid,
            "mean_density_novelty"
        ]
        * 0.50

        +

        result.loc[
            valid,
            "mean_cluster_novelty"
        ]
        * 0.50
    ).clip(
        0,
        100
    )

    # --------------------------------------------------------
    # Disease-aware A7 novelty
    # --------------------------------------------------------

    result[
        "a7_novelty_score"
    ] = result.apply(
        lambda row:
            calculate_disease_aware_novelty(
                row[
                    "a7_raw_novelty_score"
                ],
                row[
                    "mean_disease_similarity"
                ],
                row[
                    "inference_category"
                ]
            ),
        axis=1
    )

    result[
        "a7_novelty_score"
    ] = result[
        "a7_novelty_score"
    ].round(2)

    # --------------------------------------------------------
    # Novelty classification
    # --------------------------------------------------------

    result[
        "a7_novelty_level"
    ] = "INSUFFICIENT_EVIDENCE"

    result.loc[
        valid,
        "a7_novelty_level"
    ] = result.loc[
        valid,
        "a7_novelty_score"
    ].apply(
        classify_novelty
    )

    # --------------------------------------------------------
    # A7 interpretation
    # --------------------------------------------------------

    def interpretation(row):

        if (
            row[
                "a7_evidence_status"
            ]
            !=
            "SUFFICIENT_MATCHING_ENCOUNTERS"
        ):

            return (
                "INSUFFICIENT_REPRESENTATION_EVIDENCE"
            )

        novelty = row[
            "a7_novelty_score"
        ]

        disease_similarity = (
            row[
                "mean_disease_similarity"
            ]
            * 100
        )

        inference = str(
            row[
                "inference_category"
            ]
        ).upper()

        # ----------------------------------------------------
        # Strongest Objective-A case
        # ----------------------------------------------------

        if (
            inference
            ==
            "UNEXPLAINED_EMERGING_PATTERN"
            and novelty >= HIGH_NOVELTY
        ):

            return (
                "HIGH_NOVELTY_UNEXPLAINED_PATTERN"
            )

        # ----------------------------------------------------
        # Atypical established disease
        # ----------------------------------------------------

        if (
            inference
            ==
            "KNOWN_DISEASE_ATYPICAL"
            and novelty >= HIGH_NOVELTY
        ):

            return (
                "HIGH_NOVELTY_ATYPICAL_DISEASE_PATTERN"
            )

        if (
            inference
            ==
            "KNOWN_DISEASE_ATYPICAL"
            and novelty >= MODERATE_NOVELTY
        ):

            return (
                "MODERATE_NOVELTY_ATYPICAL_DISEASE_PATTERN"
            )

        # ----------------------------------------------------
        # Expected disease patterns
        # ----------------------------------------------------

        if (
            inference
            ==
            "KNOWN_DISEASE_EXPECTED"
            and disease_similarity >= STRONG_DISEASE_MATCH
        ):

            if novelty >= HIGH_NOVELTY:

                return (
                    "HIGH_REPRESENTATION_NOVELTY_BUT_ESTABLISHED_DISEASE"
                )

            if novelty >= MODERATE_NOVELTY:

                return (
                    "MODERATE_REPRESENTATION_NOVELTY_BUT_ESTABLISHED_DISEASE"
                )

            return (
                "CONSISTENT_WITH_ESTABLISHED_DISEASE"
            )

        # ----------------------------------------------------
        # Weak disease match
        # ----------------------------------------------------

        if (
            novelty >= MODERATE_NOVELTY
            and disease_similarity < 50
        ):

            return (
                "MODERATE_NOVELTY_WEAK_DISEASE_MATCH"
            )

        # ----------------------------------------------------
        # Generic representation novelty
        # ----------------------------------------------------

        if novelty >= HIGH_NOVELTY:

            return (
                "HIGH_REPRESENTATION_NOVELTY"
            )

        if novelty >= MODERATE_NOVELTY:

            return (
                "MODERATE_REPRESENTATION_NOVELTY"
            )

        if disease_similarity >= STRONG_DISEASE_MATCH:

            return (
                "STRONG_MATCH_TO_ESTABLISHED_PROFILE"
            )

        return (
            "CONSISTENT_WITH_ESTABLISHED_PATTERNS"
        )

    result[
        "a7_interpretation"
    ] = result.apply(
        interpretation,
        axis=1
    )

    return result

# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("A7 - ADVANCED SYMPTOM REPRESENTATION & NOVELTY")
    print("=" * 80)

    # --------------------------------------------------------
    # Load A6
    # --------------------------------------------------------

    print(
        "\nLoading A6 signal-fusion output..."
    )

    a6 = load_a6()

    print(
        f"A6 patterns loaded: "
        f"{len(a6)}"
    )

    # --------------------------------------------------------
    # Load knowledge
    # --------------------------------------------------------

    print(
        "\nLoading disease knowledge..."
    )

    (
        disease_master,
        mapping,
        symptom_master
    ) = load_knowledge()

    print(
        f"Disease records          : "
        f"{len(disease_master)}"
    )

    print(
        f"Disease-symptom mappings : "
        f"{len(mapping)}"
    )

    print(
        f"Symptom records          : "
        f"{len(symptom_master)}"
    )

    # --------------------------------------------------------
    # Load ML data
    # --------------------------------------------------------

    print(
        "\nLoading hospital symptom data..."
    )

    data = load_symptom_data()

    print(
        f"Encounter records loaded: "
        f"{len(data):,}"
    )

    # --------------------------------------------------------
    # Identify symptoms
    # --------------------------------------------------------

    symptom_columns = get_symptom_columns(
        data,
        symptom_master
    )

    print(
        f"Symptom features: "
        f"{len(symptom_columns)}"
    )

    # --------------------------------------------------------
    # Build matrix
    # --------------------------------------------------------

    symptom_matrix = (
        data[
            symptom_columns
        ]
        .apply(
            pd.to_numeric,
            errors="coerce"
        )
        .fillna(0)
        .astype(float)
        .values
    )

    # --------------------------------------------------------
    # Representation
    # --------------------------------------------------------

    print(
        "\nCreating latent symptom representation..."
    )

    latent, pca = create_representation(
        symptom_matrix
    )

    print(
        f"Latent dimensions: "
        f"{latent.shape[1]}"
    )

    if pca is not None:

        explained = (
            pca.explained_variance_ratio_
            .sum()
            * 100
        )

        print(
            f"Variance explained: "
            f"{explained:.2f}%"
        )

    # --------------------------------------------------------
    # Clustering
    # --------------------------------------------------------

    print(
        "\nSearching for symptom clusters..."
    )

    (
        cluster_model,
        best_k,
        silhouette
    ) = find_best_kmeans(
        latent
    )

    if cluster_model is not None:

        print(
            f"Best cluster count: "
            f"{best_k}"
        )

        print(
            f"Silhouette score: "
            f"{silhouette:.4f}"
        )

        cluster_labels = (
            cluster_model.predict(
                latent
            )
        )

    else:

        print(
            "Clustering skipped "
            "(insufficient representation size)."
        )

        cluster_labels = np.zeros(
            len(data),
            dtype=int
        )

    # --------------------------------------------------------
    # Density
    # --------------------------------------------------------

    print(
        "\nCalculating symptom-density novelty..."
    )

    density = calculate_density(
        latent
    )

    density_novelty = (
        density_novelty_score(
            density
        )
    )

    # --------------------------------------------------------
    # Cluster novelty
    # --------------------------------------------------------

    cluster_novelty = (
        calculate_cluster_novelty(
            latent,
            cluster_model
        )
    )

    # --------------------------------------------------------
    # Disease profiles
    # --------------------------------------------------------

    print(
        "\nComparing representations "
        "with established disease profiles..."
    )

    disease_profiles = (
        build_disease_profiles(
            mapping,
            symptom_master,
            symptom_columns
        )
    )

    disease_ids = sorted(
        disease_profiles.keys()
    )

    (
        disease_similarity,
        best_diseases
    ) = calculate_disease_similarity(
        symptom_matrix,
        disease_profiles,
        disease_ids
    )

    # --------------------------------------------------------
    # Encounter-level result
    # --------------------------------------------------------

    encounter_result = data[
        [
            "encounter_id",
            "hospital_id",
        ]
    ].copy()

    encounter_result[
        "disease_similarity"
    ] = disease_similarity

    encounter_result[
        "representation_best_disease_id"
    ] = best_diseases

    encounter_result[
        "density_novelty"
    ] = density_novelty

    encounter_result[
        "cluster_novelty"
    ] = cluster_novelty

    encounter_result[
        "cluster_id"
    ] = cluster_labels

    # --------------------------------------------------------
    # Representation novelty
    # --------------------------------------------------------

    encounter_result[
        "representation_novelty"
    ] = (
        encounter_result[
            "density_novelty"
        ]
        * 0.50

        +

        encounter_result[
            "cluster_novelty"
        ]
        * 0.50
    ).clip(
        0,
        100
    )

    # Required for aggregation
    encounter_result[
        "symptom_columns"
    ] = [
        symptom_columns
    ] * len(
        encounter_result
    )

    # Add symptoms back for pattern generation
    for column in symptom_columns:

        encounter_result[
            column
        ] = data[
            column
        ].values

    # --------------------------------------------------------
    # Aggregate
    # --------------------------------------------------------

    print(
        "\nAggregating representation evidence "
        "to symptom-pattern level..."
    )

    result = aggregate_to_patterns(
        encounter_result,
        a6
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    result = result.sort_values(
        [
            "a7_novelty_score",
            "max_representation_novelty",
        ],
        ascending=False
    )

    result.to_csv(
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
        "A7 COMPLETE"
    )

    print(
        "=" * 80
    )

    print(
        f"Patterns analyzed: "
        f"{len(result)}"
    )

    print(
        f"Output            : "
        f"{OUTPUT_FILE}"
    )

    print(
        "\nNovelty levels:"
    )

    print(
        result[
            "a7_novelty_level"
        ]
        .value_counts()
        .to_string()
    )

    print(
        "\nA7 interpretations:"
    )

    print(
        result[
            "a7_interpretation"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Top patterns
    # --------------------------------------------------------

    print(
        "\nTop representation-novelty patterns:"
    )

    display_columns = [
        "symptom_pattern",
        "best_matching_disease",
        "inference_category",
        "mean_disease_similarity",
        "mean_density_novelty",
        "mean_cluster_novelty",
        "a7_raw_novelty_score",
        "a7_novelty_score",
        "a7_novelty_level",
        "a7_interpretation",
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


if __name__ == "__main__":
    main()
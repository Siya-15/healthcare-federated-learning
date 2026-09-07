"""
Objective A2 — Temporal Emerging Symptom Pattern Analysis

Pipeline:

    A1
    Unusual symptom combinations
            ↓
    A2
    Exact patterns + recurring symptom cores
            ↓
    Baseline vs current prevalence
            ↓
    Temporal growth
            ↓
    Persistence
            ↓
    A1 anomaly evidence
            ↓
    Emergence score
            ↓
    Alert level

Important design principles:

1. Baseline prevalence uses ALL baseline encounters.
2. Current prevalence uses ALL current encounters.
3. A1 anomaly frequency is retained as supporting evidence.
4. Exact emerging patterns may have lower support than cores.
5. Standard cores require stronger population support.
6. Emerging cores may have lower population support.
7. Core statistics use SUBSET matching, not exact-string matching.
8. Negative prevalence growth cannot produce an emergence alert.
9. High/Critical alerts require multiple evidence dimensions.
10. Redundant nested cores are suppressed.
"""

from pathlib import Path
from itertools import combinations
from collections import Counter, defaultdict

import pandas as pd

from emerging_symptom_model import (
    SYMPTOM_COLUMNS,
    detect_anomalies,
)


# ============================================================
# CONFIGURATION
# ============================================================

ML_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ML_DIR

DEFAULT_BASELINE_END = "2026-07-31"


# ============================================================
# EXACT-PATTERN CONFIGURATION
# ============================================================

MIN_RECURRING_OCCURRENCES = 2

MIN_EXACT_EMERGING_OCCURRENCES = 3
MIN_EXACT_EMERGING_DATES = 2
MIN_EXACT_EMERGING_WEEKS = 2

MIN_EXACT_CURRENT_PREVALENCE = 0.002
MIN_EXACT_ANOMALY_SUPPORT = 2


# ============================================================
# STANDARD CORE CONFIGURATION
# ============================================================

MIN_CORE_SIZE = 3
MAX_CORE_SIZE = 8

MIN_CORE_SUPPORT_FRACTION = 0.05
MIN_CORE_SUPPORT_COUNT = 5

MIN_CORE_DISTINCT_DATES = 2
MIN_CORE_DISTINCT_WEEKS = 2

MAX_CORE_CANDIDATE_SYMPTOMS = 18

CORE_SUBSET_SUPPORT_RATIO = 0.90

MAX_CORE_BASELINE_PREVALENCE = 0.05


# ============================================================
# EMERGING CORE CONFIGURATION
# ============================================================

# Emerging cores are intentionally allowed to be much rarer
# than standard recurring cores.

MIN_EMERGING_CORE_SUPPORT = 3
MIN_EMERGING_CORE_ANOMALY_SUPPORT = 2

MIN_EMERGING_CORE_DATES = 2
MIN_EMERGING_CORE_WEEKS = 2

MIN_EMERGING_CORE_SIZE = 3
MAX_EMERGING_CORE_SIZE = 6

# A genuinely emerging core should have low baseline prevalence.
MAX_EMERGING_CORE_BASELINE_PREVALENCE = 0.02

# Candidate symptoms for emerging-core mining.
#
# A1 already identified these records as anomalous, so we
# deliberately mine from anomalous symptom combinations.
MAX_EMERGING_CORE_CANDIDATE_SYMPTOMS = 18

# ============================================================
# EMERGING CORE NOVELTY CONFIGURATION
# ============================================================

# Emerging cores must show meaningful change, not merely
# a tiny positive percentage increase.

MIN_EMERGING_CORE_GROWTH = 1.0

# If the baseline already contains many instances of a core,
# it is probably an established symptom relationship rather
# than a genuinely emerging pattern.

MAX_EMERGING_CORE_BASELINE_SUPPORT = 5

# Require the current population to contain enough of the
# candidate core relative to its historical support.

MIN_EMERGING_CORE_CURRENT_TO_BASELINE_RATIO = 2.0
MAX_EMERGING_CORE_CANDIDATE_SYMPTOMS = 27


# ============================================================
# SCORE CONFIGURATION
# ============================================================

def prevalence_growth_score(growth):
    """
    Convert prevalence growth into a 0-1 score.

        <=0%   -> 0.00
        25%    -> 0.25
        50%    -> 0.50
        100%+  -> 1.00
    """

    if growth <= 0:
        return 0.0

    return min(growth, 1.0)


def anomaly_count_score(count):
    """
    Convert anomalous occurrence count into a 0-1 score.

    Saturates at 20 anomalous occurrences.
    """

    if count <= 0:
        return 0.0

    return min(count / 20.0, 1.0)


def persistence_score(weeks):
    """
    Convert persistence into a 0-1 score.

        1 week  -> 0.20
        2 weeks -> 0.40
        3 weeks -> 0.60
        4 weeks -> 0.80
        5+      -> 1.00
    """

    if weeks <= 0:
        return 0.0

    return min(weeks / 5.0, 1.0)


def weekly_growth_score(growth):
    """
    Convert week-over-week growth into a 0-1 score.
    """

    if growth <= 0:
        return 0.0

    return min(growth, 1.0)


def calculate_emergence_score(
    prevalence_growth,
    anomalous_count,
    persistence_weeks,
    week_over_week_growth,
):
    """
    Composite Objective A2 emergence score.

    Weighting:

        Prevalence growth       = 30%
        A1 anomaly frequency    = 30%
        Persistence             = 25%
        Recent acceleration     = 15%

    Score is scaled to 0-100.
    """

    growth_component = prevalence_growth_score(
        prevalence_growth
    )

    anomaly_component = anomaly_count_score(
        anomalous_count
    )

    persistence_component = persistence_score(
        persistence_weeks
    )

    weekly_component = weekly_growth_score(
        week_over_week_growth
    )

    score = (
        0.30 * growth_component
        +
        0.30 * anomaly_component
        +
        0.25 * persistence_component
        +
        0.15 * weekly_component
    )

    return round(score * 100, 2)


# ============================================================
# ALERT LEVEL
# ============================================================

def determine_alert_level(
    emergence_score,
    anomalous_count,
    current_occurrences,
    prevalence_growth,
    persistence_weeks,
    distinct_dates,
    distinct_weeks,
    pattern_type,
):
    """
    Convert emergence score into an alert level.

    High/Critical alerts require multiple independent
    evidence dimensions.
    """

    # --------------------------------------------------------
    # No positive growth = no emergence alert
    # --------------------------------------------------------

    if prevalence_growth <= 0:
        return "LOW"

    # --------------------------------------------------------
    # Minimum evidence
    # --------------------------------------------------------

    if current_occurrences < 2:
        return "LOW"

    if anomalous_count < MIN_EXACT_ANOMALY_SUPPORT:
        return "LOW"

    # --------------------------------------------------------
    # CRITICAL
    # --------------------------------------------------------

    if (
        emergence_score >= 75
        and anomalous_count >= 10
        and current_occurrences >= 10
        and persistence_weeks >= 3
        and distinct_dates >= 3
    ):
        return "CRITICAL"

    # --------------------------------------------------------
    # HIGH
    # --------------------------------------------------------

    if (
        emergence_score >= 55
        and anomalous_count >= 5
        and current_occurrences >= 5
        and persistence_weeks >= 2
        and distinct_weeks >= 2
    ):
        return "HIGH"

    # --------------------------------------------------------
    # MODERATE
    # --------------------------------------------------------

    if (
        emergence_score >= 35
        and current_occurrences >= 3
        and anomalous_count >= 2
        and distinct_dates >= 2
        and distinct_weeks >= 2
    ):
        return "MODERATE"

    return "LOW"


# ============================================================
# DATA LOADING
# ============================================================

def load_hospital_data(hospital_id):
    """
    Load prepared ML data for one hospital.
    """

    file_path = (
        DATA_DIR
        / f"ml_data_{hospital_id}.csv"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"ML data file not found for "
            f"{hospital_id}: {file_path}"
        )

    df = pd.read_csv(
        file_path,
        keep_default_na=False,
    )

    if "visit_timestamp" not in df.columns:
        raise ValueError(
            "visit_timestamp column is required "
            "for temporal analysis."
        )

    df["visit_timestamp"] = pd.to_datetime(
        df["visit_timestamp"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["visit_timestamp"]
    ).copy()

    return df


# ============================================================
# SYMPTOM PATTERN CREATION
# ============================================================

def create_symptom_pattern(row):
    """
    Convert binary symptom columns into an exact
    symptom combination.
    """

    symptoms = []

    for symptom in SYMPTOM_COLUMNS:

        if symptom not in row.index:
            continue

        try:
            value = int(row[symptom])

        except (
            ValueError,
            TypeError,
        ):
            value = 0

        if value == 1:
            symptoms.append(symptom)

    if not symptoms:
        return "No recorded symptoms"

    return " + ".join(
        sorted(symptoms)
    )


def add_symptom_patterns(df):

    df = df.copy()

    df["symptom_pattern"] = df.apply(
        create_symptom_pattern,
        axis=1
    )

    return df


# ============================================================
# PATTERN → SET
# ============================================================

def pattern_to_set(pattern):
    """
    Convert:

        Fever + Headache + Nausea

    into:

        {"Fever", "Headache", "Nausea"}
    """

    if not isinstance(pattern, str):
        return set()

    if pattern == "No recorded symptoms":
        return set()

    return {
        part.strip()
        for part in pattern.split("+")
        if part.strip()
    }


def set_to_pattern(symptoms):

    return " + ".join(
        sorted(symptoms)
    )


# ============================================================
# ROW → SYMPTOM SET
# ============================================================

def row_to_symptom_set(
    row,
    candidate_symptoms=None,
):
    """
    Convert one encounter row into a symptom set.

    If candidate_symptoms is supplied, only those symptoms
    are considered.
    """

    if candidate_symptoms is None:
        candidate_symptoms = SYMPTOM_COLUMNS

    symptoms = set()

    for symptom in candidate_symptoms:

        if symptom not in row.index:
            continue

        try:
            value = int(row[symptom])
        except (
            ValueError,
            TypeError,
        ):
            value = 0

        if value == 1:
            symptoms.add(symptom)

    return symptoms


# ============================================================
# PATTERN MATCHING
# ============================================================

def pattern_matches_row(
    row,
    pattern,
):
    """
    Check whether an encounter contains a pattern.

    EXACT patterns:
        The row's complete symptom pattern must equal
        the supplied pattern.

    CORE patterns:
        The supplied symptom set only needs to be a subset
        of the row's symptoms.

    This helper is used only where the caller explicitly
    requests subset matching.
    """

    pattern_set = pattern_to_set(pattern)

    if not pattern_set:
        return False

    row_set = row_to_symptom_set(row)

    return pattern_set.issubset(row_set)


def get_matching_rows(
    df,
    pattern,
    pattern_type,
):
    """
    Return rows matching a pattern.

    EXACT:
        exact symptom combination.

    CORE:
        pattern symptoms are a subset of row symptoms.
    """

    if df.empty:
        return df.iloc[0:0].copy()

    if pattern_type == "EXACT":

        return df[
            df["symptom_pattern"] == pattern
        ].copy()

    pattern_set = pattern_to_set(pattern)

    if not pattern_set:
        return df.iloc[0:0].copy()

    mask = df.apply(
        lambda row:
            pattern_set.issubset(
                row_to_symptom_set(row)
            ),
        axis=1,
    )

    return df[
        mask
    ].copy()


# ============================================================
# A1 OUTPUT HANDLING
# ============================================================

def extract_anomaly_dataframe(
    anomaly_result
):
    """
    Normalize Objective A1 output.
    """

    if isinstance(
        anomaly_result,
        pd.DataFrame
    ):
        return anomaly_result

    if isinstance(
        anomaly_result,
        (tuple, list)
    ):

        for item in anomaly_result:

            if isinstance(
                item,
                pd.DataFrame
            ):
                return item

    raise TypeError(
        "Objective A1 detect_anomalies() did not return "
        "a pandas DataFrame or tuple/list containing one."
    )


# ============================================================
# WEEKLY COUNTS
# ============================================================

def get_weekly_counts(
    df,
    pattern=None,
    pattern_type="EXACT",
):
    """
    Calculate weekly occurrence counts.

    If pattern is supplied:

        EXACT → exact pattern matching
        CORE  → subset matching
    """

    if df.empty:

        return pd.DataFrame(
            columns=[
                "week",
                "symptom_pattern",
                "count",
            ]
        )

    result = df.copy()

    result["visit_timestamp"] = pd.to_datetime(
        result["visit_timestamp"],
        errors="coerce"
    )

    result = result.dropna(
        subset=["visit_timestamp"]
    )

    if pattern is not None:

        result = get_matching_rows(
            result,
            pattern,
            pattern_type,
        )

    if result.empty:

        return pd.DataFrame(
            columns=[
                "week",
                "symptom_pattern",
                "count",
            ]
        )

    result["week"] = (
        result["visit_timestamp"]
        .dt.to_period("W-SUN")
        .apply(
            lambda x: x.start_time
        )
    )

    if pattern is not None:

        result["symptom_pattern"] = pattern

    weekly = (
        result.groupby(
            [
                "week",
                "symptom_pattern",
            ]
        )
        .size()
        .reset_index(
            name="count"
        )
    )

    return weekly


# ============================================================
# DISTINCT DATES / WEEKS
# ============================================================

def count_distinct_dates(
    df,
    pattern,
    pattern_type="EXACT",
):
    """
    Count distinct dates containing a pattern.
    """

    subset = get_matching_rows(
        df,
        pattern,
        pattern_type,
    )

    if subset.empty:
        return 0

    return int(
        subset["visit_timestamp"]
        .dt.normalize()
        .nunique()
    )


def count_distinct_weeks(
    df,
    pattern,
    pattern_type="EXACT",
):
    """
    Count distinct weeks containing a pattern.
    """

    subset = get_matching_rows(
        df,
        pattern,
        pattern_type,
    )

    if subset.empty:
        return 0

    return int(
        subset["visit_timestamp"]
        .dt.to_period("W-SUN")
        .nunique()
    )


# ============================================================
# PERSISTENCE
# ============================================================

def calculate_persistence(
    weekly_counts,
    pattern,
):
    """
    Number of consecutive recent weeks in which
    a pattern appeared.
    """

    pattern_df = weekly_counts[
        weekly_counts[
            "symptom_pattern"
        ] == pattern
    ].copy()

    if pattern_df.empty:
        return 0

    observed_weeks = set(
        pattern_df["week"].tolist()
    )

    if not observed_weeks:
        return 0

    current_week = max(
        observed_weeks
    )

    persistence = 0

    while current_week in observed_weeks:

        persistence += 1

        current_week = (
            current_week
            - pd.Timedelta(days=7)
        )

    return persistence


# ============================================================
# WEEK-OVER-WEEK GROWTH
# ============================================================

def calculate_week_over_week_growth(
    weekly_counts,
    pattern,
):
    """
    Calculate week-over-week growth.
    """

    pattern_df = weekly_counts[
        weekly_counts[
            "symptom_pattern"
        ] == pattern
    ].copy()

    if pattern_df.empty:
        return 0.0

    pattern_df = pattern_df.sort_values(
        "week"
    )

    if len(pattern_df) < 2:
        return 0.0

    previous_count = float(
        pattern_df.iloc[-2]["count"]
    )

    current_count = float(
        pattern_df.iloc[-1]["count"]
    )

    if previous_count > 0:

        return (
            current_count
            - previous_count
        ) / previous_count

    if current_count > 0:
        return 1.0

    return 0.0


# ============================================================
# CANDIDATE SYMPTOMS
# ============================================================

def get_candidate_symptoms(
    current_df,
):
    """
    Identify symptoms worth considering for standard
    core mining.
    """

    frequencies = {}

    for symptom in SYMPTOM_COLUMNS:

        if symptom not in current_df.columns:
            continue

        frequency = int(
            current_df[symptom]
            .fillna(0)
            .astype(int)
            .sum()
        )

        frequencies[symptom] = frequency

    ranked = sorted(
        frequencies.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    return [
        symptom
        for symptom, _ in ranked[
            :MAX_CORE_CANDIDATE_SYMPTOMS
        ]
    ]


def get_emerging_candidate_symptoms(
    anomalous_current_df,
):
    """
    Identify symptoms from A1 anomalous encounters.

    Unlike standard core mining, this is specifically intended
    to surface rare symptom combinations.

    We rank symptoms by their frequency inside the anomalous
    population rather than the complete population.
    """

    frequencies = {}

    for symptom in SYMPTOM_COLUMNS:

        if symptom not in anomalous_current_df.columns:
            continue

        frequency = int(
            anomalous_current_df[symptom]
            .fillna(0)
            .astype(int)
            .sum()
        )

        frequencies[symptom] = frequency

    ranked = sorted(
        frequencies.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    return [
        symptom
        for symptom, frequency in ranked[
            :MAX_EMERGING_CORE_CANDIDATE_SYMPTOMS
        ]
        if frequency > 0
    ]


def get_row_symptom_sets(
    df,
    candidate_symptoms,
):
    """
    Convert rows into symptom sets.
    """

    symptom_sets = []

    for _, row in df.iterrows():

        symptoms = row_to_symptom_set(
            row,
            candidate_symptoms,
        )

        if symptoms:
            symptom_sets.append(
                symptoms
            )

    return symptom_sets


def build_symptom_index_from_sets(
    symptom_sets,
):
    """Build symptom -> row-position index from precomputed sets."""
    index = defaultdict(set)

    for row_position, symptom_set in enumerate(symptom_sets):
        for symptom in symptom_set:
            index[symptom].add(row_position)

    return index


def get_matching_positions(
    pattern,
    symptom_index,
):
    """Fast subset matching using set intersection."""
    symptoms = pattern_to_set(pattern)

    if not symptoms:
        return set()

    sets = []

    for symptom in symptoms:
        rows = symptom_index.get(symptom, set())

        if not rows:
            return set()

        sets.append(rows)

    sets.sort(key=len)

    result = set(sets[0])

    for rows in sets[1:]:
        result.intersection_update(rows)

        if not result:
            break

    return result


def temporal_metrics_from_positions(
    df,
    positions,
):
    """Calculate distinct dates/weeks from row positions."""
    if not positions:
        return 0, 0

    timestamps = pd.to_datetime(
        df.iloc[list(positions)]["visit_timestamp"],
        errors="coerce",
    ).dropna()

    if timestamps.empty:
        return 0, 0

    return (
        int(timestamps.dt.normalize().nunique()),
        int(timestamps.dt.to_period("W-SUN").nunique()),
    )


# ============================================================
# STANDARD CORE MINING
# ============================================================

def mine_symptom_cores(
    current_df,
    baseline_df,
):
    """
    Discover recurring symptom cores from ALL current encounters.

    Optimized by generating only combinations actually observed
    in current encounters and using symptom-set indexes for
    support/temporal calculations.
    """

    candidate_symptoms = get_candidate_symptoms(current_df)

    if len(candidate_symptoms) < MIN_CORE_SIZE:
        return []

    current_sets = get_row_symptom_sets(
        current_df,
        candidate_symptoms,
    )

    if not current_sets:
        return []

    baseline_sets = get_row_symptom_sets(
        baseline_df,
        candidate_symptoms,
    )

    current_index = build_symptom_index_from_sets(current_sets)
    baseline_index = build_symptom_index_from_sets(baseline_sets)

    combo_counts = Counter()

    for symptom_set in current_sets:
        available = sorted(symptom_set)
        max_size = min(MAX_CORE_SIZE, len(available))

        for size in range(MIN_CORE_SIZE, max_size + 1):
            for combo in combinations(available, size):
                combo_counts[combo] += 1

    if not combo_counts:
        return []

    candidates = []
    total_current = len(current_df)
    total_baseline = len(baseline_df)

    for combo, support in combo_counts.items():

        if support < MIN_CORE_SUPPORT_COUNT:
            continue

        support_fraction = support / max(total_current, 1)

        if support_fraction < MIN_CORE_SUPPORT_FRACTION:
            continue

        pattern = set_to_pattern(combo)

        current_positions = get_matching_positions(
            pattern,
            current_index,
        )

        current_support = len(current_positions)

        if current_support < MIN_CORE_SUPPORT_COUNT:
            continue

        baseline_positions = get_matching_positions(
            pattern,
            baseline_index,
        )

        baseline_support = len(baseline_positions)

        baseline_prevalence = (
            baseline_support / max(total_baseline, 1)
        )

        if baseline_prevalence > MAX_CORE_BASELINE_PREVALENCE:
            continue

        distinct_dates, distinct_weeks = (
            temporal_metrics_from_positions(
                current_df,
                current_positions,
            )
        )

        if distinct_dates < MIN_CORE_DISTINCT_DATES:
            continue

        if distinct_weeks < MIN_CORE_DISTINCT_WEEKS:
            continue

        current_prevalence = (
            current_support / max(total_current, 1)
        )

        if baseline_prevalence > 0:
            prevalence_growth = (
                current_prevalence - baseline_prevalence
            ) / baseline_prevalence
        else:
            prevalence_growth = 1.0

        if prevalence_growth < 0.25:
            continue

        candidates.append(
            {
                "pattern": pattern,
                "symptoms": set(combo),
                "support": current_support,
                "support_fraction": support_fraction,
                "baseline_prevalence": baseline_prevalence,
                "prevalence_growth": prevalence_growth,
            }
        )

    if not candidates:
        return []

    return suppress_redundant_cores(candidates)




# ============================================================
# EMERGING CORE MINING
# ============================================================

def mine_emerging_cores(
    current_df,
    anomalous_current_df,
    baseline_df,
):
    """
    Discover low-support emerging symptom cores.

    Optimized:
      - candidates come only from combinations observed in A1
        anomalous encounters
      - all 27 active symptoms can participate
      - support uses set intersections rather than repeated
        full DataFrame scans
      - novelty filters run before temporal calculations
    """

    if anomalous_current_df.empty:
        return []

    candidate_symptoms = get_emerging_candidate_symptoms(
        anomalous_current_df
    )

    if len(candidate_symptoms) < MIN_EMERGING_CORE_SIZE:
        return []

    anomalous_sets = get_row_symptom_sets(
        anomalous_current_df,
        candidate_symptoms,
    )

    if not anomalous_sets:
        return []

    # Generate only combinations that actually occur in
    # anomalous encounters.
    combo_counts = Counter()

    for symptom_set in anomalous_sets:

        available = sorted(symptom_set)
        max_size = min(
            MAX_EMERGING_CORE_SIZE,
            len(available),
        )

        for size in range(
            MIN_EMERGING_CORE_SIZE,
            max_size + 1,
        ):
            for combo in combinations(
                available,
                size,
            ):
                combo_counts[combo] += 1

    candidate_combos = [
        (combo, support)
        for combo, support in combo_counts.items()
        if support >= MIN_EMERGING_CORE_ANOMALY_SUPPORT
    ]

    if not candidate_combos:
        return []

    # Build indexes once.
    current_sets = get_row_symptom_sets(
        current_df,
        candidate_symptoms,
    )

    baseline_sets = get_row_symptom_sets(
        baseline_df,
        candidate_symptoms,
    )

    current_index = build_symptom_index_from_sets(
        current_sets
    )

    baseline_index = build_symptom_index_from_sets(
        baseline_sets
    )

    total_current = len(current_df)
    total_baseline = len(baseline_df)

    candidates = []

    for combo, anomalous_support in candidate_combos:

        pattern = set_to_pattern(combo)

        current_positions = get_matching_positions(
            pattern,
            current_index,
        )

        current_support = len(current_positions)

        if current_support < MIN_EMERGING_CORE_SUPPORT:
            continue

        baseline_positions = get_matching_positions(
            pattern,
            baseline_index,
        )

        baseline_support = len(baseline_positions)

        # Strong novelty protection.
        if baseline_support > MAX_EMERGING_CORE_BASELINE_SUPPORT:
            continue

        baseline_prevalence = (
            baseline_support / max(total_baseline, 1)
        )

        if (
            baseline_prevalence
            > MAX_EMERGING_CORE_BASELINE_PREVALENCE
        ):
            continue

        current_prevalence = (
            current_support / max(total_current, 1)
        )

        # Current support should be meaningfully larger than
        # historical support when a baseline exists.
        if baseline_support > 0:

            support_ratio = (
                current_support / baseline_support
            )

            if (
                support_ratio
                < MIN_EMERGING_CORE_CURRENT_TO_BASELINE_RATIO
            ):
                continue

        else:
            support_ratio = float("inf")

        # Prevalence growth.
        if baseline_prevalence > 0:

            prevalence_growth = (
                current_prevalence
                - baseline_prevalence
            ) / baseline_prevalence

        elif current_prevalence > 0:

            prevalence_growth = 1.0

        else:

            prevalence_growth = 0.0

        if prevalence_growth < MIN_EMERGING_CORE_GROWTH:
            continue

        # Temporal evidence.
        distinct_dates, distinct_weeks = (
            temporal_metrics_from_positions(
                current_df,
                current_positions,
            )
        )

        if distinct_dates < MIN_EMERGING_CORE_DATES:
            continue

        if distinct_weeks < MIN_EMERGING_CORE_WEEKS:
            continue

        candidates.append(
            {
                "pattern": pattern,
                "symptoms": set(combo),
                "support": current_support,
                "anomalous_support": anomalous_support,
                "baseline_prevalence": baseline_prevalence,
                "current_prevalence": current_prevalence,
                "prevalence_growth": prevalence_growth,
                "support_ratio": support_ratio,
            }
        )

    if not candidates:
        return []

    return suppress_redundant_cores(candidates)



# ============================================================
# REDUNDANCY SUPPRESSION
# ============================================================

def suppress_redundant_cores(
    candidates,
):
    """
    Remove redundant nested cores.

    Example:

        Fever + Headache + Nausea

    and

        Fever + Headache + Nausea + Vomiting

    If the smaller core explains >=90% of the larger core's
    support, retain the smaller core.

    Candidates are assumed to have already been evaluated
    using subset matching.
    """

    candidates = sorted(
        candidates,
        key=lambda x: (
            x.get(
                "support",
                0
            ),
            -len(
                x["symptoms"]
            ),
        ),
        reverse=True,
    )

    retained = []

    for candidate in candidates:

        is_redundant = False

        for existing in retained:

            existing_set = existing[
                "symptoms"
            ]

            candidate_set = candidate[
                "symptoms"
            ]

            if not existing_set.issubset(
                candidate_set
            ):
                continue

            existing_support = existing.get(
                "support",
                0,
            )

            candidate_support = candidate.get(
                "support",
                0,
            )

            if candidate_support <= 0:
                continue

            ratio = (
                existing_support
                /
                candidate_support
            )

            if (
                ratio
                >= CORE_SUBSET_SUPPORT_RATIO
            ):

                is_redundant = True
                break

        if not is_redundant:
            retained.append(
                candidate
            )

    return [
        item["pattern"]
        for item in retained
    ]


# ============================================================
# EXACT EMERGING PATTERN DISCOVERY
# ============================================================

def discover_exact_emerging_patterns(
    current_df,
    anomalous_current_df,
    baseline_df,
):
    """
    Discover complete symptom combinations that are emerging
    but may not satisfy the stronger core-support threshold.
    """

    current_counts = (
        current_df[
            "symptom_pattern"
        ]
        .value_counts()
    )

    anomalous_counts = (
        anomalous_current_df[
            "symptom_pattern"
        ]
        .value_counts()
    )

    candidates = []

    for pattern, current_count in current_counts.items():

        if (
            current_count
            < MIN_EXACT_EMERGING_OCCURRENCES
        ):
            continue

        if pattern == "No recorded symptoms":
            continue

        anomalous_count = int(
            anomalous_counts.get(
                pattern,
                0,
            )
        )

        if (
            anomalous_count
            < MIN_EXACT_ANOMALY_SUPPORT
        ):
            continue

        matching_current = get_matching_rows(
            current_df,
            pattern,
            "EXACT",
        )

        distinct_dates = (
            matching_current[
                "visit_timestamp"
            ]
            .dt.normalize()
            .nunique()
        )

        distinct_weeks = (
            matching_current[
                "visit_timestamp"
            ]
            .dt.to_period("W-SUN")
            .nunique()
        )

        if (
            distinct_dates
            < MIN_EXACT_EMERGING_DATES
        ):
            continue

        if (
            distinct_weeks
            < MIN_EXACT_EMERGING_WEEKS
        ):
            continue

        baseline_matching = get_matching_rows(
            baseline_df,
            pattern,
            "EXACT",
        )

        baseline_count = len(
            baseline_matching
        )

        baseline_prevalence = (
            baseline_count
            /
            max(len(baseline_df), 1)
        )

        current_prevalence = (
            current_count
            /
            max(len(current_df), 1)
        )

        if baseline_prevalence > 0:

            growth = (
                current_prevalence
                -
                baseline_prevalence
            ) / baseline_prevalence

        else:

            growth = (
                1.0
                if current_prevalence > 0
                else 0.0
            )

        if growth <= 0:
            continue

        if (
            current_prevalence
            < MIN_EXACT_CURRENT_PREVALENCE
        ):
            continue

        candidates.append(
            {
                "pattern": pattern,
                "current_occurrences": int(
                    current_count
                ),
                "anomalous_occurrences": anomalous_count,
                "baseline_occurrences": baseline_count,
                "baseline_prevalence": baseline_prevalence,
                "current_prevalence": current_prevalence,
                "prevalence_growth": growth,
                "distinct_dates": int(
                    distinct_dates
                ),
                "distinct_weeks": int(
                    distinct_weeks
                ),
            }
        )

    return candidates


# ============================================================
# MAIN TEMPORAL ANALYSIS
# ============================================================

def analyze_temporal_patterns(
    hospital_id,
    baseline_end=DEFAULT_BASELINE_END,
):
    """
    Perform Objective A2 temporal analysis.
    """

    print("=" * 80)

    print(
        f"TEMPORAL SYMPTOM ANALYSIS: "
        f"{hospital_id}"
    )

    print("=" * 80)

    # ========================================================
    # LOAD
    # ========================================================

    df = load_hospital_data(
        hospital_id
    )

    baseline_end = pd.Timestamp(
        baseline_end
    )

    baseline_df = df[
        df["visit_timestamp"]
        <= baseline_end
    ].copy()

    current_df = df[
        df["visit_timestamp"]
        > baseline_end
    ].copy()

    print(
        f"Baseline encounters : "
        f"{len(baseline_df)}"
    )

    print(
        f"Current encounters  : "
        f"{len(current_df)}"
    )

    if baseline_df.empty:
        raise ValueError(
            f"No baseline encounters found "
            f"for {hospital_id}."
        )

    if current_df.empty:
        raise ValueError(
            f"No current encounters found "
            f"for {hospital_id}."
        )

    # ========================================================
    # CREATE PATTERNS
    # ========================================================

    baseline_df = add_symptom_patterns(
        baseline_df
    )

    current_df = add_symptom_patterns(
        current_df
    )

    # ========================================================
    # A1
    # ========================================================

    print()

    print(
        "Running Objective A1 anomaly detection..."
    )

    raw_anomaly_result = detect_anomalies(
        hospital_id
    )

    anomaly_df = extract_anomaly_dataframe(
        raw_anomaly_result
    )

    if "is_anomalous" not in anomaly_df.columns:
        raise ValueError(
            "A1 anomaly output does not contain "
            "'is_anomalous'."
        )

    anomaly_df = anomaly_df[
        anomaly_df[
            "is_anomalous"
        ] == True
    ].copy()

    print(
        f"A1 anomalous rows : "
        f"{len(anomaly_df)}"
    )

    if anomaly_df.empty:
        print(
            "No anomalous encounters detected."
        )
        return pd.DataFrame()

    # ========================================================
    # NORMALIZE IDs
    # ========================================================

    if "encounter_id" not in anomaly_df.columns:
        raise ValueError(
            "A1 anomaly output does not contain "
            "'encounter_id'."
        )

    anomaly_df[
        "encounter_id"
    ] = (
        anomaly_df[
            "encounter_id"
        ]
        .astype(str)
    )

    current_df[
        "encounter_id"
    ] = (
        current_df[
            "encounter_id"
        ]
        .astype(str)
    )

    # ========================================================
    # CURRENT A1 ANOMALIES
    # ========================================================

    anomalous_ids = set(
        anomaly_df[
            "encounter_id"
        ].tolist()
    )

    anomalous_current_df = current_df[
        current_df[
            "encounter_id"
        ].isin(
            anomalous_ids
        )
    ].copy()

    print(
        f"Current anomalous encounters : "
        f"{len(anomalous_current_df)}"
    )

    if anomalous_current_df.empty:
        print(
            "No current anomalous encounters "
            "matched the current period."
        )
        return pd.DataFrame()

    # ========================================================
    # WEEKLY A1 ANOMALY COUNTS
    # ========================================================

    weekly_anomalous_counts = get_weekly_counts(
        anomalous_current_df
    )

    # ========================================================
    # EXACT PATTERNS
    # ========================================================

    print()

    print(
        "Analysing EXACT symptom patterns..."
    )

    anomalous_exact_counts = (
        anomalous_current_df[
            "symptom_pattern"
        ]
        .value_counts()
    )

    exact_candidates = (
        anomalous_exact_counts[
            anomalous_exact_counts
            >= MIN_RECURRING_OCCURRENCES
        ]
        .index
        .tolist()
    )

    low_support_exact = (
        discover_exact_emerging_patterns(
            current_df=current_df,
            anomalous_current_df=anomalous_current_df,
            baseline_df=baseline_df,
        )
    )

    low_support_exact_patterns = [
        item["pattern"]
        for item in low_support_exact
    ]

    exact_candidates = list(
        dict.fromkeys(
            exact_candidates
            +
            low_support_exact_patterns
        )
    )

    print(
        f"Exact patterns : "
        f"{len(exact_candidates)}"
    )

    # ========================================================
    # STANDARD CORES
    # ========================================================

    print()

    print(
        "Mining recurring symptom CORES..."
    )

    core_candidates = mine_symptom_cores(
        current_df=current_df,
        baseline_df=baseline_df,
    )

    print(
        f"Standard core patterns : "
        f"{len(core_candidates)}"
    )

    # ========================================================
    # EMERGING CORES
    # ========================================================

    print()

    print(
        "Mining low-support EMERGING CORES..."
    )

    emerging_core_candidates = mine_emerging_cores(
        current_df=current_df,
        anomalous_current_df=anomalous_current_df,
        baseline_df=baseline_df,
    )

    print(
        f"Emerging core patterns : "
        f"{len(emerging_core_candidates)}"
    )

    # ========================================================
    # COMBINE
    # ========================================================

    pattern_records = []

    for pattern in exact_candidates:

        pattern_records.append(
            {
                "pattern": pattern,
                "pattern_type": "EXACT",
            }
        )

    for pattern in core_candidates:

        if pattern in exact_candidates:
            continue

        pattern_records.append(
            {
                "pattern": pattern,
                "pattern_type": "CORE",
            }
        )

    for pattern in emerging_core_candidates:

        if pattern in exact_candidates:
            continue

        if pattern in core_candidates:
            continue

        pattern_records.append(
            {
                "pattern": pattern,
                "pattern_type": "CORE",
            }
        )

    if not pattern_records:

        print(
            "No temporal patterns generated."
        )

        return pd.DataFrame()

    # ========================================================
    # DATE RANGES
    # ========================================================

    baseline_total_encounters = len(
        baseline_df
    )

    current_total_encounters = len(
        current_df
    )

    baseline_days = max(
        (
            baseline_df[
                "visit_timestamp"
            ].max()
            -
            baseline_df[
                "visit_timestamp"
            ].min()
        ).days + 1,
        1,
    )

    current_days = max(
        (
            current_df[
                "visit_timestamp"
            ].max()
            -
            current_df[
                "visit_timestamp"
            ].min()
        ).days + 1,
        1,
    )

    # ========================================================
    # RESULT CONSTRUCTION
    # ========================================================

    results = []

    for record in pattern_records:

        pattern = record[
            "pattern"
        ]

        pattern_type = record[
            "pattern_type"
        ]

        # ----------------------------------------------------
        # Baseline matching
        # ----------------------------------------------------

        baseline_matching = get_matching_rows(
            baseline_df,
            pattern,
            pattern_type,
        )

        baseline_occurrences = len(
            baseline_matching
        )

        # ----------------------------------------------------
        # Current ALL encounters
        #
        # IMPORTANT:
        #
        # CORE patterns use subset matching.
        # EXACT patterns use exact matching.
        # ----------------------------------------------------

        current_matching = get_matching_rows(
            current_df,
            pattern,
            pattern_type,
        )

        current_pattern_occurrences = len(
            current_matching
        )

        # ----------------------------------------------------
        # Current A1 anomalies
        # ----------------------------------------------------

        current_anomalous_matching = get_matching_rows(
            anomalous_current_df,
            pattern,
            pattern_type,
        )

        current_anomalous_occurrences = len(
            current_anomalous_matching
        )

        # ----------------------------------------------------
        # Prevalence
        # ----------------------------------------------------

        baseline_prevalence = (
            baseline_occurrences
            /
            max(
                baseline_total_encounters,
                1,
            )
        )

        current_prevalence = (
            current_pattern_occurrences
            /
            max(
                current_total_encounters,
                1,
            )
        )

        # ----------------------------------------------------
        # Prevalence growth
        # ----------------------------------------------------

        if baseline_prevalence > 0:

            prevalence_growth = (
                current_prevalence
                -
                baseline_prevalence
            ) / baseline_prevalence

        elif current_prevalence > 0:

            prevalence_growth = 1.0

        else:

            prevalence_growth = 0.0

        # ----------------------------------------------------
        # Daily averages
        # ----------------------------------------------------

        baseline_daily_average = (
            baseline_occurrences
            /
            baseline_days
        )

        current_daily_average = (
            current_pattern_occurrences
            /
            current_days
        )

        # ----------------------------------------------------
        # Weekly A1 statistics
        #
        # IMPORTANT:
        #
        # These now use subset matching for CORE patterns.
        # ----------------------------------------------------

        pattern_weekly_anomalous = get_weekly_counts(
            anomalous_current_df,
            pattern=pattern,
            pattern_type=pattern_type,
        )

        if pattern_weekly_anomalous.empty:

            current_week_count = 0
            current_weekly_average = 0.0
            peak_weekly_count = 0

        else:

            current_week_count = len(
                pattern_weekly_anomalous
            )

            current_weekly_average = float(
                pattern_weekly_anomalous[
                    "count"
                ].mean()
            )

            peak_weekly_count = int(
                pattern_weekly_anomalous[
                    "count"
                ].max()
            )

        # ----------------------------------------------------
        # Week-over-week growth
        # ----------------------------------------------------

        week_over_week_growth = (
            calculate_week_over_week_growth(
                pattern_weekly_anomalous,
                pattern,
            )
        )

        # ----------------------------------------------------
        # Baseline relative growth
        # ----------------------------------------------------

        if baseline_daily_average > 0:

            baseline_relative_growth = (
                current_daily_average
                -
                baseline_daily_average
            ) / baseline_daily_average

        elif current_daily_average > 0:

            baseline_relative_growth = 1.0

        else:

            baseline_relative_growth = 0.0

        # ----------------------------------------------------
        # Temporal evidence
        #
        # ALL current encounters.
        # ----------------------------------------------------

        distinct_dates = count_distinct_dates(
            current_df,
            pattern,
            pattern_type,
        )

        distinct_weeks = count_distinct_weeks(
            current_df,
            pattern,
            pattern_type,
        )

        # ----------------------------------------------------
        # Persistence
        #
        # First use A1-supported persistence.
        # ----------------------------------------------------

        persistence_weeks = calculate_persistence(
            pattern_weekly_anomalous,
            pattern,
        )

        # ----------------------------------------------------
        # For exact patterns, allow all-current persistence
        # after minimum A1 support has been established.
        # Same principle is retained for emerging cores.
        # ----------------------------------------------------

        if (
            current_anomalous_occurrences
            >= MIN_EXACT_ANOMALY_SUPPORT
        ):

            current_weekly_counts = get_weekly_counts(
                current_df,
                pattern=pattern,
                pattern_type=pattern_type,
            )

            all_current_persistence = (
                calculate_persistence(
                    current_weekly_counts,
                    pattern,
                )
            )

            persistence_weeks = max(
                persistence_weeks,
                all_current_persistence,
            )

        # ----------------------------------------------------
        # Emergence score
        # ----------------------------------------------------

        emergence_score = calculate_emergence_score(
            prevalence_growth=prevalence_growth,
            anomalous_count=current_anomalous_occurrences,
            persistence_weeks=persistence_weeks,
            week_over_week_growth=week_over_week_growth,
        )

        # ----------------------------------------------------
        # Alert
        # ----------------------------------------------------

        alert_level = determine_alert_level(
            emergence_score=emergence_score,
            anomalous_count=current_anomalous_occurrences,
            current_occurrences=current_pattern_occurrences,
            prevalence_growth=prevalence_growth,
            persistence_weeks=persistence_weeks,
            distinct_dates=distinct_dates,
            distinct_weeks=distinct_weeks,
            pattern_type=pattern_type,
        )

        # ----------------------------------------------------
        # Store
        # ----------------------------------------------------

        results.append(
            {
                "hospital_id":
                    hospital_id,

                "pattern_type":
                    pattern_type,

                "symptom_pattern":
                    pattern,

                # Frequency
                "baseline_occurrences":
                    baseline_occurrences,

                "current_pattern_occurrences":
                    current_pattern_occurrences,

                "current_anomalous_occurrences":
                    current_anomalous_occurrences,

                # Prevalence
                "baseline_prevalence":
                    baseline_prevalence,

                "current_prevalence":
                    current_prevalence,

                "prevalence_growth":
                    prevalence_growth,

                # Daily
                "baseline_daily_average":
                    baseline_daily_average,

                "current_daily_average":
                    current_daily_average,

                # Weekly
                "current_weekly_average":
                    current_weekly_average,

                "current_week_count":
                    current_week_count,

                "peak_weekly_count":
                    peak_weekly_count,

                "distinct_dates":
                    distinct_dates,

                "distinct_weeks":
                    distinct_weeks,

                # Growth
                "week_over_week_growth":
                    week_over_week_growth,

                "baseline_relative_growth":
                    baseline_relative_growth,

                # Persistence
                "persistence_weeks":
                    persistence_weeks,

                # Score
                "emergence_score":
                    emergence_score,

                "alert_level":
                    alert_level,
            }
        )

    # ========================================================
    # DATAFRAME
    # ========================================================

    result_df = pd.DataFrame(
        results
    )

    if result_df.empty:
        return result_df

    # ========================================================
    # SORT
    # ========================================================

    result_df = result_df.sort_values(
        by=[
            "emergence_score",
            "prevalence_growth",
            "persistence_weeks",
            "current_anomalous_occurrences",
            "current_pattern_occurrences",
        ],
        ascending=[
            False,
            False,
            False,
            False,
            False,
        ],
    ).reset_index(
        drop=True
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    print()

    print("=" * 80)

    print(
        "TEMPORAL PATTERN SUMMARY"
    )

    print("=" * 80)

    print(
        f"Patterns analysed : "
        f"{len(result_df)}"
    )

    exact_count = int(
        (
            result_df[
                "pattern_type"
            ]
            == "EXACT"
        ).sum()
    )

    core_count = int(
        (
            result_df[
                "pattern_type"
            ]
            == "CORE"
        ).sum()
    )

    print(
        f"  EXACT : {exact_count}"
    )

    print(
        f"  CORE  : {core_count}"
    )

    print()

    display_columns = [
        "pattern_type",
        "symptom_pattern",
        "baseline_occurrences",
        "current_pattern_occurrences",
        "current_anomalous_occurrences",
        "baseline_prevalence",
        "current_prevalence",
        "prevalence_growth",
        "persistence_weeks",
        "emergence_score",
        "alert_level",
    ]

    print(
        result_df[
            display_columns
        ].head(20).to_string(
            index=False
        )
    )

    return result_df


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":

    hospitals = [
        "H001",
        "H002",
        "H003",
        "H004",
        "H005",
        "H006",
        "H007",
        "H008",
        "H009",
        "H010",
    ]

    for hospital_id in hospitals:

        try:

            analyze_temporal_patterns(
                hospital_id
            )

            print()

        except Exception as error:

            print()

            print(
                f"ERROR for {hospital_id}: "
                f"{error}"
            )

            print()
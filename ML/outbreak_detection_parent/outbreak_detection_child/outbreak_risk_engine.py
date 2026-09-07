"""
B10 - Composite Outbreak-Risk Engine

Purpose
-------
Combines evidence from B3-B9 into a single outbreak-risk assessment.

B3 - Historical baseline
B4 - Statistical anomaly detection
B5 - Temporal acceleration
B6 - Persistence
B7 - Spatial propagation
B8 - Objective A emerging/atypical symptom integration
B9 - Severity burden

Important design principle
--------------------------
B3-B8 primarily operate at symptom/pattern level.

B9 operates at disease level.

Therefore B9 severity evidence is NOT broadcast to every symptom.
Severity is connected to symptom-level risk only when B8 provides
a disease association for that symptom's Objective-A pattern.

Outputs
-------
outbreak_risk_engine.csv
outbreak_risk_latest.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

B3_FILE = BASE_DIR / "symptom_historical_baseline.csv"
B4_FILE = BASE_DIR / "symptom_anomaly_detection.csv"
B5_FILE = BASE_DIR / "temporal_acceleration.csv"
B6_FILE = BASE_DIR / "symptom_persistence_detection.csv"
B7_FILE = BASE_DIR / "spatial_propagation.csv"
B8_FILE = BASE_DIR / "objective_a_integration.csv"
B9_FILE = BASE_DIR / "severity_burden.csv"

OUTPUT_FILE = BASE_DIR / "outbreak_risk_engine.csv"
LATEST_OUTPUT_FILE = BASE_DIR / "outbreak_risk_latest.csv"


# ============================================================================
# CONFIGURATION
# ============================================================================

WEIGHTS = {
    "baseline": 0.15,
    "anomaly": 0.15,
    "temporal": 0.15,
    "persistence": 0.15,
    "spatial": 0.15,
    "objective_a": 0.10,
    "severity": 0.15,
}

YELLOW_THRESHOLD = 35.0
ORANGE_THRESHOLD = 55.0
RED_THRESHOLD = 75.0

STRONG_EVIDENCE = 55.0
MODERATE_EVIDENCE = 35.0


# ============================================================================
# HELPERS
# ============================================================================

def clamp(value, low=0.0, high=100.0):
    if pd.isna(value):
        return 0.0

    return float(
        max(
            low,
            min(high, float(value))
        )
    )


def safe_numeric(df, columns):
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            ).fillna(0.0)

    return df


def find_first_existing(
    df,
    candidates,
    default=0.0,
):
    for column in candidates:
        if column in df.columns:
            return df[column]

    return pd.Series(
        default,
        index=df.index
    )


# ============================================================================
# LOADERS
# ============================================================================

def load_b3():

    print("Loading B3 historical baseline...")

    df = pd.read_csv(B3_FILE)

    print(f"B3 rows: {len(df)}")

    required = [
        "week",
        "hospital_id",
        "symptom_id",
        "symptom_name",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"B3 missing columns: {missing}"
        )

    return df


def load_b4():

    print("Loading B4 statistical anomaly detection...")

    df = pd.read_csv(B4_FILE)

    print(f"B4 rows: {len(df)}")

    if "week" not in df.columns:
        raise ValueError(
            "B4 missing week column."
        )

    return df


def load_b5():

    print("Loading B5 temporal acceleration...")

    df = pd.read_csv(B5_FILE)

    print(f"B5 rows: {len(df)}")

    if "week" not in df.columns:
        raise ValueError(
            "B5 missing week column."
        )

    return df


def load_b6():

    print("Loading B6 persistence detection...")

    df = pd.read_csv(B6_FILE)

    print(f"B6 rows: {len(df)}")

    if "week" not in df.columns:
        raise ValueError(
            "B6 missing week column."
        )

    return df


def load_b7():

    print("Loading B7 spatial propagation...")

    df = pd.read_csv(B7_FILE)

    print(f"B7 rows: {len(df)}")

    if "week" not in df.columns:
        raise ValueError(
            "B7 missing week column."
        )

    return df


def load_b8():

    print("Loading B8 Objective A integration...")

    df = pd.read_csv(B8_FILE)

    print(f"B8 rows: {len(df)}")

    required = [
        "symptom_pattern",
        "best_matching_disease_id",
        "objective_a_score",
        "b8_integration_score",
        "b8_alert",
        "b8_integration_signal",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"B8 missing columns: {missing}"
        )

    return df


def load_b9():

    print("Loading B9 severity burden...")

    df = pd.read_csv(B9_FILE)

    print(f"B9 rows: {len(df)}")

    if "week" not in df.columns:
        raise ValueError(
            "B9 missing week column."
        )

    required = [
        "disease_id",
        "severity_burden_score",
        "severe_cases",
        "total_cases",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"B9 missing columns: {missing}"
        )

    return df


# ============================================================================
# B3 STANDARDIZATION
# ============================================================================

def standardize_b3(df):

    """
    Convert B3 hospital × symptom × week data into
    symptom × week baseline evidence.
    """

    df = df.copy()

    numeric_columns = [
        "z_score",
        "deviation_percent",
        "current_cases",
    ]

    df = safe_numeric(
        df,
        numeric_columns
    )

    grouped = (
        df
        .groupby(
            [
                "week",
                "symptom_id",
            ],
            as_index=False,
        )
        .agg(
            symptom_name=(
                "symptom_name",
                "first"
            ),

            baseline_z_max=(
                "z_score",
                "max"
            ),

            baseline_deviation_max=(
                "deviation_percent",
                "max"
            ),

            baseline_hospitals_elevated=(
                "z_score",
                lambda x: int(
                    (x >= 1.5).sum()
                )
            ),

            baseline_hospitals_observed=(
                "hospital_id",
                "nunique"
            ),
        )
    )

    def calculate_score(row):

        z_score = clamp(
            (row["baseline_z_max"] / 3.0)
            * 100.0
        )

        deviation_score = clamp(
            row["baseline_deviation_max"]
        )

        hospital_score = clamp(
            (
                row["baseline_hospitals_elevated"]
                / 10.0
            )
            * 100.0
        )

        return (
            0.50 * z_score
            +
            0.30 * deviation_score
            +
            0.20 * hospital_score
        )

    grouped["baseline_score"] = (
        grouped
        .apply(
            calculate_score,
            axis=1
        )
        .clip(0, 100)
    )

    return grouped


# ============================================================================
# GENERIC B4-B7 STANDARDIZATION
# ============================================================================

def standardize_generic(
    df,
    score_candidates,
    output_name,
    group_columns=(
        "week",
        "symptom_id",
    ),
):

    df = df.copy()

    score_series = find_first_existing(
        df,
        score_candidates,
        default=0.0
    )

    df[output_name] = pd.to_numeric(
        score_series,
        errors="coerce"
    ).fillna(0.0).clip(
        0,
        100
    )

    available_groups = [
        c
        for c in group_columns
        if c in df.columns
    ]

    if not available_groups:
        raise ValueError(
            f"Could not find grouping columns "
            f"for {output_name}."
        )

    grouped = (
        df
        .groupby(
            available_groups,
            as_index=False
        )[output_name]
        .max()
    )

    return grouped


# ============================================================================
# B8 STANDARDIZATION
# ============================================================================

def standardize_b8(df):

    """
    Convert B8 pattern-level Objective A evidence
    into symptom-level supporting evidence.

    B8 patterns may contain multiple symptoms.

    Example:

        Fever + Headache + Rash

    becomes:

        Fever
        Headache
        Rash

    The strongest pattern containing each symptom is retained.

    B8 remains supporting evidence and is not treated as
    an independent weekly outbreak detector.
    """

    df = df.copy()

    df["objective_a_score"] = pd.to_numeric(
        df["objective_a_score"],
        errors="coerce"
    ).fillna(0.0).clip(
        0,
        100
    )

    df["b8_integration_score"] = pd.to_numeric(
        df["b8_integration_score"],
        errors="coerce"
    ).fillna(0.0).clip(
        0,
        100
    )

    df["b8_pattern_score"] = (
        0.60 * df["objective_a_score"]
        +
        0.40 * df["b8_integration_score"]
    ).clip(
        0,
        100
    )

    rows = []

    for _, row in df.iterrows():

        pattern = str(
            row["symptom_pattern"]
        )

        symptoms = [
            s.strip()
            for s in pattern.split("+")
            if s.strip()
        ]

        for symptom in symptoms:

            rows.append(
                {
                    "symptom_name": symptom,

                    "best_matching_disease_id":
                        row[
                            "best_matching_disease_id"
                        ],

                    "b8_pattern_score":
                        row[
                            "b8_pattern_score"
                        ],

                    "objective_a_score":
                        row[
                            "objective_a_score"
                        ],

                    "b8_integration_score":
                        row[
                            "b8_integration_score"
                        ],

                    "b8_alert":
                        row["b8_alert"],

                    "b8_integration_signal":
                        row[
                            "b8_integration_signal"
                        ],
                }
            )

    expanded = pd.DataFrame(rows)

    if expanded.empty:

        return pd.DataFrame(
            columns=[
                "symptom_name",
                "best_matching_disease_id",
                "b8_pattern_score",
                "objective_a_score",
                "b8_integration_score",
                "b8_alert",
                "b8_integration_signal",
            ]
        )

    # Keep strongest pattern for each symptom.
    expanded = (
        expanded
        .sort_values(
            "b8_pattern_score",
            ascending=False
        )
        .drop_duplicates(
            "symptom_name"
        )
    )

    return expanded.reset_index(
        drop=True
    )


# ============================================================================
# B9 STANDARDIZATION
# ============================================================================

def standardize_b9(df):

    """
    Preserve B9 as disease × week evidence.

    No aggregation to symptom level occurs here.
    """

    df = df.copy()

    df["severity_score"] = pd.to_numeric(
        df["severity_burden_score"],
        errors="coerce"
    ).fillna(0.0).clip(
        0,
        100
    )

    df["severe_cases"] = pd.to_numeric(
        df["severe_cases"],
        errors="coerce"
    ).fillna(0.0)

    df["total_cases"] = pd.to_numeric(
        df["total_cases"],
        errors="coerce"
    ).fillna(0.0)

    keep_columns = [
        "week",
        "disease_id",
        "severity_score",
        "severe_cases",
        "total_cases",
    ]

    result = df[
        [
            c
            for c in keep_columns
            if c in df.columns
        ]
    ].copy()

    return result


# ============================================================================
# ATTACH B8 TO SYMPTOMS
# ============================================================================

def attach_b8_to_symptoms(
    master,
    b8_std,
    b3,
):

    """
    Map B8 component symptom names to B3 symptom IDs.

    B8 contributes:

        b8_pattern_score

    and the associated disease:

        best_matching_disease_id

    to the relevant symptom.

    No weekly duplication occurs because B8 is attached
    once per symptom and acts as supporting evidence.
    """

    master = master.copy()

    columns_to_remove = [
        "b8_pattern_score",
        "objective_a_score",
        "b8_integration_score",
        "b8_patterns_observed",
        "best_matching_disease_id",
    ]

    existing = [
        c
        for c in columns_to_remove
        if c in master.columns
    ]

    if existing:
        master = master.drop(
            columns=existing
        )

    symptom_mapping = (
        b3[
            [
                "symptom_id",
                "symptom_name",
            ]
        ]
        .drop_duplicates()
    )

    b8_mapped = b8_std.merge(
        symptom_mapping,
        on="symptom_name",
        how="left",
    )

    b8_mapped = b8_mapped.dropna(
        subset=[
            "symptom_id"
        ]
    )

    b8_mapped = (
        b8_mapped
        .sort_values(
            "b8_pattern_score",
            ascending=False
        )
        .drop_duplicates(
            "symptom_id"
        )
    )

    b8_mapped = b8_mapped[
        [
            "symptom_id",
            "best_matching_disease_id",
            "b8_pattern_score",
            "objective_a_score",
            "b8_integration_score",
        ]
    ]

    master = master.merge(
        b8_mapped,
        on="symptom_id",
        how="left",
    )

    return master


# ============================================================================
# ATTACH DISEASE SEVERITY THROUGH B8
# ============================================================================

def attach_disease_severity(
    master,
    b8_std,
    b9_std,
):

    """
    Connect B9 disease-level severity evidence to
    symptom-level B10 risk only through the disease
    association supplied by B8.

    This prevents a severe outbreak in one disease from
    automatically increasing the risk of unrelated symptoms.
    """

    # --------------------------------------------------------------
    # Build symptom → associated disease mapping from B8.
    # --------------------------------------------------------------

    symptom_mapping = (
        b8_std[
            [
                "symptom_name",
                "best_matching_disease_id",
            ]
        ]
        .dropna(
            subset=[
                "symptom_name",
                "best_matching_disease_id",
            ]
        )
        .drop_duplicates(
            "symptom_name"
        )
    )

    # --------------------------------------------------------------
    # Map symptom IDs.
    # --------------------------------------------------------------

    # B3 supplies the stable symptom ID/name mapping.
    #
    # The master table already contains symptom_name from B3,
    # so map using that directly.

    if "symptom_name" in master.columns:

        master = master.merge(
            symptom_mapping,
            on="symptom_name",
            how="left",
            suffixes=(
                "",
                "_b8"
            )
        )

        # If a previous B8 disease ID exists, prefer it.
        if "best_matching_disease_id_b8" in master.columns:

            if "best_matching_disease_id" in master.columns:

                master["best_matching_disease_id"] = (
                    master[
                        "best_matching_disease_id"
                    ]
                    .fillna(
                        master[
                            "best_matching_disease_id_b8"
                        ]
                    )
                )

                master = master.drop(
                    columns=[
                        "best_matching_disease_id_b8"
                    ]
                )

            else:

                master = master.rename(
                    columns={
                        "best_matching_disease_id_b8":
                            "best_matching_disease_id"
                    }
                )

    # --------------------------------------------------------------
    # B9 latest disease severity must match the current week.
    # --------------------------------------------------------------

    severity_lookup = b9_std[
        [
            "week",
            "disease_id",
            "severity_score",
            "severe_cases",
            "total_cases",
        ]
    ].copy()

    severity_lookup = (
        severity_lookup
        .groupby(
            [
                "week",
                "disease_id",
            ],
            as_index=False
        )
        .agg(
            severity_score=(
                "severity_score",
                "max"
            ),
            severe_cases=(
                "severe_cases",
                "sum"
            ),
            total_cases=(
                "total_cases",
                "sum"
            ),
        )
    )

    # --------------------------------------------------------------
    # Merge using week + disease.
    # --------------------------------------------------------------

    master = master.merge(
        severity_lookup,
        left_on=[
            "week",
            "best_matching_disease_id",
        ],
        right_on=[
            "week",
            "disease_id",
        ],
        how="left",
    )

    # --------------------------------------------------------------
    # IMPORTANT:
    #
    # If no B8 disease association exists, severity contribution
    # is zero.
    # --------------------------------------------------------------

    master["severity_score"] = (
        pd.to_numeric(
            master["severity_score"],
            errors="coerce"
        )
        .fillna(0.0)
        .clip(0, 100)
    )

    master["severe_cases"] = (
        pd.to_numeric(
            master["severe_cases"],
            errors="coerce"
        )
        .fillna(0.0)
    )

    master["disease_total_cases"] = (
        pd.to_numeric(
            master["total_cases"],
            errors="coerce"
        )
        .fillna(0.0)
    )

    # Remove merge helper.
    if "disease_id" in master.columns:
        master = master.drop(
            columns=[
                "disease_id"
            ]
        )

    return master


# ============================================================================
# COMPOSITE SCORE
# ============================================================================

def calculate_composite_score(
    df
):

    df = df.copy()

    df["raw_risk_score"] = (
        WEIGHTS["baseline"]
        * df["baseline_score"]

        +

        WEIGHTS["anomaly"]
        * df["anomaly_score"]

        +

        WEIGHTS["temporal"]
        * df["temporal_score"]

        +

        WEIGHTS["persistence"]
        * df["persistence_score"]

        +

        WEIGHTS["spatial"]
        * df["spatial_score"]

        +

        WEIGHTS["objective_a"]
        * df["b8_pattern_score"]

        +

        WEIGHTS["severity"]
        * df["severity_score"]
    )

    df["risk_score"] = (
        df["raw_risk_score"]
        .clip(
            0,
            100
        )
        .round(2)
    )

    return df


# ============================================================================
# ALERT CLASSIFICATION
# ============================================================================

def classify_alerts(
    df
):

    df = df.copy()

    evidence_columns = [
        "baseline_score",
        "anomaly_score",
        "temporal_score",
        "persistence_score",
        "spatial_score",
        "b8_pattern_score",
        "severity_score",
    ]

    df["strong_evidence_count"] = (
        df[evidence_columns] >= STRONG_EVIDENCE
    ).sum(
        axis=1
    )

    df["moderate_evidence_count"] = (
        df[evidence_columns] >= MODERATE_EVIDENCE
    ).sum(
        axis=1
    )

    df["persistence_support"] = (
        df["persistence_score"]
        >= MODERATE_EVIDENCE
    )

    df["spatial_support"] = (
        df["spatial_score"]
        >= MODERATE_EVIDENCE
    )

    df["temporal_support"] = (
        df["temporal_score"]
        >= MODERATE_EVIDENCE
    )

    def classify(row):

        score = row["risk_score"]

        strong = row[
            "strong_evidence_count"
        ]

        moderate = row[
            "moderate_evidence_count"
        ]

        persistence = row[
            "persistence_support"
        ]

        spatial = row[
            "spatial_support"
        ]

        # ----------------------------------------------------------
        # RED
        # ----------------------------------------------------------

        if (
            score >= RED_THRESHOLD
            and strong >= 3
            and (
                persistence
                or spatial
            )
        ):
            return "RED"

        # ----------------------------------------------------------
        # ORANGE
        # ----------------------------------------------------------

        if (
            score >= ORANGE_THRESHOLD
            and moderate >= 2
        ):
            return "ORANGE"

        # ----------------------------------------------------------
        # YELLOW
        # ----------------------------------------------------------

        if score >= YELLOW_THRESHOLD:

            return "YELLOW"

        # ----------------------------------------------------------
        # GREEN
        # ----------------------------------------------------------

        return "GREEN"

    df["risk_alert"] = (
        df
        .apply(
            classify,
            axis=1
        )
    )

    df["outbreak_signal"] = (
        df["risk_alert"]
        .isin(
            [
                "ORANGE",
                "RED",
            ]
        )
    )

    return df


# ============================================================================
# EXPLAINABILITY
# ============================================================================

def build_explanation(
    row
):

    evidence = []

    if row["baseline_score"] >= MODERATE_EVIDENCE:

        evidence.append(
            "historical baseline deviation "
            f"({row['baseline_score']:.1f})"
        )

    if row["anomaly_score"] >= MODERATE_EVIDENCE:

        evidence.append(
            "statistical anomaly "
            f"({row['anomaly_score']:.1f})"
        )

    if row["temporal_score"] >= MODERATE_EVIDENCE:

        evidence.append(
            "temporal acceleration "
            f"({row['temporal_score']:.1f})"
        )

    if row["persistence_score"] >= MODERATE_EVIDENCE:

        evidence.append(
            "persistent signal "
            f"({row['persistence_score']:.1f})"
        )

    if row["spatial_score"] >= MODERATE_EVIDENCE:

        evidence.append(
            "spatial propagation "
            f"({row['spatial_score']:.1f})"
        )

    if row["b8_pattern_score"] >= MODERATE_EVIDENCE:

        evidence.append(
            "Objective A atypical/emerging evidence "
            f"({row['b8_pattern_score']:.1f})"
        )

    if row["severity_score"] >= MODERATE_EVIDENCE:

        disease_id = (
            row.get(
                "best_matching_disease_id",
                None
            )
        )

        if pd.isna(disease_id):
            disease_text = "associated disease"
        else:
            disease_text = (
                f"disease {disease_id}"
            )

        evidence.append(
            f"severity burden from {disease_text} "
            f"({row['severity_score']:.1f})"
        )

    if not evidence:

        evidence_text = (
            "No major corroborating outbreak "
            "signals were detected."
        )

    else:

        evidence_text = (
            "Supporting evidence: "
            +
            "; ".join(evidence)
            +
            "."
        )

    return (
        f"Composite outbreak-risk score is "
        f"{row['risk_score']:.1f}, producing a "
        f"{row['risk_alert']} alert. "
        f"{evidence_text}"
    )


# ============================================================================
# MAIN COMPOSITE BUILD
# ============================================================================

def build_composite(
    b3,
    b4,
    b5,
    b6,
    b7,
    b8,
    b9,
):

    print("\nBuilding composite evidence table...")

    # ------------------------------------------------------------------
    # Standardize each evidence source.
    # ------------------------------------------------------------------

    b3_std = standardize_b3(
        b3
    )

    b4_std = standardize_generic(
        b4,
        [
            "anomaly_score",
            "outbreak_score",
            "composite_score",
            "risk_score",
        ],
        "anomaly_score",
    )

    b5_std = standardize_generic(
        b5,
        [
            "temporal_acceleration_score",
            "acceleration_score",
            "temporal_score",
        ],
        "temporal_score",
    )

    b6_std = standardize_generic(
        b6,
        [
            "persistence_score",
            "outbreak_persistence_score",
        ],
        "persistence_score",
    )

    b7_std = standardize_generic(
        b7,
        [
            "spatial_propagation_score",
            "spatial_score",
            "propagation_score",
        ],
        "spatial_score",
    )

    b8_std = standardize_b8(
        b8
    )

    b9_std = standardize_b9(
        b9
    )

    # ------------------------------------------------------------------
    # Master symptom/week table comes from B3.
    # ------------------------------------------------------------------

    master = b3_std[
        [
            "week",
            "symptom_id",
            "symptom_name",
            "baseline_score",
            "baseline_z_max",
            "baseline_deviation_max",
            "baseline_hospitals_elevated",
            "baseline_hospitals_observed",
        ]
    ].copy()

    # ------------------------------------------------------------------
    # Merge B4-B7.
    # ------------------------------------------------------------------

    for evidence_df in [
        b4_std,
        b5_std,
        b6_std,
        b7_std,
    ]:

        if (
            "week" in evidence_df.columns
            and
            "symptom_id" in evidence_df.columns
        ):

            master = master.merge(
                evidence_df,
                on=[
                    "week",
                    "symptom_id",
                ],
                how="left",
            )

    # ------------------------------------------------------------------
    # Attach Objective A / B8 evidence.
    # ------------------------------------------------------------------

    master = attach_b8_to_symptoms(
        master,
        b8_std,
        b3,
    )

    # ------------------------------------------------------------------
    # Attach B9 disease-level severity.
    # ------------------------------------------------------------------

    master = attach_disease_severity(
        master,
        b8_std,
        b9_std,
    )

    # ------------------------------------------------------------------
    # Fill missing evidence values.
    # ------------------------------------------------------------------

    evidence_columns = [
        "baseline_score",
        "anomaly_score",
        "temporal_score",
        "persistence_score",
        "spatial_score",
        "b8_pattern_score",
        "severity_score",
    ]

    for column in evidence_columns:

        if column not in master.columns:

            master[column] = 0.0

        master[column] = (
            pd.to_numeric(
                master[column],
                errors="coerce"
            )
            .fillna(0.0)
            .clip(
                0,
                100
            )
        )

    # ------------------------------------------------------------------
    # Composite score.
    # ------------------------------------------------------------------

    master = calculate_composite_score(
        master
    )

    # ------------------------------------------------------------------
    # Alert classification.
    # ------------------------------------------------------------------

    master = classify_alerts(
        master
    )

    # ------------------------------------------------------------------
    # Explanations.
    # ------------------------------------------------------------------

    master["risk_explanation"] = (
        master
        .apply(
            build_explanation,
            axis=1
        )
    )

    # ------------------------------------------------------------------
    # Sort.
    # ------------------------------------------------------------------

    master = (
        master
        .sort_values(
            [
                "week",
                "risk_score",
            ],
            ascending=[
                True,
                False,
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return master


# ============================================================================
# LATEST SUMMARY
# ============================================================================

def build_latest_summary(
    df
):

    latest_week = df[
        "week"
    ].max()

    latest = (
        df[
            df["week"] == latest_week
        ]
        .sort_values(
            "risk_score",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

    return latest


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 80)
    print("B10 - COMPOSITE OUTBREAK-RISK ENGINE")
    print("=" * 80)

    # ------------------------------------------------------------------
    # Load inputs.
    # ------------------------------------------------------------------

    b3 = load_b3()
    b4 = load_b4()
    b5 = load_b5()
    b6 = load_b6()
    b7 = load_b7()
    b8 = load_b8()
    b9 = load_b9()

    # ------------------------------------------------------------------
    # Build composite.
    # ------------------------------------------------------------------

    result = build_composite(
        b3,
        b4,
        b5,
        b6,
        b7,
        b8,
        b9,
    )

    latest = build_latest_summary(
        result
    )

    # ------------------------------------------------------------------
    # Save.
    # ------------------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    latest.to_csv(
        LATEST_OUTPUT_FILE,
        index=False
    )

    # ------------------------------------------------------------------
    # Summary.
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("B10 COMPLETE")
    print("=" * 80)

    print(
        f"Time range: "
        f"{result['week'].min()} → "
        f"{result['week'].max()}"
    )

    print(
        f"Total composite rows: "
        f"{len(result)}"
    )

    print("\nLatest risk alerts:")

    print(
        latest[
            "risk_alert"
        ]
        .value_counts()
        .to_string()
    )

    print(
        f"\nLatest outbreak signals: "
        f"{int(latest['outbreak_signal'].sum())}"
    )

    print(
        "\nStrongest current "
        "outbreak-risk signals:"
    )

    display_columns = [
        "symptom_id",
        "symptom_name",
        "risk_score",
        "risk_alert",
        "strong_evidence_count",
        "moderate_evidence_count",
        "baseline_score",
        "anomaly_score",
        "temporal_score",
        "persistence_score",
        "spatial_score",
        "b8_pattern_score",
        "severity_score",
        "best_matching_disease_id",
    ]

    available_columns = [
        c
        for c in display_columns
        if c in latest.columns
    ]

    print(
        latest[
            available_columns
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    # ------------------------------------------------------------------
    # Explanation.
    # ------------------------------------------------------------------

    if len(latest) > 0:

        strongest = latest.iloc[0]

        print(
            "\nTop outbreak-risk explanation:"
        )

        print(
            strongest[
                "risk_explanation"
            ]
        )

    # ------------------------------------------------------------------
    # Output paths.
    # ------------------------------------------------------------------

    print(
        f"\nMain output: "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Latest output: "
        f"{LATEST_OUTPUT_FILE}"
    )

    print("\n" + "=" * 80)
    print("B10 READY FOR REVIEW")
    print("=" * 80)


if __name__ == "__main__":
    main()
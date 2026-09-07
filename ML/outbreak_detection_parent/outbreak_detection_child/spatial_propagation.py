from pathlib import Path

import numpy as np
import pandas as pd


# ====================================================================
# CONFIGURATION
# ====================================================================

CURRENT_DIR = Path(__file__).resolve().parent

B2_FILE = CURRENT_DIR / "symptom_weekly_surveillance.csv"
B3_FILE = CURRENT_DIR / "symptom_historical_baseline.csv"

DISEASE_FILE = CURRENT_DIR / "disease_weekly_surveillance.csv"

DISEASE_EDGE_OUTPUT_FILE = (
    CURRENT_DIR / "disease_propagation_edges.csv"
)

HOSPITAL_FILE = (
    CURRENT_DIR
    / "../../../datasets/knowledge_tables/hospital_master.csv"
).resolve()

OUTPUT_FILE = CURRENT_DIR / "spatial_propagation.csv"
EDGE_OUTPUT_FILE = CURRENT_DIR / "spatial_propagation_edges.csv"
REGION_OUTPUT_FILE = CURRENT_DIR / "spatial_region_propagation.csv"


# --------------------------------------------------------------------
# Spatial signal thresholds
# --------------------------------------------------------------------

# Minimum positive deviation from local baseline to call a hospital
# spatially affected.
MIN_POSITIVE_DEVIATION = 10.0

# Minimum z-score for a strong local spatial signal.
MIN_Z_SCORE = 1.0

# Minimum cases before a hospital can participate in propagation.
MIN_CASES_FOR_AFFECTED_HOSPITAL = 3

# A newly affected hospital must show a meaningful increase.
MIN_NEW_HOSPITAL_GROWTH = 25.0

# Spatial alert thresholds.
YELLOW_SPATIAL_SCORE = 35
ORANGE_SPATIAL_SCORE = 55
RED_SPATIAL_SCORE = 75


# ====================================================================
# GENERAL HELPERS
# ====================================================================

def load_csv(path, name):

    if not path.exists():

        raise FileNotFoundError(
            f"{name} file not found:\n{path}"
        )

    df = pd.read_csv(path)

    print(
        f"{name} rows: {len(df)}"
    )

    return df


def normalize_week(df):

    df = df.copy()

    if "week" not in df.columns:

        raise ValueError(
            "Required column 'week' not found."
        )

    df["week"] = pd.to_datetime(
        df["week"],
        errors="coerce"
    )

    return df.dropna(
        subset=["week"]
    )


# ====================================================================
# LOAD B2
# ====================================================================

def load_b2():

    df = load_csv(
        B2_FILE,
        "B2"
    )

    required = [
        "week",
        "hospital_id",
        "symptom_id",
        "symptom_name",
        "case_count",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            f"B2 missing columns: {missing}"
        )

    df = normalize_week(df)

    df["case_count"] = pd.to_numeric(
        df["case_count"],
        errors="coerce"
    ).fillna(0)

    return df

# ====================================================================
# LOAD DISEASE SURVEILLANCE
# ====================================================================

def load_disease_surveillance():

    df = load_csv(
        DISEASE_FILE,
        "Disease surveillance"
    )

    required = [
        "week",
        "hospital_id",
        "disease_id",
        "case_count",
        "previous_cases",
        "growth_rate",
        "hospital_total_cases",
        "incidence_proportion",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            f"Disease surveillance missing columns: {missing}"
        )

    df = normalize_week(df)

    for column in [
        "case_count",
        "previous_cases",
        "growth_rate",
        "hospital_total_cases",
        "incidence_proportion",
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df["case_count"] = (
        df["case_count"]
        .fillna(0)
    )

    df["hospital_total_cases"] = (
        df["hospital_total_cases"]
        .fillna(0)
    )

    return df


# ====================================================================
# DISEASE SPATIAL STATE
# ====================================================================

def build_disease_spatial_state(
    disease_df,
    hospitals
):

    df = disease_df.merge(
        hospitals,
        on="hospital_id",
        how="left"
    )

    for column in [
        "hospital_name",
        "city",
        "state",
        "region",
    ]:

        if column not in df.columns:

            if column == "hospital_name":
                df[column] = df["hospital_id"]
            else:
                df[column] = "Unknown"

        df[column] = (
            df[column]
            .fillna("Unknown")
            .astype(str)
        )

    # ---------------------------------------------------------------
    # Growth rate.
    # ---------------------------------------------------------------

    df["growth_rate"] = pd.to_numeric(
        df["growth_rate"],
        errors="coerce"
    )

    # ---------------------------------------------------------------
    # A disease becomes spatially active when:
    #
    # 1. It has cases
    # 2. It has a meaningful positive growth rate
    #
    # We do NOT call every hospital containing a disease affected.
    # ---------------------------------------------------------------

    df["spatially_active"] = (
        (df["case_count"] >= MIN_CASES_FOR_AFFECTED_HOSPITAL)
        &
        (df["growth_rate"] >= MIN_NEW_HOSPITAL_GROWTH)
    )

    return df

# ====================================================================
# DISEASE PROPAGATION SUMMARY
# ====================================================================

def calculate_disease_propagation(
    disease_state
):

    df = disease_state.copy()

    df = df.sort_values(
        [
            "disease_id",
            "hospital_id",
            "week",
        ]
    )

    # ---------------------------------------------------------------
    # Previous spatially-active state
    # ---------------------------------------------------------------

    df["previous_active"] = (
        df.groupby(
            [
                "disease_id",
                "hospital_id",
            ]
        )["spatially_active"]
        .shift(1)
        .fillna(False)
    )

    # ---------------------------------------------------------------
    # Newly active hospital
    # ---------------------------------------------------------------

    df["newly_active"] = (
        df["spatially_active"]
        &
        ~df["previous_active"]
    )

    # ---------------------------------------------------------------
    # Aggregate disease-level spatial activity
    # ---------------------------------------------------------------

    summary = (
        df.groupby(
            [
                "week",
                "disease_id",
            ],
            as_index=False
        )
        .agg(
            disease_affected_hospitals=(
                "spatially_active",
                "sum"
            ),

            disease_newly_affected_hospitals=(
                "newly_active",
                "sum"
            ),

            disease_total_cases=(
                "case_count",
                "sum"
            ),

            disease_average_growth=(
                "growth_rate",
                "mean"
            ),
        )
    )

    return (
        df,
        summary
    )

# ====================================================================
# DISEASE PROPAGATION EDGES
# ====================================================================

def build_disease_propagation_edges(
    disease_state
):

    df = disease_state.copy()

    df = df.sort_values(
        [
            "disease_id",
            "hospital_id",
            "week",
        ]
    )

    df["previous_active"] = (
        df.groupby(
            [
                "disease_id",
                "hospital_id",
            ]
        )["spatially_active"]
        .shift(1)
        .fillna(False)
    )

    df["newly_active"] = (
        df["spatially_active"]
        &
        ~df["previous_active"]
    )

    rows = []

    for (
        week,
        disease_id
    ), group in df.groupby(
        [
            "week",
            "disease_id",
        ]
    ):

        targets = group[
            group["newly_active"]
        ]

        if targets.empty:
            continue

        sources = group[
            group["previous_active"]
        ]

        if sources.empty:
            continue

        for _, source in sources.iterrows():

            for _, target in targets.iterrows():

                if (
                    source["hospital_id"]
                    ==
                    target["hospital_id"]
                ):
                    continue

                # ---------------------------------------------------
                # Geographic relationship.
                # ---------------------------------------------------

                if (
                    source["city"]
                    ==
                    target["city"]
                ):

                    relation = "same_city"

                elif (
                    source["region"]
                    ==
                    target["region"]
                ):

                    relation = "same_region"

                else:

                    relation = "cross_region"

                rows.append(
                    {
                        "week": week,
                        "disease_id": disease_id,

                        "source_hospital_id":
                            source["hospital_id"],

                        "source_hospital_name":
                            source["hospital_name"],

                        "source_city":
                            source["city"],

                        "source_region":
                            source["region"],

                        "target_hospital_id":
                            target["hospital_id"],

                        "target_hospital_name":
                            target["hospital_name"],

                        "target_city":
                            target["city"],

                        "target_region":
                            target["region"],

                        "geographic_relation":
                            relation,

                        "target_growth_rate":
                            target["growth_rate"],
                    }
                )

    return pd.DataFrame(rows)

# ====================================================================
# DISEASE PROPAGATION SUMMARY
# ====================================================================

def summarize_disease_propagation(
    edges
):

    if edges.empty:

        return pd.DataFrame(
            columns=[
                "week",
                "disease_id",
                "disease_propagation_edges",
                "disease_source_hospitals",
                "disease_target_hospitals",
                "disease_same_city_edges",
                "disease_same_region_edges",
                "disease_cross_region_edges",
            ]
        )

    result = (
        edges.groupby(
            [
                "week",
                "disease_id",
            ],
            as_index=False
        )
        .agg(
            disease_propagation_edges=(
                "source_hospital_id",
                "count"
            ),

            disease_source_hospitals=(
                "source_hospital_id",
                "nunique"
            ),

            disease_target_hospitals=(
                "target_hospital_id",
                "nunique"
            ),

            disease_same_city_edges=(
                "geographic_relation",
                lambda x:
                (x == "same_city").sum()
            ),

            disease_same_region_edges=(
                "geographic_relation",
                lambda x:
                (x == "same_region").sum()
            ),

            disease_cross_region_edges=(
                "geographic_relation",
                lambda x:
                (x == "cross_region").sum()
            ),
        )
    )

    return result

# ====================================================================
# LOAD B3
# ====================================================================

def load_b3():

    df = load_csv(
        B3_FILE,
        "B3"
    )

    required = [
        "week",
        "hospital_id",
        "symptom_id",
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            f"B3 missing columns: {missing}"
        )

    df = normalize_week(df)

    numeric_columns = [
        "current_cases",
        "historical_mean",
        "historical_std",
        "deviation_from_baseline",
        "deviation_percent",
        "z_score",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


# ====================================================================
# LOAD HOSPITAL METADATA
# ====================================================================

def load_hospital_metadata():

    df = load_csv(
        HOSPITAL_FILE,
        "Hospital metadata"
    )

    required = [
        "hospital_id"
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:

        raise ValueError(
            f"Hospital metadata missing columns: {missing}"
        )

    # ---------------------------------------------------------------
    # Optional metadata fields.
    # ---------------------------------------------------------------

    defaults = {
        "hospital_name": "Unknown",
        "city": "Unknown",
        "state": "Unknown",
        "hospital_type": "Unknown",
        "level": "Unknown",
    }

    for column, default in defaults.items():

        if column not in df.columns:

            df[column] = default

    for column in [
        "hospital_id",
        "hospital_name",
        "city",
        "state",
        "hospital_type",
        "level",
    ]:

        df[column] = (
            df[column]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
        )

    df = df.drop_duplicates(
        subset=["hospital_id"]
    )

    # State is the geographic region available in the metadata.
    df["region"] = df["state"]

    return df[
        [
            "hospital_id",
            "hospital_name",
            "city",
            "state",
            "region",
            "hospital_type",
            "level",
        ]
    ]


# ====================================================================
# PREPARE LOCAL SPATIAL SIGNAL
# ====================================================================

def prepare_spatial_data(
    b2,
    b3,
    hospitals
):

    # ---------------------------------------------------------------
    # Start from B2 hospital/week/symptom surveillance.
    # ---------------------------------------------------------------

    df = b2.merge(
        hospitals,
        on="hospital_id",
        how="left"
    )

    # ---------------------------------------------------------------
    # Attach B3 local baseline.
    # ---------------------------------------------------------------

    baseline_columns = [
        "week",
        "hospital_id",
        "symptom_id",
    ]

    optional_baseline_columns = [
        "historical_mean",
        "historical_std",
        "deviation_from_baseline",
        "deviation_percent",
        "z_score",
    ]

    for column in optional_baseline_columns:

        if column in b3.columns:

            baseline_columns.append(
                column
            )

    baseline = b3[
        baseline_columns
    ].copy()

    df = df.merge(
        baseline,
        on=[
            "week",
            "hospital_id",
            "symptom_id",
        ],
        how="left"
    )

    # ---------------------------------------------------------------
    # Fill geography.
    # ---------------------------------------------------------------

    for column in [
        "hospital_name",
        "city",
        "state",
        "region",
    ]:

        df[column] = (
            df[column]
            .fillna("Unknown")
            .astype(str)
        )

    # ---------------------------------------------------------------
    # Numeric baseline fields.
    # ---------------------------------------------------------------

    for column in [
        "historical_mean",
        "historical_std",
        "deviation_from_baseline",
        "deviation_percent",
        "z_score",
    ]:

        if column not in df.columns:

            df[column] = np.nan

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # ---------------------------------------------------------------
    # A hospital is spatially affected only when the current
    # symptom burden is meaningfully elevated above its own
    # historical baseline.
    #
    # This is the key correction.
    # ---------------------------------------------------------------

    df["baseline_elevated"] = (
        (
            df["deviation_percent"]
            >= MIN_POSITIVE_DEVIATION
        )
        &
        (
            df["z_score"]
            >= MIN_Z_SCORE
        )
    )

    # ---------------------------------------------------------------
    # Minimum case-volume safeguard.
    # ---------------------------------------------------------------

    df["affected"] = (
        (
            df["case_count"]
            >= MIN_CASES_FOR_AFFECTED_HOSPITAL
        )
        &
        df["baseline_elevated"]
    )

    return df


# ====================================================================
# BUILD HOSPITAL SPATIAL STATE
# ====================================================================

def build_hospital_spatial_state(
    df
):

    result = (
        df.groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
                "hospital_id",
                "hospital_name",
                "city",
                "state",
                "region",
            ],
            as_index=False
        )
        .agg(
            cases=(
                "case_count",
                "sum"
            ),

            deviation_percent=(
                "deviation_percent",
                "mean"
            ),

            z_score=(
                "z_score",
                "mean"
            ),
        )
    )

    result["affected"] = (
        (
            result["cases"]
            >= MIN_CASES_FOR_AFFECTED_HOSPITAL
        )
        &
        (
            result["deviation_percent"]
            >= MIN_POSITIVE_DEVIATION
        )
        &
        (
            result["z_score"]
            >= MIN_Z_SCORE
        )
    )

    return result


# ====================================================================
# CALCULATE SPATIAL COVERAGE
# ====================================================================

def calculate_spatial_coverage(
    hospital_state
):

    result = (
        hospital_state
        .groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
            ],
            as_index=False
        )
        .agg(
            affected_hospitals=(
                "affected",
                "sum"
            ),

            total_hospitals=(
                "hospital_id",
                "nunique"
            ),

            total_cases=(
                "cases",
                "sum"
            ),
        )
    )

    result["hospital_coverage"] = np.where(
        result["total_hospitals"] > 0,
        result["affected_hospitals"]
        / result["total_hospitals"],
        0
    )

    return result


# ====================================================================
# GEOGRAPHIC REGION SPREAD
# ====================================================================

def calculate_geographic_spread(
    hospital_state
):

    affected = hospital_state[
        hospital_state["affected"]
    ].copy()

    if affected.empty:

        region_state = pd.DataFrame(
            columns=[
                "week",
                "symptom_id",
                "symptom_name",
                "region",
                "affected_hospitals",
                "cases",
            ]
        )

        summary = pd.DataFrame(
            columns=[
                "week",
                "symptom_id",
                "symptom_name",
                "affected_regions",
                "geographic_cases",
            ]
        )

        return (
            region_state,
            summary
        )

    region_state = (
        affected
        .groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
                "region",
            ],
            as_index=False
        )
        .agg(
            affected_hospitals=(
                "hospital_id",
                "nunique"
            ),

            cases=(
                "cases",
                "sum"
            ),
        )
    )

    summary = (
        region_state
        .groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
            ],
            as_index=False
        )
        .agg(
            affected_regions=(
                "region",
                "nunique"
            ),

            geographic_cases=(
                "cases",
                "sum"
            ),
        )
    )

    return (
        region_state,
        summary
    )


# ====================================================================
# CITY SPREAD
# ====================================================================

def calculate_city_spread(
    hospital_state
):

    affected = hospital_state[
        hospital_state["affected"]
    ]

    return (
        affected
        .groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
            ],
            as_index=False
        )
        .agg(
            affected_cities=(
                "city",
                "nunique"
            )
        )
    )


# ====================================================================
# TEMPORAL HOSPITAL PROPAGATION
# ====================================================================

def calculate_hospital_propagation(
    hospital_state
):

    df = hospital_state.copy()

    df = df.sort_values(
        [
            "symptom_id",
            "hospital_id",
            "week",
        ]
    )

    # ---------------------------------------------------------------
    # Previous affected state.
    # ---------------------------------------------------------------

    df["previous_affected"] = (
        df.groupby(
            [
                "symptom_id",
                "hospital_id",
            ]
        )["affected"]
        .shift(1)
        .fillna(False)
    )

    # ---------------------------------------------------------------
    # Previous case count.
    # ---------------------------------------------------------------

    df["previous_cases"] = (
        df.groupby(
            [
                "symptom_id",
                "hospital_id",
            ]
        )["cases"]
        .shift(1)
    )

    # ---------------------------------------------------------------
    # Current growth.
    # ---------------------------------------------------------------

    df["growth_rate"] = np.where(
        df["previous_cases"] > 0,
        (
            (
                df["cases"]
                - df["previous_cases"]
            )
            /
            df["previous_cases"]
        )
        * 100,
        np.nan
    )

    # ---------------------------------------------------------------
    # A newly affected hospital:
    #
    # 1. currently elevated
    # 2. was not elevated last week
    # 3. has meaningful current growth
    #
    # This prevents widespread common symptoms from being interpreted
    # as newly propagating.
    # ---------------------------------------------------------------

    df["newly_affected"] = (
        df["affected"]
        &
        ~df["previous_affected"]
        &
        (
            df["growth_rate"]
            >= MIN_NEW_HOSPITAL_GROWTH
        )
    )

    propagation = (
        df.groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
            ],
            as_index=False
        )
        .agg(
            newly_affected_hospitals=(
                "newly_affected",
                "sum"
            )
        )
    )

    return (
        df,
        propagation
    )


# ====================================================================
# BUILD PROPAGATION EDGES
# ====================================================================

def build_propagation_edges(
    hospital_state
):

    df = hospital_state.copy()

    df = df.sort_values(
        [
            "symptom_id",
            "hospital_id",
            "week",
        ]
    )

    # ---------------------------------------------------------------
    # Previous state.
    # ---------------------------------------------------------------

    df["previous_affected"] = (
        df.groupby(
            [
                "symptom_id",
                "hospital_id",
            ]
        )["affected"]
        .shift(1)
        .fillna(False)
    )

    df["previous_cases"] = (
        df.groupby(
            [
                "symptom_id",
                "hospital_id",
            ]
        )["cases"]
        .shift(1)
    )

    df["growth_rate"] = np.where(
        df["previous_cases"] > 0,
        (
            (
                df["cases"]
                - df["previous_cases"]
            )
            /
            df["previous_cases"]
        )
        * 100,
        np.nan
    )

    df["newly_affected"] = (
        df["affected"]
        &
        ~df["previous_affected"]
        &
        (
            df["growth_rate"]
            >= MIN_NEW_HOSPITAL_GROWTH
        )
    )

    rows = []

    # ---------------------------------------------------------------
    # Process symptom/week.
    # ---------------------------------------------------------------

    for (
        week,
        symptom_id,
        symptom_name
    ), group in df.groupby(
        [
            "week",
            "symptom_id",
            "symptom_name",
        ]
    ):

        new_group = group[
            group["newly_affected"]
        ]

        if new_group.empty:
            continue

        # -----------------------------------------------------------
        # Sources must have been affected in the previous week.
        # -----------------------------------------------------------

        source_group = group[
            group["previous_affected"]
        ]

        if source_group.empty:
            continue

        # -----------------------------------------------------------
        # Create source → newly affected target edges.
        # -----------------------------------------------------------

        for _, source in source_group.iterrows():

            for _, target in new_group.iterrows():

                if (
                    source["hospital_id"]
                    ==
                    target["hospital_id"]
                ):
                    continue

                # ---------------------------------------------------
                # Geographic relationship.
                # ---------------------------------------------------

                if (
                    source["city"]
                    ==
                    target["city"]
                ):

                    geographic_relation = (
                        "same_city"
                    )

                elif (
                    source["region"]
                    ==
                    target["region"]
                ):

                    geographic_relation = (
                        "same_region"
                    )

                else:

                    geographic_relation = (
                        "cross_region"
                    )

                rows.append(
                    {
                        "week": week,
                        "symptom_id": symptom_id,
                        "symptom_name": symptom_name,

                        "source_hospital_id":
                            source[
                                "hospital_id"
                            ],

                        "source_hospital_name":
                            source[
                                "hospital_name"
                            ],

                        "source_city":
                            source[
                                "city"
                            ],

                        "source_region":
                            source[
                                "region"
                            ],

                        "target_hospital_id":
                            target[
                                "hospital_id"
                            ],

                        "target_hospital_name":
                            target[
                                "hospital_name"
                            ],

                        "target_city":
                            target[
                                "city"
                            ],

                        "target_region":
                            target[
                                "region"
                            ],

                        "geographic_relation":
                            geographic_relation,

                        "target_growth_rate":
                            target[
                                "growth_rate"
                            ],
                    }
                )

    return pd.DataFrame(
        rows
    )


# ====================================================================
# PROPAGATION GRAPH SUMMARY
# ====================================================================

def summarize_propagation_graph(
    edges
):

    if edges.empty:

        return pd.DataFrame(
            columns=[
                "week",
                "symptom_id",
                "symptom_name",
                "propagation_edges",
                "source_hospitals",
                "target_hospitals",
                "same_city_edges",
                "same_region_edges",
                "cross_region_edges",
            ]
        )

    result = (
        edges.groupby(
            [
                "week",
                "symptom_id",
                "symptom_name",
            ],
            as_index=False
        )
        .agg(
            propagation_edges=(
                "source_hospital_id",
                "count"
            ),

            source_hospitals=(
                "source_hospital_id",
                "nunique"
            ),

            target_hospitals=(
                "target_hospital_id",
                "nunique"
            ),

            same_city_edges=(
                "geographic_relation",
                lambda x:
                (
                    x == "same_city"
                ).sum()
            ),

            same_region_edges=(
                "geographic_relation",
                lambda x:
                (
                    x == "same_region"
                ).sum()
            ),

            cross_region_edges=(
                "geographic_relation",
                lambda x:
                (
                    x == "cross_region"
                ).sum()
            ),
        )
    )

    return result


# ====================================================================
# SPATIAL SCORE
# ====================================================================

def calculate_spatial_score(
    row
):

    # ---------------------------------------------------------------
    # 1. Affected hospital coverage
    # Maximum = 30
    # ---------------------------------------------------------------

    coverage = row[
        "hospital_coverage"
    ]

    coverage_component = (
        min(
            max(
                coverage,
                0
            ),
            1
        )
        * 30
    )

    # ---------------------------------------------------------------
    # 2. Geographic spread
    # Maximum = 20
    # ---------------------------------------------------------------

    regions = row[
        "affected_regions"
    ]

    geographic_component = (
        min(
            max(
                regions - 1,
                0
            ) / 4,
            1
        )
        * 20
    )

    # ---------------------------------------------------------------
    # 3. Newly affected hospitals
    # Maximum = 30
    # ---------------------------------------------------------------

    new_hospitals = row[
        "newly_affected_hospitals"
    ]

    new_hospital_component = (
        min(
            max(
                new_hospitals,
                0
            ) / 5,
            1
        )
        * 30
    )

    # ---------------------------------------------------------------
    # 4. Propagation graph
    # Maximum = 20
    # ---------------------------------------------------------------

    edges = row[
        "propagation_edges"
    ]

    edge_component = (
        min(
            max(
                edges,
                0
            ) / 10,
            1
        )
        * 20
    )

    score = (
        coverage_component
        + geographic_component
        + new_hospital_component
        + edge_component
    )

    return round(
        min(
            max(
                score,
                0
            ),
            100
        ),
        2
    )


# ====================================================================
# SPATIAL ALERT
# ====================================================================

def classify_spatial_alert(
    row
):

    score = row[
        "spatial_propagation_score"
    ]

    affected = row[
        "affected_hospitals"
    ]

    regions = row[
        "affected_regions"
    ]

    new_hospitals = row[
        "newly_affected_hospitals"
    ]

    edges = row[
        "propagation_edges"
    ]

    # ---------------------------------------------------------------
    # RED
    #
    # Broad spatial spread + multiple newly affected hospitals +
    # actual propagation edges.
    # ---------------------------------------------------------------

    if (
        score >= RED_SPATIAL_SCORE
        and affected >= 6
        and regions >= 3
        and new_hospitals >= 3
        and edges >= 5
    ):

        return "RED"

    # ---------------------------------------------------------------
    # ORANGE
    # ---------------------------------------------------------------

    if (
        score >= ORANGE_SPATIAL_SCORE
        and affected >= 4
        and regions >= 2
        and (
            new_hospitals >= 2
            or edges >= 3
        )
    ):

        return "ORANGE"

    # ---------------------------------------------------------------
    # YELLOW
    # ---------------------------------------------------------------

    if (
        score >= YELLOW_SPATIAL_SCORE
        and affected >= 2
        and (
            new_hospitals >= 1
            or regions >= 2
            or edges >= 1
        )
    ):

        return "YELLOW"

    return "GREEN"


# ====================================================================
# MAIN B7
# ====================================================================

def run_b7():

    print("=" * 80)
    print("B7 - SPATIAL PROPAGATION")
    print("=" * 80)

    # ---------------------------------------------------------------
    # Load
    # ---------------------------------------------------------------

    b2 = load_b2()

    b3 = load_b3()

    disease_df = load_disease_surveillance()

    hospitals = (
        load_hospital_metadata()
    )

    # ---------------------------------------------------------------
    # Prepare local spatial evidence.
    # ---------------------------------------------------------------

    spatial_data = (
        prepare_spatial_data(
            b2,
            b3,
            hospitals
        )
    )

    hospital_state = (
        build_hospital_spatial_state(
            spatial_data
        )
    )

    print(
        f"Hospital spatial-state rows: "
        f"{len(hospital_state)}"
    )

    # ---------------------------------------------------------------
    # Spatial coverage.
    # ---------------------------------------------------------------

    coverage = (
        calculate_spatial_coverage(
            hospital_state
        )
    )

    # ---------------------------------------------------------------
    # Geographic spread.
    # ---------------------------------------------------------------

    (
        region_state,
        region_summary
    ) = calculate_geographic_spread(
        hospital_state
    )

    city_summary = (
        calculate_city_spread(
            hospital_state
        )
    )

    # ---------------------------------------------------------------
    # Temporal propagation.
    # ---------------------------------------------------------------

    (
        hospital_state,
        propagation
    ) = calculate_hospital_propagation(
        hospital_state
    )

    # ---------------------------------------------------------------
    # Propagation graph.
    # ---------------------------------------------------------------

    edges = (
        build_propagation_edges(
            hospital_state
        )
    )

    print(
        f"Propagation edges: "
        f"{len(edges)}"
    )

    # ---------------------------------------------------------------
    # Disease propagation
    # ---------------------------------------------------------------

    disease_state = build_disease_spatial_state(
        disease_df,
        hospitals
    )

    (
        disease_state,
        disease_summary
    ) = calculate_disease_propagation(
        disease_state
    )

    disease_edges = (
        build_disease_propagation_edges(
            disease_state
        )
    )

    print(
        f"Disease propagation edges: "
        f"{len(disease_edges)}"
    )

    disease_graph_summary = (
        summarize_disease_propagation(
            disease_edges
        )
    )

    graph_summary = (
        summarize_propagation_graph(
            edges
        )
    )

    # ---------------------------------------------------------------
    # Combine.
    # ---------------------------------------------------------------

    result = coverage.merge(
        region_summary,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    result = result.merge(
        city_summary,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    result = result.merge(
        propagation,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    result = result.merge(
        graph_summary,
        on=[
            "week",
            "symptom_id",
            "symptom_name",
        ],
        how="left"
    )

    # ---------------------------------------------------------------
    # Fill missing values.
    # ---------------------------------------------------------------

    numeric_columns = [
        "affected_regions",
        "affected_cities",
        "newly_affected_hospitals",
        "propagation_edges",
        "source_hospitals",
        "target_hospitals",
        "same_city_edges",
        "same_region_edges",
        "cross_region_edges",
    ]

    for column in numeric_columns:

        if column not in result.columns:

            result[column] = 0

        result[column] = (
            pd.to_numeric(
                result[column],
                errors="coerce"
            )
            .fillna(0)
        )

    # ---------------------------------------------------------------
    # Score.
    # ---------------------------------------------------------------

    result[
        "spatial_propagation_score"
    ] = result.apply(
        calculate_spatial_score,
        axis=1
    )

    # ---------------------------------------------------------------
    # Alert.
    # ---------------------------------------------------------------

    result[
        "spatial_alert"
    ] = result.apply(
        classify_spatial_alert,
        axis=1
    )

    result[
        "spatial_propagation_signal"
    ] = (
        result[
            "spatial_alert"
        ].isin(
            [
                "YELLOW",
                "ORANGE",
                "RED",
            ]
        )
    )

    # ---------------------------------------------------------------
    # Sort.
    # ---------------------------------------------------------------

    result = result.sort_values(
        [
            "week",
            "spatial_propagation_score",
        ],
        ascending=[
            True,
            False,
        ]
    )

    # ---------------------------------------------------------------
    # Save.
    # ---------------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    edges.to_csv(
        EDGE_OUTPUT_FILE,
        index=False
    )

    disease_edges.to_csv(
        DISEASE_EDGE_OUTPUT_FILE,
        index=False
    )

    disease_summary.to_csv(
        CURRENT_DIR / "disease_spatial_propagation.csv",
        index=False
    )

    region_state.to_csv(
        REGION_OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------------------------
    # Summary.
    # ---------------------------------------------------------------

    print()
    print(
        f"Output rows: {len(result)}"
    )

    print(
        f"Main output: {OUTPUT_FILE}"
    )

    print(
        f"Graph edges: {EDGE_OUTPUT_FILE}"
    )

    print(
        f"Region output: {REGION_OUTPUT_FILE}"
    )

    print()
    print(
        "Spatial alert summary:"
    )

    print(
        result[
            "spatial_alert"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print(
        "Spatial propagation signals:",
        int(
            result[
                "spatial_propagation_signal"
            ].sum()
        )
    )

    # ---------------------------------------------------------------
    # Latest week.
    # ---------------------------------------------------------------

    latest_week = result[
        "week"
    ].max()

    latest = result[
        result["week"] == latest_week
    ].copy()

    latest = latest.sort_values(
        "spatial_propagation_score",
        ascending=False
    )

    print()
    print(
        f"Latest surveillance week: "
        f"{latest_week.date()}"
    )

    print()

    print(
        latest[
            [
                "symptom_id",
                "symptom_name",
                "affected_hospitals",
                "total_hospitals",
                "hospital_coverage",
                "affected_regions",
                "affected_cities",
                "newly_affected_hospitals",
                "source_hospitals",
                "target_hospitals",
                "propagation_edges",
                "same_city_edges",
                "same_region_edges",
                "cross_region_edges",
                "spatial_propagation_score",
                "spatial_alert",
                "spatial_propagation_signal",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print()
    print("=" * 80)
    print("B7 COMPLETE")
    print("=" * 80)

    return result


# ====================================================================
# ENTRY POINT
# ====================================================================

if __name__ == "__main__":

    run_b7()
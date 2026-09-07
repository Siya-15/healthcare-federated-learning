from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

BASE_DIR = (
    PROJECT_ROOT
    / "ML"
    / "emerging_symptoms"
    / "a9_validation"
    / "scenarios"
)


TARGET_PATTERNS = {
    "atypical_known_disease": [
        "Fever",
        "Headache",
        "Muscle Pain",
        "Nausea",
        "Rash",
        "Vomiting",
    ],
    "unexplained_emerging_pattern": [
        "Breathlessness",
        "Chest Pain",
        "Diarrhoea",
        "Loss of Appetite",
        "Night Sweats",
        "Runny Nose",
    ],
}


def load_scenario(name):

    path = (
        BASE_DIR
        / name
        / "combined_validation.csv"
    )

    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(
        path,
        keep_default_na=False
    )

    df["visit_timestamp"] = pd.to_datetime(
        df["visit_timestamp"]
    )

    return df


def calculate_pattern_prevalence(
    df,
    symptoms
):

    mask = pd.Series(
        True,
        index=df.index
    )

    for symptom in symptoms:
        mask &= (
            pd.to_numeric(
                df[symptom],
                errors="coerce"
            )
            .fillna(0)
            > 0
        )

    return mask.mean()


def calculate_daily_pattern(
    df,
    symptoms
):

    rows = []

    for date, day_data in df.groupby(
        df["visit_timestamp"].dt.date
    ):

        prevalence = calculate_pattern_prevalence(
            day_data,
            symptoms
        )

        rows.append({
            "date": date,
            "records": len(day_data),
            "pattern_prevalence": prevalence,
        })

    return pd.DataFrame(rows)


def main():

    print("=" * 80)
    print("A9 - VALIDATION DATASET SANITY CHECK")
    print("=" * 80)

    normal = load_scenario(
        "normal"
    )

    atypical = load_scenario(
        "atypical_known_disease"
    )

    unexplained = load_scenario(
        "unexplained_emerging_pattern"
    )

    print("\nDATASET SIZES")
    print("-" * 80)

    for name, df in [
        ("Normal", normal),
        ("Atypical", atypical),
        ("Unexplained", unexplained),
    ]:

        print(
            f"{name:12}: "
            f"{len(df):,} records | "
            f"{df['hospital_id'].nunique()} hospitals | "
            f"{df['visit_timestamp'].nunique()} dates"
        )

    # ------------------------------------------------------------------
    # Check the two injected patterns.
    # ------------------------------------------------------------------

    print("\nPATTERN PREVALENCE")
    print("-" * 80)

    for scenario, symptoms in TARGET_PATTERNS.items():

        print(
            f"\n{scenario.upper()}"
        )

        print(
            "Pattern: "
            + " + ".join(symptoms)
        )

        for name, df in [
            ("Normal", normal),
            ("Target", (
                atypical
                if scenario == "atypical_known_disease"
                else unexplained
            )),
        ]:

            prevalence = (
                calculate_pattern_prevalence(
                    df,
                    symptoms
                )
            )

            print(
                f"  {name:8}: "
                f"{prevalence * 100:.2f}%"
            )

    # ------------------------------------------------------------------
    # Daily progression.
    # ------------------------------------------------------------------

    print("\nDAILY PROGRESSION")
    print("-" * 80)

    for scenario, symptoms in TARGET_PATTERNS.items():

        df = (
            atypical
            if scenario == "atypical_known_disease"
            else unexplained
        )

        daily = calculate_daily_pattern(
            df,
            symptoms
        )

        print(
            f"\n{scenario.upper()}"
        )

        print(
            daily.to_string(
                index=False,
                formatters={
                    "pattern_prevalence":
                        lambda x:
                        f"{x * 100:.2f}%"
                }
            )
        )

    # ------------------------------------------------------------------
    # Hospital spread.
    # ------------------------------------------------------------------

    print("\nHOSPITAL SPREAD")
    print("-" * 80)

    for scenario, symptoms in TARGET_PATTERNS.items():

        df = (
            atypical
            if scenario == "atypical_known_disease"
            else unexplained
        )

        affected = []

        for hospital_id, hospital_data in df.groupby(
            "hospital_id"
        ):

            prevalence = (
                calculate_pattern_prevalence(
                    hospital_data,
                    symptoms
                )
            )

            affected.append({
                "hospital_id": hospital_id,
                "prevalence": prevalence,
            })

        hospital_df = pd.DataFrame(
            affected
        )

        print(
            f"\n{scenario.upper()}"
        )

        print(
            hospital_df.to_string(
                index=False,
                formatters={
                    "prevalence":
                        lambda x:
                        f"{x * 100:.2f}%"
                }
            )
        )

    print("\n" + "=" * 80)
    print("A9 SANITY CHECK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
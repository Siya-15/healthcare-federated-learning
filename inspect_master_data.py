from sqlalchemy import text
from database import get_engine


TABLES = [
    "hospital_master",
    "disease_master",
    "symptom_master",
    "treatment_master",
    "complication_master",
    "severity_master",
    "disease_symptom_mapping",
    "disease_treatment_mapping",
    "disease_complication_mapping",
]


def main():
    engine = get_engine()

    with engine.connect() as conn:

        for table in TABLES:
            print("\n" + "=" * 80)
            print(table.upper())
            print("=" * 80)

            result = conn.execute(
                text(f'SELECT * FROM "{table}"')
            )

            rows = result.fetchall()
            columns = result.keys()

            print("Columns:")
            print(" | ".join(columns))

            print(f"\nRows: {len(rows)}")

            for row in rows[:30]:
                print(" | ".join(str(value) for value in row))


if __name__ == "__main__":
    main()
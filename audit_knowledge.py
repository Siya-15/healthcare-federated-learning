from sqlalchemy import text
from database import get_engine


def main():
    engine = get_engine()

    with engine.connect() as conn:

        print("\n" + "=" * 80)
        print("1. SYMPTOMS NEVER GENERATED")
        print("=" * 80)

        rows = conn.execute(text("""
            SELECT
                s.symptom_id,
                s.symptom_name
            FROM symptom_master s
            LEFT JOIN encounter_symptoms es
                ON s.symptom_id = es.symptom_id
            WHERE es.symptom_id IS NULL
            ORDER BY s.symptom_id
        """))

        for row in rows:
            print(row.symptom_id, "|", row.symptom_name)


        print("\n" + "=" * 80)
        print("2. SYMPTOMS PER DISEASE")
        print("=" * 80)

        rows = conn.execute(text("""
            SELECT
                d.disease_id,
                d.disease_name,
                COUNT(DISTINCT m.symptom_id) AS mapped_symptoms
            FROM disease_master d
            LEFT JOIN disease_symptom_mapping m
                ON d.disease_id = m.disease_id
            GROUP BY d.disease_id, d.disease_name
            ORDER BY d.disease_id
        """))

        for row in rows:
            print(
                row.disease_id,
                "|",
                row.disease_name,
                "| symptoms:",
                row.mapped_symptoms
            )


        print("\n" + "=" * 80)
        print("3. TREATMENTS PER DISEASE")
        print("=" * 80)

        rows = conn.execute(text("""
            SELECT
                d.disease_id,
                d.disease_name,
                COUNT(m.treatment_id) AS mapped_treatments
            FROM disease_master d
            LEFT JOIN disease_treatment_mapping m
                ON d.disease_id = m.disease_id
            GROUP BY d.disease_id, d.disease_name
            ORDER BY d.disease_id
        """))

        for row in rows:
            print(
                row.disease_id,
                "|",
                row.disease_name,
                "| treatments:",
                row.mapped_treatments
            )


        print("\n" + "=" * 80)
        print("4. COMPLICATIONS PER DISEASE")
        print("=" * 80)

        rows = conn.execute(text("""
            SELECT
                d.disease_id,
                d.disease_name,
                COUNT(m.complication_id) AS mapped_complications
            FROM disease_master d
            LEFT JOIN disease_complication_mapping m
                ON d.disease_id = m.disease_id
            GROUP BY d.disease_id, d.disease_name
            ORDER BY d.disease_id
        """))

        for row in rows:
            print(
                row.disease_id,
                "|",
                row.disease_name,
                "| complications:",
                row.mapped_complications
            )


        print("\n" + "=" * 80)
        print("5. DISEASES WITH NO TREATMENT MAPPING")
        print("=" * 80)

        rows = conn.execute(text("""
            SELECT
                d.disease_id,
                d.disease_name
            FROM disease_master d
            LEFT JOIN disease_treatment_mapping m
                ON d.disease_id = m.disease_id
            WHERE m.disease_id IS NULL
        """))

        for row in rows:
            print(row.disease_id, "|", row.disease_name)


        print("\n" + "=" * 80)
        print("6. DISEASES WITH NO COMPLICATION MAPPING")
        print("=" * 80)

        rows = conn.execute(text("""
            SELECT
                d.disease_id,
                d.disease_name
            FROM disease_master d
            LEFT JOIN disease_complication_mapping m
                ON d.disease_id = m.disease_id
            WHERE m.disease_id IS NULL
        """))

        for row in rows:
            print(row.disease_id, "|", row.disease_name)


        print("\n" + "=" * 80)
        print("7. DISEASE SYMPTOM FREQUENCY DISTRIBUTION")
        print("=" * 80)

        rows = conn.execute(text("""
            SELECT
                frequency,
                COUNT(*) AS count
            FROM disease_symptom_mapping
            GROUP BY frequency
            ORDER BY frequency
        """))

        for row in rows:
            print(row.frequency, "|", row.count)


        print("\n" + "=" * 80)
        print("8. DISEASE TREATMENT PRIORITY")
        print("=" * 80)

        rows = conn.execute(text("""
            SELECT
                disease_id,
                severity_id,
                MIN(priority) AS highest_priority,
                COUNT(*) AS treatment_options
            FROM disease_treatment_mapping
            GROUP BY disease_id, severity_id
            ORDER BY disease_id, severity_id
        """))

        for row in rows:
            print(
                row.disease_id,
                "| severity:",
                row.severity_id,
                "| first priority:",
                row.highest_priority,
                "| options:",
                row.treatment_options
            )


if __name__ == "__main__":
    main()
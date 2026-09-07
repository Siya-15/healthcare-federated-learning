from sqlalchemy import text
from database import get_engine


def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def scalar(conn, query):
    return conn.execute(text(query)).scalar()


def main():
    engine = get_engine()

    with engine.connect() as conn:

        # ================================================================
        # 1. TABLE ROW COUNTS
        # ================================================================
        section("1. TABLE ROW COUNTS")

        tables = [
            "patient_encounter",
            "encounter_symptoms",
            "encounter_treatments",
            "encounter_complications",
            "disease_master",
            "symptom_master",
            "treatment_master",
            "complication_master",
            "severity_master",
            "hospital_master",
            "disease_symptom_mapping",
            "disease_treatment_mapping",
            "disease_complication_mapping",
            "disease_generation_config",
            "hospital_generation_config",
            "vital_range_config",
        ]

        for table in tables:
            count = scalar(conn, f'SELECT COUNT(*) FROM "{table}"')
            print(f"{table:<35} {count:>8}")

        # ================================================================
        # 2. HOSPITAL DISTRIBUTION
        # ================================================================
        section("2. ENCOUNTERS BY HOSPITAL")

        rows = conn.execute(text("""
            SELECT hospital_id, COUNT(*) AS encounters
            FROM patient_encounter
            GROUP BY hospital_id
            ORDER BY hospital_id
        """))

        for row in rows:
            print(f"{row.hospital_id:<15} {row.encounters:>8}")

        # ================================================================
        # 3. NULL / MISSING VALUES
        # ================================================================
        section("3. NULL VALUES — PATIENT_ENCOUNTER")

        columns = [
            "encounter_id",
            "patient_id",
            "hospital_id",
            "visit_timestamp",
            "age",
            "gender",
            "occupation",
            "district",
            "state",
            "temperature",
            "heart_rate",
            "respiratory_rate",
            "systolic_bp",
            "diastolic_bp",
            "spo2",
            "disease_id",
            "severity_id",
            "admission_status",
            "visit_type",
            "symptom_onset_days",
            "travel_history",
            "vaccination_status",
            "discharge_status",
            "recovery_days",
        ]

        for column in columns:
            count = scalar(
                conn,
                f'SELECT COUNT(*) FROM patient_encounter '
                f'WHERE "{column}" IS NULL'
            )
            if count > 0:
                print(f"{column:<30} NULLS: {count}")

        print("Done checking nulls.")

        # ================================================================
        # 4. DISTINCT VALUES
        # ================================================================
        section("4. CATEGORICAL VALUE DISTRIBUTIONS")

        categorical = [
            "gender",
            "admission_status",
            "visit_type",
            "vaccination_status",
            "discharge_status",
            "severity_id",
        ]

        for column in categorical:
            print(f"\n--- {column} ---")

            rows = conn.execute(text(f"""
                SELECT "{column}", COUNT(*) AS count
                FROM patient_encounter
                GROUP BY "{column}"
                ORDER BY count DESC
            """))

            for row in rows:
                print(f"{str(row[0]):<30} {row[1]:>8}")

        # ================================================================
        # 5. NUMERIC RANGES
        # ================================================================
        section("5. CLINICAL NUMERIC RANGES")

        numeric_columns = [
            "age",
            "temperature",
            "heart_rate",
            "respiratory_rate",
            "systolic_bp",
            "diastolic_bp",
            "spo2",
            "symptom_onset_days",
            "recovery_days",
        ]

        for column in numeric_columns:
            row = conn.execute(text(f"""
                SELECT
                    MIN("{column}") AS min_value,
                    MAX("{column}") AS max_value,
                    AVG("{column}") AS avg_value
                FROM patient_encounter
            """)).fetchone()

            print(
                f"{column:<25}"
                f" min={row.min_value!s:<10}"
                f" max={row.max_value!s:<10}"
                f" avg={round(float(row.avg_value), 2) if row.avg_value is not None else None}"
            )

        # ================================================================
        # 6. REFERENTIAL INTEGRITY
        # ================================================================
        section("6. REFERENTIAL INTEGRITY")

        checks = {

            "Invalid hospital_id": """
                SELECT COUNT(*)
                FROM patient_encounter p
                LEFT JOIN hospital_master h
                    ON p.hospital_id = h.hospital_id
                WHERE h.hospital_id IS NULL
            """,

            "Invalid disease_id": """
                SELECT COUNT(*)
                FROM patient_encounter p
                LEFT JOIN disease_master d
                    ON p.disease_id = d.disease_id
                WHERE d.disease_id IS NULL
            """,

            "Invalid severity_id": """
                SELECT COUNT(*)
                FROM patient_encounter p
                LEFT JOIN severity_master s
                    ON p.severity_id = s.severity_id
                WHERE s.severity_id IS NULL
            """,

            "Orphan encounter_symptoms": """
                SELECT COUNT(*)
                FROM encounter_symptoms s
                LEFT JOIN patient_encounter p
                    ON s.encounter_id = p.encounter_id
                WHERE p.encounter_id IS NULL
            """,

            "Invalid symptom_id": """
                SELECT COUNT(*)
                FROM encounter_symptoms e
                LEFT JOIN symptom_master s
                    ON e.symptom_id = s.symptom_id
                WHERE s.symptom_id IS NULL
            """,

            "Orphan encounter_treatments": """
                SELECT COUNT(*)
                FROM encounter_treatments t
                LEFT JOIN patient_encounter p
                    ON t.encounter_id = p.encounter_id
                WHERE p.encounter_id IS NULL
            """,

            "Invalid treatment_id": """
                SELECT COUNT(*)
                FROM encounter_treatments e
                LEFT JOIN treatment_master t
                    ON e.treatment_id = t.treatment_id
                WHERE t.treatment_id IS NULL
            """,

            "Orphan encounter_complications": """
                SELECT COUNT(*)
                FROM encounter_complications c
                LEFT JOIN patient_encounter p
                    ON c.encounter_id = p.encounter_id
                WHERE p.encounter_id IS NULL
            """,

            "Invalid complication_id": """
                SELECT COUNT(*)
                FROM encounter_complications e
                LEFT JOIN complication_master c
                    ON e.complication_id = c.complication_id
                WHERE c.complication_id IS NULL
            """,
        }

        for name, query in checks.items():
            count = scalar(conn, query)
            status = "PASS" if count == 0 else "FAIL"
            print(f"{status:<6} {name:<35} {count}")

        # ================================================================
        # 7. ENCOUNTER COVERAGE
        # ================================================================
        section("7. ENCOUNTER COVERAGE")

        total = scalar(conn, """
            SELECT COUNT(*) FROM patient_encounter
        """)

        checks = {
            "Encounters with symptoms": """
                SELECT COUNT(DISTINCT encounter_id)
                FROM encounter_symptoms
            """,

            "Encounters with treatments": """
                SELECT COUNT(DISTINCT encounter_id)
                FROM encounter_treatments
            """,

            "Encounters with complications": """
                SELECT COUNT(DISTINCT encounter_id)
                FROM encounter_complications
            """,
        }

        for name, query in checks.items():
            count = scalar(conn, query)
            percentage = (count / total * 100) if total else 0
            print(
                f"{name:<35}"
                f"{count:>8}"
                f" ({percentage:.2f}%)"
            )

        # ================================================================
        # 8. SYMPTOM STATISTICS
        # ================================================================
        section("8. SYMPTOM STATISTICS")

        total_symptoms = scalar(conn, """
            SELECT COUNT(*) FROM encounter_symptoms
        """)

        unique_symptoms = scalar(conn, """
            SELECT COUNT(DISTINCT symptom_id)
            FROM encounter_symptoms
        """)

        print(f"Total symptom records : {total_symptoms}")
        print(f"Unique symptoms       : {unique_symptoms}")

        # ================================================================
        # 9. TREATMENT STATISTICS
        # ================================================================
        section("9. TREATMENT STATISTICS")

        total_treatments = scalar(conn, """
            SELECT COUNT(*) FROM encounter_treatments
        """)

        administered = scalar(conn, """
            SELECT COUNT(*)
            FROM encounter_treatments
            WHERE administered = TRUE
        """)

        ai_recommended = scalar(conn, """
            SELECT COUNT(*)
            FROM encounter_treatments
            WHERE recommended_by_ai = TRUE
        """)

        doctor_accepted = scalar(conn, """
            SELECT COUNT(*)
            FROM encounter_treatments
            WHERE accepted_by_doctor = TRUE
        """)

        print(f"Total treatment records : {total_treatments}")
        print(f"Administered            : {administered}")
        print(f"AI recommended          : {ai_recommended}")
        print(f"Doctor accepted         : {doctor_accepted}")

        # ================================================================
        # 10. COMPLICATION STATISTICS
        # ================================================================
        section("10. COMPLICATION STATISTICS")

        total_complications = scalar(conn, """
            SELECT COUNT(*) FROM encounter_complications
        """)

        resolved = scalar(conn, """
            SELECT COUNT(*)
            FROM encounter_complications
            WHERE resolved = TRUE
        """)

        print(f"Total complication records : {total_complications}")
        print(f"Resolved complications     : {resolved}")

        # ================================================================
        # 11. DATA QUALITY RULES
        # ================================================================
        section("11. BASIC DATA QUALITY CHECKS")

        quality_checks = {

            "Age outside 0-120": """
                SELECT COUNT(*)
                FROM patient_encounter
                WHERE age < 0 OR age > 120
            """,

            "SpO2 outside 0-100": """
                SELECT COUNT(*)
                FROM patient_encounter
                WHERE spo2 < 0 OR spo2 > 100
            """,

            "Negative symptom onset": """
                SELECT COUNT(*)
                FROM patient_encounter
                WHERE symptom_onset_days < 0
            """,

            "Negative recovery days": """
                SELECT COUNT(*)
                FROM patient_encounter
                WHERE recovery_days < 0
            """,

            "Invalid heart rate": """
                SELECT COUNT(*)
                FROM patient_encounter
                WHERE heart_rate <= 0
            """,

            "Invalid respiratory rate": """
                SELECT COUNT(*)
                FROM patient_encounter
                WHERE respiratory_rate <= 0
            """,

            "Invalid systolic BP": """
                SELECT COUNT(*)
                FROM patient_encounter
                WHERE systolic_bp <= 0
            """,

            "Invalid diastolic BP": """
                SELECT COUNT(*)
                FROM patient_encounter
                WHERE diastolic_bp <= 0
            """,

            "Temperature <= 0": """
                SELECT COUNT(*)
                FROM patient_encounter
                WHERE temperature <= 0
            """,
        }

        for name, query in quality_checks.items():
            count = scalar(conn, query)
            status = "PASS" if count == 0 else "FAIL"
            print(f"{status:<6} {name:<35} {count}")

        # ================================================================
        # 12. DUPLICATE CHECKS
        # ================================================================
        section("12. DUPLICATE CHECKS")

        duplicate_encounters = scalar(conn, """
            SELECT COUNT(*)
            FROM (
                SELECT encounter_id
                FROM patient_encounter
                GROUP BY encounter_id
                HAVING COUNT(*) > 1
            ) x
        """)

        duplicate_patients = scalar(conn, """
            SELECT COUNT(*)
            FROM (
                SELECT patient_id
                FROM patient_encounter
                GROUP BY patient_id
                HAVING COUNT(*) > 1
            ) x
        """)

        print(f"Duplicate encounter IDs : {duplicate_encounters}")
        print(f"Patients with >1 visit  : {duplicate_patients}")

        # ================================================================
        # END
        # ================================================================
        section("AUDIT COMPLETE")


if __name__ == "__main__":
    main()
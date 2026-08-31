from database import get_engine
import pandas as pd
from sqlalchemy import text

engine = get_engine()

tables = [
    "patient_encounter",
    "encounter_symptoms",
    "encounter_treatments",
    "encounter_complications",
]

with engine.connect() as connection:

    for table in tables:

        query = f"""
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name = '{table}'
        ORDER BY ordinal_position
        """

        df = pd.read_sql(
            text(query),
            connection
        )

        print("\n" + "=" * 60)
        print(table.upper())
        print("=" * 60)

        print(
            df.to_string(index=False)
        )
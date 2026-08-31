from database import get_engine
import pandas as pd
from sqlalchemy import text

engine = get_engine()

query = """
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'patient_encounter'
ORDER BY ordinal_position
"""

with engine.connect() as connection:
    df = pd.read_sql(
        text(query),
        connection
    )

print("=" * 60)
print("PATIENT ENCOUNTER SCHEMA")
print("=" * 60)

print(
    df.to_string(index=False)
)
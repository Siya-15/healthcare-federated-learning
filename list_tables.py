from database import get_engine
import pandas as pd
from sqlalchemy import text

engine = get_engine()

query = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name
"""

with engine.connect() as connection:
    df = pd.read_sql(
        text(query),
        connection
    )

print(df.to_string(index=False))
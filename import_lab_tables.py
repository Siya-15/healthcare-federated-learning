import pandas as pd
from database import get_engine
from sqlalchemy import text


engine = get_engine()

BASE = "datasets/knowledge tables"


def import_table(csv_name, table_name):

    path = f"{BASE}/{csv_name}"

    df = pd.read_csv(
        path,
        keep_default_na=False
    )

    # Convert genuinely empty cells to None
    df = df.map(lambda x: None if x == "" else x)

    with engine.begin() as conn:
        conn.execute(
            text(f"TRUNCATE TABLE {table_name} CASCADE")
        )

    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False
    )

    print(f"{table_name}: {len(df)} rows imported")


import_table(
    "imaging_master.csv",
    "imaging_master"
)

import_table(
    "disease_imaging_mapping.csv",
    "disease_imaging_mapping"
)

print("\nImaging tables imported successfully.")
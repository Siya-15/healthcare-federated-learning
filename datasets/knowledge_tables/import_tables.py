import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# DATABASE CONNECTION
# ==========================================================

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "federatedProject_db")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ==========================================================
# READ CSV
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent
file_path = BASE_DIR / "disease_complication_mapping.csv"

df = pd.read_csv(
    file_path,
    encoding="utf-8-sig",
    dtype=str
)

# ==========================================================
# CLEAN COLUMN NAMES
# ==========================================================

df.columns = (
    df.columns
      .str.strip()
      .str.lower()
      .str.replace(" ", "_", regex=False)
)

# ==========================================================
# CLEAN VALUES
# ==========================================================

for col in df.columns:
    df[col] = (
        df[col]
        .fillna("")
        .astype(str)
        .str.replace("\u00A0", "", regex=False)
        .str.strip()
    )



# ==========================================================
# TRUNCATE TABLE
# ==========================================================

with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE disease_complication_mapping CASCADE"))

# ==========================================================
# INSERT ROW BY ROW
# ==========================================================

print("=" * 70)
print("STARTING IMPORT")
print("=" * 70)

for index, row in df.iterrows():

    try:

        pd.DataFrame([row]).to_sql(
            "disease_complication_mapping",
            engine,
            if_exists="append",
            index=False
        )

        print(f"✓ Row {index + 1} imported")

    except Exception as e:

        print("\n")
        print("=" * 70)
        print(f"FAILED AT ROW {index + 1}")
        print("=" * 70)

        print(row)

        print("\nException:\n")
        print(e)

        break

print("\nFinished.")
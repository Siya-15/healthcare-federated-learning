from loader import load_all_tables

tables = load_all_tables()

for name, df in tables.items():
    print(f"{name}: {len(df)} rows")
import pandas as pd

from database import get_engine


TABLES = [

    # Knowledge Base
    "hospital_master",
    "disease_master",
    "symptom_master",
    "treatment_master",
    "severity_master",
    "complication_master",

    "disease_symptom_mapping",
    "disease_treatment_mapping",
    "disease_complication_mapping",

    # Laboratory
    "lab_master",
    "disease_lab_mapping",

    #Imaging
    "imaging_master",
    "disease_imaging_mapping",

    # Config
    "disease_generation_config",
    "hospital_generation_config",
    "vital_range_config"
]


def load_all_tables():

    engine = get_engine()

    tables = {}

    for table in TABLES:

        print(f"Loading {table}...")

        tables[table] = pd.read_sql(
            f"SELECT * FROM {table}",
            engine
        )

    print("\nAll tables loaded successfully.\n")

    return tables
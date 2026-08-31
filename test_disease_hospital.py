from collections import Counter

from generators.disease_generator import DiseaseGenerator
from models.encounter import Encounter
from simulation.simulation_context import SimulationContext

# If your import paths are different, adjust these two lines.


# ---------------------------------------------------------
# MOCK TABLES
# ---------------------------------------------------------

# IMPORTANT:
# Use your existing table-loading code here.
# If you already have a loader such as load_all_tables(),
# import and use that instead.

from loader import load_all_tables


tables = load_all_tables()

disease_generator = DiseaseGenerator(tables)


# ---------------------------------------------------------
# TEST SETTINGS
# ---------------------------------------------------------

HOSPITALS = [
    "H001",
    "H002",
    "H003",
    "H004",
    "H005",
    "H006",
    "H007",
    "H008",
    "H009",
    "H010"
]

N = 1000


# ---------------------------------------------------------
# TEST
# ---------------------------------------------------------

for hospital_id in HOSPITALS:

    counter = Counter()

    context = SimulationContext(
        current_date=None,
        hospital_id=hospital_id,
        season="Summer",
        outbreak_active=False
    )

    for _ in range(N):

        encounter = Encounter()

        # Age is needed because DiseaseGenerator
        # applies age-based multipliers.
        encounter.demographics.age = 35

        disease_generator.generate(
            encounter,
            context
        )

        counter[encounter.disease_id] += 1

    print()
    print("=" * 60)
    print(f"HOSPITAL: {hospital_id}")
    print("=" * 60)

    for disease_id in sorted(counter):

        count = counter[disease_id]

        percentage = (count / N) * 100

        print(
            f"{disease_id}: "
            f"{count:4d} "
            f"({percentage:5.2f}%)"
        )
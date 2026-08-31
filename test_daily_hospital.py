from generators.vitals_generator import VitalGenerator
from loader import load_all_tables
from models.encounter import Encounter

tables = load_all_tables()

encounter = Encounter()

vitals = VitalGenerator(tables)

vitals.generate(encounter)

print("\nVitals")
print("-" * 40)

print(f"Temperature : {encounter.vitals.temperature} °C")
print(f"Heart Rate  : {encounter.vitals.heart_rate} bpm")
print(f"SpO₂        : {encounter.vitals.spo2} %")
print(
    f"Blood Pressure : "
    f"{encounter.vitals.systolic_bp}/"
    f"{encounter.vitals.diastolic_bp}"
)
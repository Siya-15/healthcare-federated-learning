import random


class VitalGenerator:

    def __init__(self, tables):

        self.vital_config = tables["vital_range_config"]

    def get_config(self, disease_id, severity_id):

        return self.vital_config[

            (self.vital_config["disease_id"] == disease_id) &

            (self.vital_config["severity_id"] == severity_id)

        ].iloc[0]

    def generate(self, encounter):

        config = self.get_config(

            encounter.disease_id,

            encounter.severity_id

        )

        encounter.vitals.temperature = float(
            round(
                random.uniform(
                    float(config["temperature_min"]),
                    float(config["temperature_max"])
                ),
                1
            )
        )

        encounter.vitals.heart_rate = random.randint(

            int(config["heart_rate_min"]),

            int(config["heart_rate_max"])

        )

        encounter.vitals.respiratory_rate = random.randint(
            int(config["respiratory_rate_min"]),
            int(config["respiratory_rate_max"])
        )

        encounter.vitals.spo2 = random.randint(

            int(config["spo2_min"]),

            int(config["spo2_max"])

        )

        encounter.vitals.systolic_bp = random.randint(

            int(config["systolic_bp_min"]),

            int(config["systolic_bp_max"])

        )

        encounter.vitals.diastolic_bp = random.randint(

            int(config["diastolic_bp_min"]),

            int(config["diastolic_bp_max"])

        )

        return encounter
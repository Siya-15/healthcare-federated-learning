import random

from models.daily_hospital import DailyHospital


class DailyHospitalGenerator:

    def __init__(self, tables):

        self.hospital_master = tables["hospital_master"]
        self.hospital_config = tables["hospital_generation_config"]

    def generate(self, hospital_id, simulation_date):

        # --------------------------------------------------
        # Fetch Hospital Information
        # --------------------------------------------------

        hospital = self.hospital_master[
            self.hospital_master["hospital_id"] == hospital_id
        ].iloc[0]

        config = self.hospital_config[
            self.hospital_config["hospital_id"] == hospital_id
        ].iloc[0]

        # --------------------------------------------------
        # Calculate Today's Patient Count
        # --------------------------------------------------

        base_patients = config["expected_daily_patients"]

        seasonal_factor = config["seasonal_variation_factor"]

        random_factor = random.uniform(0.90, 1.10)

        patient_count = round(
            base_patients *
            seasonal_factor *
            random_factor
        )

        # --------------------------------------------------
        # Create Daily Hospital Object
        # --------------------------------------------------

        daily_hospital = DailyHospital(

            simulation_date=simulation_date,

            hospital_id=hospital["hospital_id"],

            hospital_name=hospital["hospital_name"],

            expected_patients=patient_count,

            outbreak_active=False,

            outbreak_disease=None

        )

        return daily_hospital
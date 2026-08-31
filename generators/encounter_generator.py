from datetime import datetime
import uuid


class EncounterGenerator:

    def generate(self, encounter, context):

        # Unique encounter ID
        encounter.encounter_id = (
            f"ENC-{uuid.uuid4().hex[:10].upper()}"
        )

        # Unique patient ID
        encounter.patient_id = (
            f"PAT-{uuid.uuid4().hex[:10].upper()}"
        )

        # Use simulation date instead of system date
        encounter.visit_timestamp = datetime.combine(
            context.current_date,
            datetime.min.time()
        )

        # Administrative information
        encounter.hospital_id = context.hospital_id

        encounter.visit_type = "New"

        return encounter
from sqlalchemy import text


class DatabaseWriter:

    def __init__(self, engine):
        self.engine = engine

    def save(self, encounter):

        """
        Writes one complete encounter into:

        - patient_encounter
        - encounter_symptoms
        - encounter_treatments
        - encounter_complications
        """

        with self.engine.begin() as connection:

            # ==================================================
            # 1. PATIENT ENCOUNTER
            # ==================================================

            connection.execute(
                text("""
                    INSERT INTO patient_encounter (
                        encounter_id,
                        patient_id,
                        hospital_id,
                        visit_timestamp,
                        age,
                        gender,
                        occupation,
                        district,
                        state,
                        temperature,
                        heart_rate,
                        respiratory_rate,
                        systolic_bp,
                        diastolic_bp,
                        spo2,
                        disease_id,
                        severity_id,
                        admission_status,
                        visit_type,
                        symptom_onset_days,
                        travel_history,
                        vaccination_status,
                        discharge_status,
                        recovery_days
                    )
                    VALUES (
                        :encounter_id,
                        :patient_id,
                        :hospital_id,
                        :visit_timestamp,
                        :age,
                        :gender,
                        :occupation,
                        :district,
                        :state,
                        :temperature,
                        :heart_rate,
                        :respiratory_rate,
                        :systolic_bp,
                        :diastolic_bp,
                        :spo2,
                        :disease_id,
                        :severity_id,
                        :admission_status,
                        :visit_type,
                        :symptom_onset_days,
                        :travel_history,
                        :vaccination_status,
                        :discharge_status,
                        :recovery_days
                    )
                """),
                {
                    "encounter_id": encounter.encounter_id,
                    "patient_id": encounter.patient_id,
                    "hospital_id": encounter.hospital_id,
                    "visit_timestamp": encounter.visit_timestamp,

                    "age": encounter.demographics.age,
                    "gender": encounter.demographics.gender,
                    "occupation": encounter.demographics.occupation,
                    "district": encounter.demographics.district,
                    "state": encounter.demographics.state,

                    "temperature": encounter.vitals.temperature,
                    "heart_rate": encounter.vitals.heart_rate,
                    "respiratory_rate": encounter.vitals.respiratory_rate,
                    "systolic_bp": encounter.vitals.systolic_bp,
                    "diastolic_bp": encounter.vitals.diastolic_bp,
                    "spo2": encounter.vitals.spo2,

                    "disease_id": encounter.disease_id,
                    "severity_id": encounter.severity_id,

                    "admission_status": (
                        "Admitted"
                        if encounter.admission_required
                        else "OPD"
                    ),

                    "visit_type": encounter.visit_type,

                    "symptom_onset_days": encounter.symptom_onset_days,

                    "travel_history": encounter.demographics.travel_history,

                    "vaccination_status": (
                        "Vaccinated"
                        if encounter.demographics.vaccination_status
                        else "Not Vaccinated"
                    ),

                    "discharge_status": {
                        "Recovered": "Recovered",
                        "Not Recovered": "Stable",
                        "Critical": "Referred"
                    }.get(encounter.outcome, "Stable"),

                    "recovery_days": encounter.recovery_days,
                }
            )

            # ==================================================
            # 2. SYMPTOMS
            # ==================================================

            for index, symptom in enumerate(encounter.symptoms):

                connection.execute(
                    text("""
                        INSERT INTO encounter_symptoms (
                            encounter_id,
                            symptom_id,
                            symptom_text,
                            symptom_source,
                            is_primary,
                            onset_stage
                        )
                        VALUES (
                            :encounter_id,
                            :symptom_id,
                            :symptom_text,
                            :symptom_source,
                            :is_primary,
                            :onset_stage
                        )
                    """),
                    {
                        "encounter_id": encounter.encounter_id,
                        "symptom_id": symptom.symptom_id,
                        "symptom_text": symptom.symptom_name,
                        "symptom_source": "MASTER",
                        "is_primary": index == 0,
                        "onset_stage": {
                            "Early": "Initial",
                            "Middle": "Progressive",
                            "Late": "Severe"
                        }.get(symptom.onset_stage, "Initial"),
                    }
                )

            # ==================================================
            # 3. TREATMENTS
            # ==================================================

            for index, treatment in enumerate(encounter.treatments):

                connection.execute(
                    text("""
                        INSERT INTO encounter_treatments (
                            encounter_id,
                            treatment_id,
                            treatment_sequence,
                            recommended_by_ai,
                            administered,
                            treatment_notes,
                            accepted_by_doctor,
                            treatment_origin
                        )
                        VALUES (
                            :encounter_id,
                            :treatment_id,
                            :treatment_sequence,
                            :recommended_by_ai,
                            :administered,
                            :treatment_notes,
                            :accepted_by_doctor,
                            :treatment_origin
                        )
                    """),
                    {
                        "encounter_id": encounter.encounter_id,
                        "treatment_id": treatment.treatment_id,
                        "treatment_sequence": index + 1,

                        # These are historical/generated treatments,
                        # not AI recommendations.
                        "recommended_by_ai": False,
                        "administered": True,
                        "treatment_notes": None,
                        "accepted_by_doctor": True,
                        "treatment_origin": "Doctor",
                    }
                )

            # ==================================================
            # 4. COMPLICATIONS
            # ==================================================

            for complication in encounter.complications:

                connection.execute(
                    text("""
                        INSERT INTO encounter_complications (
                            encounter_id,
                            complication_id,
                            identified_timestamp,
                            resolved,
                            notes
                        )
                        VALUES (
                            :encounter_id,
                            :complication_id,
                            :identified_timestamp,
                            :resolved,
                            :notes
                        )
                    """),
                    {
                        "encounter_id": encounter.encounter_id,
                        "complication_id": complication.complication_id,
                        "identified_timestamp": encounter.visit_timestamp,
                        "resolved": encounter.outcome == "Recovered",
                        "notes": None,
                    }
                )
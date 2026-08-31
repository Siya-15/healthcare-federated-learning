import random


class OutcomeGenerator:

    def generate(self, encounter):

        severity = encounter.severity_id
        complications = len(encounter.complications)

        # Store number of complications
        encounter.complication_count = complications

        # --------------------------------------------------
        # MILD
        # --------------------------------------------------

        if severity == "SV001":

            encounter.admission_required = False
            encounter.referral_required = False

            # Most mild cases recover, but allow small variation
            if random.random() < 0.95:
                encounter.outcome = "Recovered"
                encounter.follow_up_status = "Resolved"
            else:
                encounter.outcome = "Not Recovered"
                encounter.follow_up_status = "Persistent"

            encounter.recovery_days = random.randint(3, 7)

            encounter.treatment_duration_days = random.randint(
                3, 7
            )

            encounter.readmitted_within_30_days = (
                random.random() < 0.03
            )

        # --------------------------------------------------
        # MODERATE
        # --------------------------------------------------

        elif severity == "SV002":

            encounter.admission_required = (
                random.random() < 0.85
            )

            encounter.referral_required = (
                random.random() < 0.10
            )

            # Complications make recovery less predictable
            if complications > 0:

                encounter.outcome = random.choices(
                    ["Recovered", "Not Recovered", "Critical"],
                    weights=[0.75, 0.15, 0.10],
                    k=1
                )[0]

            else:

                encounter.outcome = random.choices(
                    ["Recovered", "Not Recovered"],
                    weights=[0.92, 0.08],
                    k=1
                )[0]

            encounter.recovery_days = random.randint(
                7, 14
            )

            encounter.treatment_duration_days = random.randint(
                5, 14
            )

            encounter.readmitted_within_30_days = (
                random.random() < 0.08
            )

            if encounter.outcome == "Recovered":
                encounter.follow_up_status = "Improved"
            else:
                encounter.follow_up_status = "Persistent"

        # --------------------------------------------------
        # SEVERE
        # --------------------------------------------------

        else:

            encounter.admission_required = True

            encounter.referral_required = (
                random.random() < 0.60
            )

            if complications > 0:

                encounter.outcome = random.choices(
                    ["Recovered", "Critical", "Not Recovered"],
                    weights=[0.55, 0.30, 0.15],
                    k=1
                )[0]

            else:

                encounter.outcome = random.choices(
                    ["Recovered", "Critical", "Not Recovered"],
                    weights=[0.75, 0.15, 0.10],
                    k=1
                )[0]

            encounter.recovery_days = random.randint(
                14, 28
            )

            encounter.treatment_duration_days = random.randint(
                10, 28
            )

            encounter.readmitted_within_30_days = (
                random.random() < 0.15
            )

            if encounter.outcome == "Recovered":
                encounter.follow_up_status = "Improved"

            elif encounter.outcome == "Critical":
                encounter.follow_up_status = "Under Treatment"

            else:
                encounter.follow_up_status = "Persistent"

        return encounter
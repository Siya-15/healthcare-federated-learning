import random
from datetime import timedelta

from models.encounter import ImagingResult


class ImagingGenerator:

    def __init__(self, tables):

        self.imaging_master = tables["imaging_master"]
        self.disease_imaging_mapping = tables["disease_imaging_mapping"]

    # ==========================================================
    # GENERATE IMAGING
    # ==========================================================

    def generate(self, encounter):

        if encounter.disease_id is None:
            return

        mappings = self.disease_imaging_mapping[
            self.disease_imaging_mapping["disease_id"]
            == encounter.disease_id
        ]

        if mappings.empty:
            return

        for _, mapping in mappings.iterrows():

            imaging_id = mapping["imaging_id"]

            # --------------------------------------------------
            # Frequency-based selection
            # --------------------------------------------------

            frequency = str(mapping["frequency"]).strip().lower()

            probability = {
                "common": 0.70,
                "occasional": 0.40,
                "rare": 0.15
            }.get(frequency, 0.30)

            # Severity increases likelihood of imaging
            if encounter.severity_id == "SV002":
                probability += 0.10

            elif encounter.severity_id == "SV003":
                probability += 0.20

            probability = min(probability, 0.95)

            if random.random() > probability:
                continue

            # --------------------------------------------------
            # Get imaging master information
            # --------------------------------------------------

            master = self.imaging_master[
                self.imaging_master["imaging_id"]
                == imaging_id
            ]

            if master.empty:
                continue

            imaging = master.iloc[0]

            # --------------------------------------------------
            # Generate result
            # --------------------------------------------------

            abnormal_probability = float(
                mapping["abnormal_probability"]
            )

            # Severity increases abnormality likelihood
            if encounter.severity_id == "SV002":
                abnormal_probability += 0.10

            elif encounter.severity_id == "SV003":
                abnormal_probability += 0.20

            abnormal_probability = min(
                abnormal_probability,
                0.95
            )

            abnormal = (
                random.random() < abnormal_probability
            )

            body_site = self._body_site(
                imaging["imaging_name"],
                imaging["body_system"]
            )

            finding, impression = self._generate_finding(
                imaging["imaging_name"],
                abnormal,
                encounter.severity_id
            )

            performed_timestamp = encounter.visit_timestamp

            encounter.imaging.append(
                ImagingResult(
                    imaging_id=imaging["imaging_id"],
                    imaging_name=imaging["imaging_name"],
                    modality=imaging["modality"],
                    body_site=body_site,
                    finding=finding,
                    impression=impression,
                    performed_timestamp=performed_timestamp
                )
            )

    # ==========================================================
    # BODY SITE
    # ==========================================================

    def _body_site(self, imaging_name, body_system):

        name = str(imaging_name).lower()
        system = str(body_system).lower()

        if "chest" in name:
            return "Chest"

        if "abdominal" in name:
            return "Abdomen"

        if "liver" in name:
            return "Liver"

        if "brain" in name:
            return "Brain"

        if "joint" in name:
            return "Joint"

        if "respiratory" in system:
            return "Chest"

        if "hepatic" in system:
            return "Liver"

        if "gastrointestinal" in system:
            return "Abdomen"

        return None

    # ==========================================================
    # FINDING + IMPRESSION
    # ==========================================================

    def _generate_finding(
        self,
        imaging_name,
        abnormal,
        severity_id
    ):

        name = str(imaging_name).lower()

        if "chest x-ray" in name:

            if abnormal:
                return (
                    "Patchy pulmonary opacities",
                    "Abnormal chest radiograph with pulmonary changes"
                )

            return (
                "No focal pulmonary opacity",
                "No acute cardiopulmonary abnormality"
            )

        if "chest ct" in name:

            if abnormal:
                return (
                    "Bilateral ground-glass or patchy opacities",
                    "Abnormal pulmonary findings"
                )

            return (
                "No significant pulmonary abnormality",
                "No acute thoracic abnormality"
            )

        if "liver" in name:

            if abnormal:
                return (
                    "Mild hepatomegaly",
                    "Mild hepatic enlargement"
                )

            return (
                "Normal liver size and echotexture",
                "No significant hepatic abnormality"
            )

        if "abdominal ultrasound" in name:

            if abnormal:
                return (
                    "Mild bowel wall or abdominal inflammatory changes",
                    "Abnormal abdominal sonographic findings"
                )

            return (
                "No significant abdominal abnormality",
                "Unremarkable abdominal ultrasound"
            )

        if "abdominal ct" in name:

            if abnormal:
                return (
                    "Inflammatory changes in abdominal structures",
                    "Abnormal abdominal CT findings"
                )

            return (
                "No acute abdominal abnormality",
                "No significant acute finding"
            )

        if "brain ct" in name:

            if abnormal:
                return (
                    "Non-specific intracranial abnormality",
                    "Abnormal intracranial finding"
                )

            return (
                "No acute intracranial abnormality",
                "Normal non-contrast CT appearance"
            )

        if "joint" in name:

            if abnormal:
                return (
                    "Joint space or inflammatory changes",
                    "Abnormal musculoskeletal finding"
                )

            return (
                "No significant structural abnormality",
                "No acute osseous abnormality"
            )

        # Fallback

        if abnormal:

            return (
                "Non-specific abnormal imaging finding",
                "Abnormal imaging result"
            )

        return (
            "No significant abnormality",
            "No significant imaging abnormality"
        )
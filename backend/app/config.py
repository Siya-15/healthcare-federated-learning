"""Path + constant resolution for the API.

Everything here resolves from __file__ so the server can be started from any
working directory. The ML scripts in this repo are CWD-relative; the API
deliberately is not.
"""

import os
from pathlib import Path

# backend/app/config.py -> backend/app -> backend -> repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ML_DIR = REPO_ROOT / "ML"
ML_DATA_DIR = ML_DIR / "data"
ML_MODELS_DIR = ML_DIR / "models"
KNOWLEDGE_DIR = REPO_ROOT / "datasets" / "knowledge tables"
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"

HOSPITAL_IDS = [f"H{i:03d}" for i in range(1, 11)]

# Mirrors ML/privacy/privacy_protection.py. In a real deployment this is a
# managed secret; the fallback exists so the prototype runs out of the box.
PRIVACY_SECRET = os.environ.get("PRIVACY_SECRET", "local-hospital-secret")

# The 27 symptom columns, in the exact order the treatment model was trained on.
SYMPTOM_COLUMNS = [
    "Abdominal Pain", "Anaemia", "Bleeding", "Breathlessness", "Chest Pain",
    "Chills", "Dehydration", "Diarrhoea", "Dry Cough", "Fatigue", "Fever",
    "Headache", "Joint Pain", "Loss of Appetite", "Loss of Smell",
    "Loss of Taste", "Muscle Pain", "Nausea", "Night Sweats",
    "Persistent Cough", "Rash", "Retro-orbital Pain", "Runny Nose",
    "Sore Throat", "Sweating", "Vomiting", "Weight Loss",
]

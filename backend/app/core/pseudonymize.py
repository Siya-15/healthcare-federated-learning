"""Deterministic pseudonymisation for patient identifiers.

patient_token = "pt_" + first 8 hex chars of SHA-256(secret + ":" + patient_id)

This is a pseudonym, NOT irreversible anonymisation (spec section 16). The raw
patient_id is never returned by any application endpoint.
"""
from __future__ import annotations

import hashlib

from app.core.config import get_settings


def patient_token(patient_id: str) -> str:
    secret = get_settings().privacy_secret
    digest = hashlib.sha256(f"{secret}:{patient_id}".encode()).hexdigest()
    return f"pt_{digest[:8]}"

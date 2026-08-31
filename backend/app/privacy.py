"""Pseudonymization.

Deliberately identical to ML/privacy/privacy_protection.py:
    sha256(secret + ":" + identifier) -> "PSEUDO-" + first 16 hex chars

Keeping the scheme byte-identical means a token minted by the API links to the
same local record as one minted by the ML privacy module.
"""

import hashlib

from .config import PRIVACY_SECRET


def pseudonymize(identifier: str, secret_key: str = PRIVACY_SECRET) -> str:
    value = f"{secret_key}:{identifier}"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return "PSEUDO-" + digest[:16]

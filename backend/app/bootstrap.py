"""Put the repo root and ML/ on sys.path so the optional ML pipeline can be
imported by the advisor service. Importing this module has the side effect;
it is safe to import more than once.
"""
from __future__ import annotations

import sys

from app.core.config import REPO_ROOT

for p in (str(REPO_ROOT), str(REPO_ROOT / "ML")):
    if p not in sys.path:
        sys.path.insert(0, p)

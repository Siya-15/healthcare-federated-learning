import json

from fastapi import APIRouter

from ..config import ARTIFACTS_DIR

router = APIRouter()


@router.get("/federated-learning/status")
def fl_status():
    """Latest completed FL run.

    Reads a static artifact by design - per the integration guide, opening the
    dashboard must not kick off a federated simulation.
    """
    with open(ARTIFACTS_DIR / "fl_run.json") as f:
        return json.load(f)

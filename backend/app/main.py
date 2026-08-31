"""Healthcare federated-learning prototype API.

Serves the eight endpoints named in
md_files/04_BACKEND_FRONTEND_INTEGRATION.md.

Data source: the committed CSV artifacts, not PostgreSQL. The schema for the
clinical database is not present in this repository, so the API reads
ML/ml_data_H0XX.csv (encounter-level, a superset of the clinical view's needs)
and ML/data/*.csv (precomputed surveillance / privacy outputs) instead. The
treatment advisor uses the already-trained model in ML/models/.

The only endpoint this costs us is POST /api/encounters, which would need to
write to Postgres; it returns 501 until a schema is available.
"""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import (
    dashboard,
    encounters,
    federated,
    hospitals,
    privacy,
    surveillance,
    treatment,
)

app = FastAPI(
    title="Healthcare Federated Learning API",
    version="1.0.0",
    description="Review 2 prototype API. Decision support, not clinical use.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(dashboard.router, tags=["dashboard"])
api.include_router(surveillance.router, tags=["surveillance"])
api.include_router(federated.router, tags=["federated-learning"])
api.include_router(treatment.router, tags=["treatment"])
api.include_router(privacy.router, tags=["privacy"])
api.include_router(hospitals.router, tags=["hospitals"])
api.include_router(encounters.router, tags=["encounters"])


@api.post("/encounters", status_code=501)
def create_encounter():
    """Not implemented: writing an encounter requires the PostgreSQL schema,
    which is not present in this repository."""
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Not implemented. Creating an encounter requires a write "
                      "to PostgreSQL, and the database schema is not available "
                      "in this repository. Read endpoints are served from the "
                      "committed CSV artifacts.",
        },
    )


app.include_router(api)


@app.get("/health")
def health():
    return {"status": "ok"}

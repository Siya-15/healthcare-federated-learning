"""FastAPI entrypoint for the multi-portal healthcare application backend.

Run from the repo root:
    .venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000

All routes are mounted under /api/* to match the frontend service layer
(frontend/src/services/*). RBAC + hospital scope are enforced server-side.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings

from app.routers import clinical, federated, health, models, privacy, surveillance, objective_a,objective_c4

from app.routers.objective_b import router as objective_b_router


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

settings = get_settings()

app = FastAPI(title="Healthcare FL — Application API", version=settings.app_version)
app.include_router(objective_b_router)
app.include_router(objective_c4.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (health, clinical, surveillance, federated, privacy, models, objective_a):
    app.include_router(r.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Request validation failed.", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak internals / clinical data to the client (spec section 16).
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "healthcare-fl-backend", "docs": "/docs", "health": "/api/health"}

"""Read-only access to the dashboard_snapshot table.

Surveillance / Federated / Privacy / AI-Ops portals render aggregate prototype
outputs. Those are produced offline by the ML pipeline and stored as JSONB
payloads whose shape matches the API response contract exactly.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection


def get_snapshot(conn: Connection, kind: str) -> dict | None:
    row = conn.execute(
        text("SELECT payload FROM dashboard_snapshot WHERE kind = :kind"),
        {"kind": kind},
    ).fetchone()
    return dict(row[0]) if row and row[0] is not None else None


def require_snapshot(conn: Connection, kind: str) -> dict:
    payload = get_snapshot(conn, kind)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Snapshot '{kind}' has not been generated yet. Run backend/seed_supabase.py.",
        )
    return payload

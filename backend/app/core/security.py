"""Demo RBAC. Server-side enforcement of role + hospital scope (spec section 16).

The frontend sends the active demo identity as headers:
    X-Demo-Role      one of DOCTOR | HOSPITAL_ADMIN | PUBLIC_HEALTH_ADMIN | TECH_REVIEWER
    X-Demo-Hospital  e.g. H001

In a real deployment these come from an authenticated session / JWT; the
dependency below is the single seam to swap. RBAC is enforced here, not by the
React menu.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

DOCTOR = "DOCTOR"
HOSPITAL_ADMIN = "HOSPITAL_ADMIN"
PUBLIC_HEALTH_ADMIN = "PUBLIC_HEALTH_ADMIN"
TECH_REVIEWER = "TECH_REVIEWER"

ALL_ROLES = {DOCTOR, HOSPITAL_ADMIN, PUBLIC_HEALTH_ADMIN, TECH_REVIEWER}


@dataclass(frozen=True)
class CurrentUser:
    role: str
    hospital_id: str | None

    def require_roles(self, *allowed: str) -> None:
        if self.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {self.role} is not permitted to access this resource.",
            )

    def authorize_hospital(self, hospital_id: str | None) -> None:
        """A DOCTOR / HOSPITAL_ADMIN is scoped to their own hospital.

        PUBLIC_HEALTH_ADMIN and TECH_REVIEWER see cross-hospital aggregates.
        """
        if self.role in (PUBLIC_HEALTH_ADMIN, TECH_REVIEWER):
            return
        if hospital_id and self.hospital_id and hospital_id != self.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This record is outside your authorised hospital scope.",
            )


def get_current_user(
    x_demo_role: str = Header(default=DOCTOR, alias="X-Demo-Role"),
    x_demo_hospital: str | None = Header(default=None, alias="X-Demo-Hospital"),
) -> CurrentUser:
    role = (x_demo_role or DOCTOR).strip().upper()
    if role not in ALL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unknown role '{x_demo_role}'.",
        )
    hospital = (x_demo_hospital or "").strip().upper() or None
    return CurrentUser(role=role, hospital_id=hospital)


def require(*allowed: str):
    """Dependency factory: restrict an endpoint to the given roles."""
    from fastapi import Depends

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user.require_roles(*allowed)
        return user

    return dependency

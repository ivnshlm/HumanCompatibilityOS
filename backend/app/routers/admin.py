"""Admin: user management (role, activation, team).

Admin-only and fully audited. Guards against lockout — an admin can never
remove the last remaining active admin (by demotion or deactivation).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.db import get_db
from app.deps import require_roles
from app.models import Role, User
from app.schemas import AdminUserCreate, AdminUserUpdate, UserRead
from app.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])

_require_admin = require_roles(Role.admin)


def _active_admin_count(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(User).where(User.role == Role.admin, User.is_active.is_(True))
    )


@router.get("/users", response_model=list[UserRead])
def list_all_users(
    actor: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    """Full user directory for management (admin only)."""
    return list(db.scalars(select(User).order_by(User.full_name)).all())


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    actor: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> User:
    """Create a user directly (admin only) — role and team may be set on creation."""
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        team_id=payload.team_id,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()
    log_audit(
        db,
        actor_user_id=actor.id,
        action="admin.user.create",
        entity_type="user",
        entity_id=str(user.id),
        detail={"email": payload.email, "role": user.role.value},
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    update: AdminUserUpdate,
    actor: User = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> User:
    """Change a user's role / activation / team. Only provided fields are applied."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    fields = update.model_fields_set
    changes: dict[str, object] = {}

    # Lockout guard: don't let the last active admin be demoted or deactivated.
    last_admin = target.role == Role.admin and target.is_active and _active_admin_count(db) <= 1
    demoting = "role" in fields and update.role != Role.admin
    deactivating = "is_active" in fields and update.is_active is False
    if last_admin and (demoting or deactivating):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote or deactivate the last active admin",
        )
    # Extra foot-gun guard: an admin can't deactivate their own account.
    if deactivating and target.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    if "role" in fields and update.role is not None and update.role != target.role:
        changes["role"] = {"from": target.role.value, "to": update.role.value}
        target.role = update.role
    if "is_active" in fields and update.is_active is not None and update.is_active != target.is_active:
        changes["is_active"] = {"from": target.is_active, "to": update.is_active}
        target.is_active = update.is_active
    if "team_id" in fields and update.team_id != target.team_id:
        changes["team_id"] = {"from": str(target.team_id), "to": str(update.team_id)}
        target.team_id = update.team_id

    if changes:
        log_audit(
            db,
            actor_user_id=actor.id,
            action="admin.user.update",
            entity_type="user",
            entity_id=str(target.id),
            detail=changes,
        )
    db.commit()
    db.refresh(target)
    return target

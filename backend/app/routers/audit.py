"""Audit-log access (Phase 6): accountability for who did/saw what.

Restricted to Admin and Ethics Reviewer — the roles charged with oversight.
Read-only; the log itself is append-only via log_audit() across the app.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import AuditLog, Role, User
from app.schemas import AuditLogOut

router = APIRouter(tags=["audit"])

_OVERSIGHT_ROLES = {Role.admin, Role.ethics_reviewer}


@router.get("/audit", response_model=list[AuditLogOut])
def list_audit(
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    if user.role not in _OVERSIGHT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit log is restricted to oversight roles (admin, ethics reviewer)",
        )

    stmt = select(AuditLog)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)

    return list(db.scalars(stmt).all())

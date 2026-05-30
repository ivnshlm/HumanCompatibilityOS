"""Reviewer-scoped user directory — supports the calibration-review UI."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Role, User
from app.schemas import UserSummary

router = APIRouter(tags=["users"])

_REVIEWER_ROLES = {Role.hr, Role.team_lead, Role.admin, Role.ethics_reviewer}


@router.get("/users", response_model=list[UserSummary])
def list_users(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[User]:
    """List users a reviewer may act on. Team leads see only their own team."""
    if user.role not in _REVIEWER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to list users",
        )

    stmt = select(User)
    if user.role == Role.team_lead:
        if user.team_id is None:
            return []
        stmt = stmt.where(User.team_id == user.team_id)

    return list(db.scalars(stmt.order_by(User.full_name)).all())

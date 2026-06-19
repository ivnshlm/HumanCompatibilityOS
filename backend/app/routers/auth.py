"""Authentication & account routes: register, login, refresh, me, consent."""

import uuid
from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import Role, User
from app.schemas import (
    ConsentRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens_for(user: User) -> TokenResponse:
    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    # Open registration, but role is NOT client-settable: everyone starts as an
    # Employee. The only self-service path to admin is the INITIAL_ADMIN_EMAILS
    # bootstrap (so a fresh system can get its first admin without a chicken-and-egg).
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    bootstrap = payload.email.lower() in get_settings().initial_admin_email_list
    role = Role.admin if bootstrap else Role.employee

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=role,
        team_id=payload.team_id,
    )
    db.add(user)
    db.flush()
    log_audit(
        db,
        actor_user_id=user.id,
        action="user.register",
        entity_type="user",
        entity_id=str(user.id),
        detail={"role": user.role.value},
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    log_audit(db, actor_user_id=user.id, action="user.login", entity_type="user", entity_id=str(user.id))
    db.commit()
    return _tokens_for(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return _tokens_for(user)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/consent", response_model=UserRead)
def consent(
    payload: ConsentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user.consent_given = payload.consent_given
    user.consent_at = datetime.now(UTC) if payload.consent_given else None
    log_audit(
        db,
        actor_user_id=user.id,
        action="user.consent",
        entity_type="user",
        entity_id=str(user.id),
        detail={"consent_given": payload.consent_given},
    )
    db.commit()
    db.refresh(user)
    return user

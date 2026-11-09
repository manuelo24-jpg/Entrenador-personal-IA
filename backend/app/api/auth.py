from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.models import UserModel
from app.db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=4, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class LoginSchema(BaseModel):
    email: str
    password: str


def _serialize_user(user: UserModel) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> UserModel | None:
    """Extract current authenticated user from Bearer token if present."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def get_current_user_required(
    user: UserModel | None = Depends(get_current_user_optional),
) -> UserModel:
    """Require a valid authenticated user."""
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Debes iniciar sesión para acceder a esta funcionalidad",
        )
    return user


@router.post("/register")
def register_user(body: RegisterSchema, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Register a new athlete account and return an access token."""
    clean_email = body.email.strip().lower()
    if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Introduce un correo electrónico válido")

    existing = db.query(UserModel).filter(UserModel.email == clean_email).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una cuenta registrada con ese correo electrónico",
        )

    user = UserModel(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        email=clean_email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email, name=user.name)
    return {
        "token": token,
        "user": _serialize_user(user),
    }


@router.post("/login")
def login_user(body: LoginSchema, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Authenticate an athlete with email and password."""
    clean_email = body.email.strip().lower()
    user = db.query(UserModel).filter(UserModel.email == clean_email).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Correo electrónico o contraseña incorrectos",
        )

    token = create_access_token(user_id=user.id, email=user.email, name=user.name)
    return {
        "token": token,
        "user": _serialize_user(user),
    }


@router.get("/me")
def get_me(user: UserModel = Depends(get_current_user_required)) -> dict[str, Any]:
    """Return the profile of the currently authenticated user."""
    return {"user": _serialize_user(user)}

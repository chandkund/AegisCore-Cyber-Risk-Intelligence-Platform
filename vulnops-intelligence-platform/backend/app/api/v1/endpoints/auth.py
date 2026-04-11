from __future__ import annotations

from app.api.deps import Principal, get_current_user
from app.db.deps import get_db
from app.middleware.login_rate_limit import allow_login_attempt
from app.schemas.auth import LoginRequest, LogoutRequest, MeResponse, RefreshRequest, TokenResponse
from app.services.auth_service import AuthService
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    client = request.client.host if request.client else "unknown"
    if not allow_login_attempt(client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts; try again shortly",
        )
    try:
        access, refresh, expires_in = AuthService(db).login(body.email, body.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        access, refresh, expires_in = AuthService(db).refresh(body.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    try:
        AuthService(db).logout(body.refresh_token)
    except Exception:  # noqa: BLE001 — idempotent logout
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(principal: Principal = Depends(get_current_user)):
    return MeResponse(
        id=str(principal.id),
        email=principal.email,
        full_name=principal.full_name,
        roles=sorted(principal.roles),
        is_active=True,
    )

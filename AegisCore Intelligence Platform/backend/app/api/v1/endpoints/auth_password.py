"""Password change endpoints for AegisCore authentication.

This module provides endpoints for users to change their passwords,
including support for forced password changes on first login.
"""

from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_user
from app.db.deps import get_db
from app.core.security import verify_password, hash_password
from app.services.password_validation_service import validate_password_strength
from app.models.oltp import User

router = APIRouter(prefix="/auth", tags=["auth"])


class ChangePasswordRequest(BaseModel):
    """Request to change password."""
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    """Response after password change."""
    success: bool
    message: str
    require_password_change: bool = False


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    body: ChangePasswordRequest,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change user password.
    
    Requires current password for verification (unless require_password_change is set).
    Validates new password strength.
    """
    user = db.get(User, principal.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Verify current password (unless force change is set)
    if not user.require_password_change:
        if not verify_password(body.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )
    
    # Validate new password strength
    validation = validate_password_strength(
        password=body.new_password,
        user_email=user.email,
        user_name=user.full_name,
    )
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation["errors"][0] if validation["errors"] else "Password does not meet requirements",
        )
    
    # Update password and clear require_password_change flag
    user.hashed_password = hash_password(body.new_password)
    user.require_password_change = False
    db.commit()
    
    return ChangePasswordResponse(
        success=True,
        message="Password changed successfully",
        require_password_change=False,
    )

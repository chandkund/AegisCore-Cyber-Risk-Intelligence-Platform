from __future__ import annotations

import uuid

from app.api.deps import AdminDep
from app.db.deps import get_db
from app.schemas.common import Paginated
from app.schemas.user import (
    UserCreate,
    UserInvitationCreate,
    UserInvitationOut,
    UserOut,
    UserRoleAssign,
    UserUpdate,
)
from app.services.audit_service import AuditService
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Paginated[UserOut])
def list_users(
    principal: AdminDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    svc = UserService(db)
    rows, total = svc.list_users(tenant_id=principal.tenant_id, limit=limit, offset=offset)
    return Paginated(
        items=[svc.to_out(u) for u in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(principal: AdminDep, body: UserCreate, db: Session = Depends(get_db)):
    svc = UserService(db)
    try:
        user = svc.create(body, tenant_id=principal.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    AuditService(db).record(
        actor_user_id=principal.id,
        action="user.create",
        resource_type="user",
        resource_id=str(user.id),
        payload={"email": user.email},
    )
    db.commit()
    u = svc.get(user.id, principal.tenant_id)
    if not u:
        raise HTTPException(status_code=500, detail="User persist failed")
    return svc.to_out(u)


@router.get("/{user_id}", response_model=UserOut)
def get_user(principal: AdminDep, user_id: uuid.UUID, db: Session = Depends(get_db)):
    svc = UserService(db)
    u = svc.get(user_id, principal.tenant_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return svc.to_out(u)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    principal: AdminDep, user_id: uuid.UUID, body: UserUpdate, db: Session = Depends(get_db)
):
    svc = UserService(db)
    u = svc.update(user_id, body, tenant_id=principal.tenant_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return svc.to_out(u)


@router.post("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def assign_role(
    principal: AdminDep,
    user_id: uuid.UUID,
    body: UserRoleAssign,
    db: Session = Depends(get_db),
):
    svc = UserService(db)
    try:
        svc.assign_role(user_id, body.role_name.strip(), tenant_id=principal.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/invitations", response_model=UserInvitationOut, status_code=status.HTTP_201_CREATED)
async def invite_user(
    principal: AdminDep,
    body: UserInvitationCreate,
    db: Session = Depends(get_db),
    company_name: str = "AegisCore",  # TODO: Get from tenant context
    accept_url: str = "http://localhost:3000/accept-invitation",
):
    """Create user invitation and send email notification."""
    from app.repositories.organization_repository import OrganizationRepository

    svc = UserService(db)

    # Get company name for email
    org = OrganizationRepository(db).get_by_id(principal.tenant_id)
    company_name_for_email = org.name if org else company_name

    try:
        invitation, invitation_token = await svc.create_and_send_invitation(
            tenant_id=principal.tenant_id,
            inviter_user_id=principal.id,
            inviter_name=principal.full_name or "Admin",
            company_name=company_name_for_email,
            email=body.email,
            role_name=body.role_name.strip().lower(),
            expires_in_hours=body.expires_in_hours,
            accept_url=accept_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserInvitationOut(
        invitation_token=invitation_token,
        email=invitation.email,
        role_name=invitation.role_name,
        expires_at=invitation.expires_at,
    )

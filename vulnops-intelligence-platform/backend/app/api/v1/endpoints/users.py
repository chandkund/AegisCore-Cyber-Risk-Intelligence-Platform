from __future__ import annotations

import uuid

from app.api.deps import AdminDep
from app.db.deps import get_db
from app.schemas.common import Paginated
from app.schemas.user import UserCreate, UserOut, UserRoleAssign, UserUpdate
from app.services.audit_service import AuditService
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Paginated[UserOut])
def list_users(
    _: AdminDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    svc = UserService(db)
    rows, total = svc.list_users(limit=limit, offset=offset)
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
        user = svc.create(body)
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
    u = svc.get(user.id)
    if not u:
        raise HTTPException(status_code=500, detail="User persist failed")
    return svc.to_out(u)


@router.get("/{user_id}", response_model=UserOut)
def get_user(_: AdminDep, user_id: uuid.UUID, db: Session = Depends(get_db)):
    svc = UserService(db)
    u = svc.get(user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return svc.to_out(u)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(_: AdminDep, user_id: uuid.UUID, body: UserUpdate, db: Session = Depends(get_db)):
    svc = UserService(db)
    u = svc.update(user_id, body)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return svc.to_out(u)


@router.post("/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def assign_role(
    _: AdminDep,
    user_id: uuid.UUID,
    body: UserRoleAssign,
    db: Session = Depends(get_db),
):
    svc = UserService(db)
    try:
        svc.assign_role(user_id, body.role_name.strip())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)

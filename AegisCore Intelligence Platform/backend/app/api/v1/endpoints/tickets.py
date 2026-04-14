from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import ReaderDep, WriterDep
from app.db.deps import get_db
from app.schemas.tickets import TicketCreateRequest, TicketOut, TicketSyncRequest
from app.services.ticketing_service import TicketingService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("/findings/{finding_id}", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket_for_finding(
    principal: WriterDep,
    finding_id: uuid.UUID,
    body: TicketCreateRequest,
    db: Session = Depends(get_db),
):
    svc = TicketingService(db, tenant_id=principal.tenant_id)
    try:
        return svc.create_ticket(
            finding_id=finding_id, body=body, actor_user_id=principal.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/findings/{finding_id}", response_model=list[TicketOut])
def list_tickets_for_finding(
    principal: ReaderDep,
    finding_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    svc = TicketingService(db, tenant_id=principal.tenant_id)
    try:
        return svc.list_tickets(finding_id=finding_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{ticket_id}/sync", response_model=TicketOut)
def sync_ticket_status(
    principal: WriterDep,
    ticket_id: uuid.UUID,
    body: TicketSyncRequest,
    db: Session = Depends(get_db),
):
    row = TicketingService(db, tenant_id=principal.tenant_id).sync_ticket_status(
        ticket_id=ticket_id,
        status=body.status,
        payload=body.payload,
        actor_user_id=principal.id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return row

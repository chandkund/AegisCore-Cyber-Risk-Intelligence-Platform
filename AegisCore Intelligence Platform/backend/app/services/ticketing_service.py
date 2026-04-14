from __future__ import annotations



import uuid

from datetime import datetime, timezone

from typing import Any



from sqlalchemy import select

from sqlalchemy.orm import Session



from app.models.oltp import RemediationTicket, VulnerabilityFinding

from app.schemas.tickets import TicketCreateRequest, TicketOut

from app.services.audit_service import AuditService





class TicketingService:

    def __init__(self, db: Session, tenant_id: uuid.UUID):

        self.db = db

        self.tenant_id = tenant_id

        self.audit = AuditService(db)



    @staticmethod

    def _provider_ref(provider: str) -> str:

        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        suffix = str(uuid.uuid4()).split("-")[0]

        if provider == "jira":

            return f"VULN-{ts[-6:]}"

        if provider == "servicenow":

            return f"INC{ts}{suffix[:4].upper()}"

        return f"{provider.upper()}-{suffix}"



    @staticmethod

    def _provider_url(provider: str, external_id: str) -> str:

        if provider == "jira":

            return f"https://jira.example.local/browse/{external_id}"

        if provider == "servicenow":

            return f"https://servicenow.example.local/nav_to.do?uri=incident.do?sys_id={external_id}"

        return f"https://github.com/example/aegiscore-intelligence-platform/issues/{external_id}"



    def _require_finding(self, finding_id: uuid.UUID) -> VulnerabilityFinding:

        finding = self.db.execute(

            select(VulnerabilityFinding).where(

                VulnerabilityFinding.id == finding_id,

                VulnerabilityFinding.tenant_id == self.tenant_id,

            )

        ).scalar_one_or_none()

        if finding is None:

            raise ValueError("Finding not found")

        return finding



    @staticmethod

    def _to_out(row: RemediationTicket) -> TicketOut:

        return TicketOut(

            id=str(row.id),

            finding_id=str(row.finding_id),

            provider=row.provider,  # type: ignore[arg-type]

            external_ticket_id=row.external_ticket_id,

            external_url=row.external_url,

            status=row.status,

            title=row.title,

            payload=row.payload,

            created_by_user_id=str(row.created_by_user_id) if row.created_by_user_id else None,

            created_at=row.created_at,

            updated_at=row.updated_at,

        )



    def create_ticket(

        self,

        *,

        finding_id: uuid.UUID,

        body: TicketCreateRequest,

        actor_user_id: uuid.UUID | None,

    ) -> TicketOut:

        self._require_finding(finding_id)

        external_ticket_id = self._provider_ref(body.provider)

        row = RemediationTicket(

            tenant_id=self.tenant_id,

            finding_id=finding_id,

            provider=body.provider,

            external_ticket_id=external_ticket_id,

            external_url=self._provider_url(body.provider, external_ticket_id),

            status="OPEN",

            title=body.title,

            payload={

                "description": body.description,

                "assignee": body.assignee,

                "labels": body.labels,

                "metadata": body.metadata,

            },

            created_by_user_id=actor_user_id,

        )

        self.db.add(row)

        self.db.flush()

        self.audit.record(

            actor_user_id=actor_user_id,

            action="ticket.create",

            resource_type="remediation_ticket",

            resource_id=str(row.id),

            payload={"provider": row.provider, "external_ticket_id": row.external_ticket_id},

        )

        self.db.commit()

        self.db.refresh(row)

        return self._to_out(row)



    def list_tickets(self, *, finding_id: uuid.UUID) -> list[TicketOut]:

        self._require_finding(finding_id)

        rows = self.db.execute(

            select(RemediationTicket)

            .where(

                RemediationTicket.tenant_id == self.tenant_id,

                RemediationTicket.finding_id == finding_id,

            )

            .order_by(RemediationTicket.created_at.desc())

        ).scalars().all()

        return [self._to_out(r) for r in rows]



    def sync_ticket_status(

        self,

        *,

        ticket_id: uuid.UUID,

        status: str,

        payload: dict[str, Any] | None,

        actor_user_id: uuid.UUID | None,

    ) -> TicketOut | None:

        row = self.db.execute(

            select(RemediationTicket).where(

                RemediationTicket.id == ticket_id,

                RemediationTicket.tenant_id == self.tenant_id,

            )

        ).scalar_one_or_none()

        if row is None:

            return None

        row.status = status.upper()

        if payload is not None:

            row.payload = {**(row.payload or {}), "sync": payload}

        self.audit.record(

            actor_user_id=actor_user_id,

            action="ticket.sync_status",

            resource_type="remediation_ticket",

            resource_id=str(row.id),

            payload={"status": row.status},

        )

        self.db.commit()

        self.db.refresh(row)

        return self._to_out(row)



    def close_tickets_for_finding(

        self,

        *,

        finding_id: uuid.UUID,

        actor_user_id: uuid.UUID | None,

    ) -> int:

        rows = self.db.execute(

            select(RemediationTicket).where(

                RemediationTicket.tenant_id == self.tenant_id,

                RemediationTicket.finding_id == finding_id,

                RemediationTicket.status.not_in(["RESOLVED", "CLOSED"]),

            )

        ).scalars().all()

        for row in rows:

            row.status = "RESOLVED"

        if rows:

            self.audit.record(

                actor_user_id=actor_user_id,

                action="ticket.auto_resolve",

                resource_type="vulnerability_finding",

                resource_id=str(finding_id),

                payload={"resolved_ticket_count": len(rows)},

            )

            self.db.commit()

        return len(rows)


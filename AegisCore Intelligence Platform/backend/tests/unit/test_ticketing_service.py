from __future__ import annotations



import uuid

from datetime import datetime, timezone

from decimal import Decimal



from sqlalchemy.orm import Session



from app.models.oltp import Asset, BusinessUnit, CveRecord, Organization, VulnerabilityFinding

from app.schemas.finding import FindingUpdate

from app.schemas.tickets import TicketCreateRequest

from app.services.finding_service import FindingService

from app.services.ticketing_service import TicketingService





def _seed_finding(db: Session, tenant_id: uuid.UUID) -> VulnerabilityFinding:

    bu = BusinessUnit(id=uuid.uuid4(), code=f"TKT{str(tenant_id.int)[-6:]}", name="Ticket BU")

    db.add(bu)

    db.flush()

    asset = Asset(

        id=uuid.uuid4(),

        tenant_id=tenant_id,

        name="ticketed-asset",

        asset_type="server",

        business_unit_id=bu.id,

        criticality=2,

        is_external=True,

    )

    cve = CveRecord(

        id=uuid.uuid4(),

        cve_id=f"CVE-2026-{str(tenant_id.int)[-4:]}",

        severity="HIGH",

        cvss_base_score=Decimal("8.1"),

        exploit_available=True,

    )

    finding = VulnerabilityFinding(

        id=uuid.uuid4(),

        tenant_id=tenant_id,

        asset_id=asset.id,

        cve_record_id=cve.id,

        status="OPEN",

        discovered_at=datetime.now(timezone.utc),

        risk_score=Decimal("83.0"),

    )

    db.add_all([asset, cve, finding])

    db.flush()

    return finding





def test_create_and_sync_ticket(db: Session):

    tenant_id = uuid.UUID("00000000-0000-4000-8000-0000000000CA")

    db.add(Organization(id=tenant_id, name="Ticket Org", code="ticket-org"))

    finding = _seed_finding(db, tenant_id)



    svc = TicketingService(db, tenant_id=tenant_id)

    created = svc.create_ticket(

        finding_id=finding.id,

        body=TicketCreateRequest(

            provider="github",

            title="Fix high-risk vulnerability",

            description="Created from aegiscore finding",

        ),

        actor_user_id=None,

    )

    assert created.provider == "github"

    assert created.status == "OPEN"

    assert created.external_ticket_id



    synced = svc.sync_ticket_status(

        ticket_id=uuid.UUID(created.id),

        status="in_progress",

        payload={"remote_state": "triaged"},

        actor_user_id=None,

    )

    assert synced is not None

    assert synced.status == "IN_PROGRESS"





def test_finding_remediation_auto_resolves_tickets(db: Session):

    tenant_id = uuid.UUID("00000000-0000-4000-8000-0000000000CB")

    db.add(Organization(id=tenant_id, name="Ticket Org 2", code="ticket-org-2"))

    finding = _seed_finding(db, tenant_id)

    svc = TicketingService(db, tenant_id=tenant_id)

    ticket = svc.create_ticket(

        finding_id=finding.id,

        body=TicketCreateRequest(

            provider="jira",

            title="Remediate CVE",

            description="Jira workflow",

        ),

        actor_user_id=None,

    )

    assert ticket.status == "OPEN"



    updated = FindingService(db).update(

        finding.id,

        FindingUpdate(status="REMEDIATED"),

        actor_id=None,

        tenant_id=tenant_id,

    )

    assert updated is not None

    tickets = svc.list_tickets(finding_id=finding.id)

    assert len(tickets) == 1

    assert tickets[0].status == "RESOLVED"


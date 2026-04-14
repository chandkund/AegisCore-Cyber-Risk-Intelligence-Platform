from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import WriterDep
from app.db.deps import get_db
from app.schemas.ingestion import ConnectorIngestRequest, ConnectorIngestResponse, ConnectorProvider
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/connectors/{provider}/ingest", response_model=ConnectorIngestResponse)
def ingest_connector_records(
    provider: ConnectorProvider,
    body: ConnectorIngestRequest,
    principal: WriterDep,
    db: Session = Depends(get_db),
):
    service = IngestionService(db, tenant_id=principal.tenant_id)
    try:
        result = service.ingest(
            provider=provider,
            records=body.records,
            watermark=body.watermark,
            actor_user_id=principal.id,
            dry_run=body.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ConnectorIngestResponse(**result)

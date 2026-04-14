"""AI Security Assistant API endpoints."""

from __future__ import annotations

from app.api.deps import ReaderDep
from app.db.deps import get_db
from app.schemas.assistant import (
    AssistantQueryOut,
    AssistantRequest,
    AssistantResponseOut,
)
from app.services.assistant_service import AssistantService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantResponseOut)
def ask_assistant(
    principal: ReaderDep,
    body: AssistantRequest,
    db: Session = Depends(get_db),
):
    """Ask the AI Security Assistant a question.
    
    The assistant answers using real platform data including:
    - Prioritized vulnerabilities
    - Risk scores and explanations
    - Simulation results
    - Asset information
    
    Example questions:
    - "What should I fix first?"
    - "Why is this asset high risk?"
    - "Show me critical web vulnerabilities"
    - "What if I fix 5 high-risk issues?"
    """
    service = AssistantService(db, tenant_id=principal.tenant_id)
    response = service.ask(body.question)
    
    return AssistantResponseOut(
        answer=response.answer,
        question_type=response.question_type,
        supporting_records=response.supporting_records,
        confidence=response.confidence,
        suggested_followups=response.suggested_followups,
        generated_at=response.generated_at,
    )


@router.post("/quick", response_model=AssistantQueryOut)
def quick_query(
    principal: ReaderDep,
    body: AssistantRequest,
    db: Session = Depends(get_db),
):
    """Quick assistant query - returns just the answer text.
    
    Lightweight endpoint for simple chat interactions.
    """
    service = AssistantService(db, tenant_id=principal.tenant_id)
    response = service.ask(body.question)
    
    return AssistantQueryOut(
        answer=response.answer,
        question_type=response.question_type,
    )

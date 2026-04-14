"""Risk Explanation API endpoints.

Provides human-readable explanations for why vulnerabilities
received specific risk scores.
"""

from __future__ import annotations

import uuid

from app.api.deps import ReaderDep
from app.db.deps import get_db
from app.schemas.explanation import RiskExplanationOut
from app.services.explanation_service import ExplanationService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/explanations", tags=["explanations"])


@router.get("/vulnerabilities/{finding_id}", response_model=RiskExplanationOut)
def explain_vulnerability(
    principal: ReaderDep,
    finding_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get comprehensive risk explanation for a vulnerability.
    
    Returns:
        - Overall assessment
        - Severity level
        - Top contributing factors
        - Detailed explanation
        - Remediation priority reasoning
        - Comparable examples
    """
    service = ExplanationService(db)
    explanation = service.explain_finding(finding_id, tenant_id=principal.tenant_id)
    
    if not explanation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability finding not found",
        )
    
    return RiskExplanationOut(
        finding_id=explanation.finding_id,
        risk_score=explanation.risk_score,
        overall_assessment=explanation.overall_assessment,
        severity_level=explanation.severity_level,
        top_factors=explanation.top_factors,
        detailed_explanation=explanation.detailed_explanation,
        remediation_priority_reason=explanation.remediation_priority_reason,
        comparable_examples=explanation.comparable_examples,
        generated_at=explanation.generated_at,
    )


@router.get("/vulnerabilities/{finding_id}/factors")
def get_top_factors(
    principal: ReaderDep,
    finding_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get top contributing factors for a vulnerability (lightweight).
    
    Quick endpoint for showing risk drivers without full explanation.
    """
    service = ExplanationService(db)
    factors = service.explain_top_factors(finding_id, tenant_id=principal.tenant_id)
    
    if not factors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found or no risk factors available",
        )
    
    return {"finding_id": str(finding_id), "top_factors": factors}

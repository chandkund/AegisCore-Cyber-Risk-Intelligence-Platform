"""Prioritization API endpoints for risk scoring and prioritized vulnerabilities."""

from __future__ import annotations

import uuid
from typing import Any

from app.api.deps import AdminDep, ReaderDep, WriterDep
from app.db.deps import get_db
from app.schemas.common import Paginated
from app.schemas.prioritization import (
    BulkRecalculateRequest,
    BulkRecalculateResponse,
    PrioritizedFindingOut,
    PrioritizationFeedbackRequest,
    PrioritizationFeedbackResponse,
    RiskRecalculateRequest,
    RiskScoreOut,
)
from app.services.feedback_service import FeedbackService
from app.services.risk_engine_service import RiskEngineService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/prioritization", tags=["prioritization"])


@router.get("/vulnerabilities", response_model=Paginated[PrioritizedFindingOut])
def list_prioritized_vulnerabilities(
    principal: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    min_risk_score: float | None = Query(None, ge=0, le=100, description="Minimum risk score filter"),
    status: str | None = Query(None, description="Filter by status (OPEN, IN_PROGRESS, etc.)"),
    asset_id: uuid.UUID | None = Query(None),
    business_unit_id: uuid.UUID | None = Query(None),
):
    """Get vulnerabilities sorted by risk score (highest risk first).
    
    Returns paginated list of vulnerabilities with risk scores, 
    contributing factors, and asset/CVE details.
    """
    service = RiskEngineService(db)
    
    results, total = service.get_prioritized_findings(
        tenant_id=principal.tenant_id,
        limit=limit,
        offset=offset,
        min_risk_score=min_risk_score,
        status_filter=status,
        asset_id=asset_id,
        business_unit_id=business_unit_id,
    )
    
    # Transform to response schema
    items = []
    for r in results:
        f = r["finding"]
        items.append(PrioritizedFindingOut(
            id=str(f.id),
            asset_id=str(f.asset_id),
            cve_record_id=str(f.cve_record_id),
            cve_id=r["cve_id"],
            status=f.status,
            discovered_at=f.discovered_at,
            due_at=f.due_at,
            assigned_to_user_id=str(f.assigned_to_user_id) if f.assigned_to_user_id else None,
            risk_score=r["risk_score"],
            risk_factors=f.risk_factors,
            risk_calculated_at=f.risk_calculated_at,
            asset_name=r["asset_name"],
            asset_criticality=r["asset_criticality"],
            cvss_score=r["cvss_score"],
        ))
    
    return Paginated(items=items, total=total, limit=limit, offset=offset)


@router.get("/vulnerabilities/{finding_id}/risk-score", response_model=RiskScoreOut)
def get_finding_risk_score(
    principal: ReaderDep,
    finding_id: uuid.UUID,
    db: Session = Depends(get_db),
    include_ml: bool = Query(True, description="Include ML prediction if available"),
):
    """Get detailed risk score and contributing factors for a specific vulnerability.
    
    Returns:
        - Risk score (0-100)
        - Individual factor scores
        - Contributing factors (top drivers of risk)
        - Calculation method used
        - Percentile rank among all open vulnerabilities
    """
    from app.models.oltp import Asset, CveRecord, VulnerabilityFinding
    from sqlalchemy import select
    
    service = RiskEngineService(db)
    
    # Get finding with related records
    finding = db.execute(
        select(VulnerabilityFinding).where(
            VulnerabilityFinding.id == finding_id,
            VulnerabilityFinding.tenant_id == principal.tenant_id,
        )
    ).scalar_one_or_none()
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability finding not found",
        )
    
    asset = db.get(Asset, finding.asset_id)
    cve = db.get(CveRecord, finding.cve_record_id)
    
    if not asset or not cve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Related asset or CVE record not found",
        )
    
    # Calculate risk
    calc = service.calculate_risk(finding, asset, cve, use_ml=include_ml)
    
    # Get percentile rank
    percentile = service.get_risk_percentile(finding_id, principal.tenant_id)
    
    return RiskScoreOut(
        finding_id=str(finding_id),
        risk_score=calc.risk_score,
        rule_based_score=calc.rule_based_score,
        ml_score=calc.ml_score,
        calculation_method=calc.calculation_method,
        factors={
            "cvss": round(calc.factors.cvss_score, 3),
            "criticality": round(calc.factors.criticality_score, 3),
            "exposure": round(calc.factors.exposure_score, 3),
            "exploit": round(calc.factors.exploit_score, 3),
            "age": round(calc.factors.age_score, 3),
            "ml_probability": calc.factors.ml_probability,
        },
        contributing_factors=calc.contributing_factors,
        percentile_rank=percentile,
        calculated_at=calc.calculated_at,
    )


@router.post("/vulnerabilities/{finding_id}/recalculate", response_model=RiskScoreOut)
def recalculate_finding_risk(
    principal: WriterDep,
    finding_id: uuid.UUID,
    body: RiskRecalculateRequest | None = None,
    db: Session = Depends(get_db),
):
    """Recalculate and store risk score for a specific vulnerability.
    
    Requires write access. Updates the database with new risk score.
    """
    use_ml = body.use_ml if body else True
    
    service = RiskEngineService(db)
    calc = service.recalculate_and_store(
        finding_id, tenant_id=principal.tenant_id, use_ml=use_ml
    )
    
    if not calc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability finding not found or could not be calculated",
        )
    
    percentile = service.get_risk_percentile(finding_id, principal.tenant_id)
    
    return RiskScoreOut(
        finding_id=str(finding_id),
        risk_score=calc.risk_score,
        rule_based_score=calc.rule_based_score,
        ml_score=calc.ml_score,
        calculation_method=calc.calculation_method,
        factors={
            "cvss": round(calc.factors.cvss_score, 3),
            "criticality": round(calc.factors.criticality_score, 3),
            "exposure": round(calc.factors.exposure_score, 3),
            "exploit": round(calc.factors.exploit_score, 3),
            "age": round(calc.factors.age_score, 3),
            "ml_probability": calc.factors.ml_probability,
        },
        contributing_factors=calc.contributing_factors,
        percentile_rank=percentile,
        calculated_at=calc.calculated_at,
    )


@router.post("/risk/recalculate", response_model=BulkRecalculateResponse)
def bulk_recalculate_risk(
    principal: AdminDep,
    body: BulkRecalculateRequest,
    db: Session = Depends(get_db),
):
    """Recalculate risk scores for all open vulnerabilities.
    
    Admin only. Processes in batches and updates database.
    This can be a long-running operation for large datasets.
    """
    service = RiskEngineService(db)
    
    result = service.recalculate_all_open(
        tenant_id=principal.tenant_id,
        batch_size=body.batch_size,
        use_ml=body.use_ml,
    )
    
    return BulkRecalculateResponse(
        total=result["total"],
        updated=result["updated"],
        failed=result["failed"],
        batch_size=result["batch_size"],
    )


@router.get("/top-risks", response_model=list[PrioritizedFindingOut])
def get_top_risks(
    principal: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50, description="Number of top risks to return"),
    min_risk_score: float = Query(50.0, ge=0, le=100, description="Minimum risk score threshold"),
):
    """Get the top N highest-risk open vulnerabilities.
    
    Quick endpoint for dashboard widgets and alert systems.
    """
    service = RiskEngineService(db)
    
    results, _ = service.get_prioritized_findings(
        tenant_id=principal.tenant_id,
        limit=limit,
        offset=0,
        min_risk_score=min_risk_score,
        status_filter="OPEN",
    )
    
    items = []
    for r in results:
        f = r["finding"]
        items.append(PrioritizedFindingOut(
            id=str(f.id),
            asset_id=str(f.asset_id),
            cve_record_id=str(f.cve_record_id),
            cve_id=r["cve_id"],
            status=f.status,
            discovered_at=f.discovered_at,
            due_at=f.due_at,
            assigned_to_user_id=str(f.assigned_to_user_id) if f.assigned_to_user_id else None,
            risk_score=r["risk_score"],
            risk_factors=f.risk_factors,
            risk_calculated_at=f.risk_calculated_at,
            asset_name=r["asset_name"],
            asset_criticality=r["asset_criticality"],
            cvss_score=r["cvss_score"],
        ))
    
    return items


@router.post(
    "/vulnerabilities/{finding_id}/feedback",
    response_model=PrioritizationFeedbackResponse,
)
def submit_feedback(
    principal: WriterDep,
    finding_id: uuid.UUID,
    body: PrioritizationFeedbackRequest,
    db: Session = Depends(get_db),
):
    try:
        out = FeedbackService(db, tenant_id=principal.tenant_id).submit(
            finding_id=finding_id,
            feedback_type=body.feedback_type,
            notes=body.notes,
            actor_user_id=principal.id,
            queue_retrain=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return PrioritizationFeedbackResponse(**out)

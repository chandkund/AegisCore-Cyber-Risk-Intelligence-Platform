"""What-If Risk Simulation API endpoints."""

from __future__ import annotations

from app.api.deps import ReaderDep, WriterDep
from app.db.deps import get_db
from app.schemas.simulation import (
    CompareScenariosRequest,
    RecommendationsOut,
    SimulationRequest,
    SimulationResultOut,
)
from app.services.simulation_service import SimulationService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/simulate", tags=["simulation"])


@router.post("/remediation", response_model=SimulationResultOut)
def simulate_remediation(
    principal: WriterDep,
    body: SimulationRequest,
    db: Session = Depends(get_db),
):
    """Simulate risk reduction from remediating specific vulnerabilities.
    
    Body:
        finding_ids: List of vulnerability IDs to simulate fixing
        scenario_name: Optional name for this scenario
        
    Returns:
        Before/after risk metrics, reduction percentage, impacted assets
    """
    if not body.finding_ids:
        raise HTTPException(
            status_code=422,
            detail="At least one finding_id is required",
        )
    
    service = SimulationService(db, tenant_id=principal.tenant_id)
    try:
        result = service.simulate_remediation(
            finding_ids=body.finding_ids,
            scenario_name=body.scenario_name,
        )
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="One or more finding_ids are invalid UUIDs",
        )
    
    return SimulationResultOut(
        scenario_name=result.scenario_name,
        selected_count=result.selected_count,
        before_risk=result.before_risk,
        after_risk=result.after_risk,
        reduction_percentage=result.reduction_percentage,
        impacted_assets=result.impacted_assets,
        remaining_top_risks=result.remaining_top_risks,
    )


@router.post("/compare", response_model=list[SimulationResultOut])
def compare_scenarios(
    principal: ReaderDep,
    body: CompareScenariosRequest,
    db: Session = Depends(get_db),
):
    """Compare multiple remediation scenarios.
    
    Body:
        scenarios: List of {name, finding_ids} objects to compare
        
    Returns:
        List of simulation results sorted by reduction percentage
    """
    if not body.scenarios:
        raise HTTPException(
            status_code=422,
            detail="At least one scenario is required",
        )
    
    service = SimulationService(db, tenant_id=principal.tenant_id)
    
    scenario_tuples = [
        (s.name, s.finding_ids)
        for s in body.scenarios
    ]
    
    try:
        results = service.compare_scenarios(scenario_tuples)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="One or more scenario finding_ids are invalid UUIDs",
        )
    
    return [
        SimulationResultOut(
            scenario_name=r.scenario_name,
            selected_count=r.selected_count,
            before_risk=r.before_risk,
            after_risk=r.after_risk,
            reduction_percentage=r.reduction_percentage,
            impacted_assets=r.impacted_assets,
            remaining_top_risks=r.remaining_top_risks,
        )
        for r in results
    ]


@router.get("/recommendations", response_model=RecommendationsOut)
def get_recommendations(
    principal: ReaderDep,
    limit: int = Query(10, ge=1, le=20),
    min_risk_score: float = Query(60, ge=0, le=100),
    db: Session = Depends(get_db),
):
    """Get AI-recommended highest-impact vulnerabilities to fix.
    
    Considers risk score, asset criticality, external exposure, and clustering.
    
    Query:
        limit: Number of recommendations (default 10)
        min_risk_score: Minimum risk score threshold (default 60)
        
    Returns:
        Ranked list of recommended vulnerabilities with impact scores
    """
    service = SimulationService(db, tenant_id=principal.tenant_id)
    recommendations = service.recommend_high_impact_fixes(
        max_recommendations=limit,
        min_risk_score=min_risk_score,
    )
    
    return RecommendationsOut(
        recommendations=recommendations,
        total_available=len(recommendations),
    )

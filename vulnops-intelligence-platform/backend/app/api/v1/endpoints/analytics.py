from __future__ import annotations

from app.api.deps import ReaderDep
from app.db.deps import get_db
from app.schemas.analytics import (
    AnalyticsSummary,
    BusinessUnitRiskRow,
    RiskTrendResponse,
    SlaForecastResponse,
    TopAssetRow,
)
from app.schemas.compliance import ComplianceReportOut, RootCauseCluster
from app.services.analytics_service import AnalyticsService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(principal: ReaderDep, db: Session = Depends(get_db)):
    return AnalyticsService(db).summary(tenant_id=principal.tenant_id)


@router.get("/top-assets", response_model=list[TopAssetRow])
def top_assets(
    principal: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    return AnalyticsService(db).top_assets(tenant_id=principal.tenant_id, limit=limit)


@router.get("/business-units", response_model=list[BusinessUnitRiskRow])
def business_units_risk(
    principal: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    return AnalyticsService(db).business_units(tenant_id=principal.tenant_id, limit=limit)


@router.get("/risk-trend", response_model=RiskTrendResponse)
def risk_trend(
    principal: ReaderDep,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=7, le=180),
):
    return AnalyticsService(db).risk_trend(tenant_id=principal.tenant_id, days=days)


@router.get("/sla-forecast", response_model=SlaForecastResponse)
def sla_forecast(
    principal: ReaderDep,
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).sla_forecast(tenant_id=principal.tenant_id)


@router.get("/root-cause-clusters", response_model=list[RootCauseCluster])
def root_cause_clusters(
    principal: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    return AnalyticsService(db).root_cause_clusters(tenant_id=principal.tenant_id, limit=limit)


@router.get("/compliance-report", response_model=ComplianceReportOut)
def compliance_report(
    principal: ReaderDep,
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).compliance_report(tenant_id=principal.tenant_id)

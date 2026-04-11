from __future__ import annotations

from app.api.deps import ReaderDep
from app.db.deps import get_db
from app.schemas.analytics import AnalyticsSummary, BusinessUnitRiskRow, TopAssetRow
from app.services.analytics_service import AnalyticsService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(_: ReaderDep, db: Session = Depends(get_db)):
    return AnalyticsService(db).summary()


@router.get("/top-assets", response_model=list[TopAssetRow])
def top_assets(
    _: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    return AnalyticsService(db).top_assets(limit=limit)


@router.get("/business-units", response_model=list[BusinessUnitRiskRow])
def business_units_risk(
    _: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    return AnalyticsService(db).business_units(limit=limit)

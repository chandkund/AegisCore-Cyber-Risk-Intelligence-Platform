"""Smart NLP Search API endpoints."""

from __future__ import annotations

from app.api.deps import ReaderDep
from app.db.deps import get_db
from app.schemas.search import SearchResultOut, SearchSuggestionsOut
from app.services.search_service import SearchService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResultOut)
def search_vulnerabilities(
    principal: ReaderDep,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="Filter by status"),
    min_risk_score: float | None = Query(None, ge=0, le=100),
    db: Session = Depends(get_db),
):
    """Smart NLP search over vulnerabilities.
    
    Supports natural language queries:
    - "critical web server vulnerabilities with exploits"
    - "high risk issues in internet-facing assets"  
    - "old vulnerabilities in finance systems"
    
    Returns vulnerabilities ranked by relevance and risk score.
    """
    service = SearchService(db, tenant_id=principal.tenant_id)
    results, total = service.search(
        query=q,
        limit=limit,
        offset=offset,
        status_filter=status,
        min_risk_score=min_risk_score,
    )
    
    return SearchResultOut(
        query=q,
        total=total,
        limit=limit,
        offset=offset,
        results=[
            {
                "finding_id": r.finding_id,
                "cve_id": r.cve_id,
                "title": r.title,
                "asset_name": r.asset_name,
                "status": r.status,
                "risk_score": r.risk_score,
                "relevance_score": r.relevance_score,
                "semantic_score": r.semantic_score,
                "keyword_score": r.keyword_score,
                "match_type": r.match_type,
                "snippet": r.snippet,
            }
            for r in results
        ],
    )


@router.get("/suggestions", response_model=SearchSuggestionsOut)
def get_search_suggestions(
    principal: ReaderDep,
    q: str = Query(..., min_length=2, description="Partial search query"),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Get search suggestions based on partial input."""
    service = SearchService(db, tenant_id=principal.tenant_id)
    suggestions = service.search_suggestions(q, limit)
    
    return SearchSuggestionsOut(
        query=q,
        suggestions=suggestions,
    )

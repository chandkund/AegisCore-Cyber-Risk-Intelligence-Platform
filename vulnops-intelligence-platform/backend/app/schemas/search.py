"""Pydantic schemas for search functionality."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """Single search result item."""
    finding_id: str
    cve_id: str | None
    title: str | None
    asset_name: str
    status: str
    risk_score: float | None
    relevance_score: float = Field(ge=0, le=1)
    semantic_score: float = Field(ge=0, le=1)
    keyword_score: float = Field(ge=0, le=1)
    match_type: str
    snippet: str | None


class SearchResultOut(BaseModel):
    """Search results response."""
    query: str
    total: int
    limit: int
    offset: int
    results: list[SearchResultItem]


class SearchSuggestionsOut(BaseModel):
    """Search suggestions response."""
    query: str
    suggestions: list[str]

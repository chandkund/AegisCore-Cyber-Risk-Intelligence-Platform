"""Pydantic schemas for AI Security Assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssistantRequest(BaseModel):
    """Request to ask the AI assistant."""
    question: str = Field(..., min_length=1, max_length=1000)


class AssistantResponseOut(BaseModel):
    """Full assistant response with metadata."""
    answer: str = Field(description="Assistant's answer to the question")
    question_type: str = Field(description="Classified question type")
    supporting_records: list[dict[str, Any]] = Field(
        description="Records/data used to generate the answer"
    )
    confidence: str = Field(description="Confidence level: high, medium, low")
    suggested_followups: list[str] = Field(description="Suggested follow-up questions")
    generated_at: datetime = Field(description="When response was generated")


class AssistantQueryOut(BaseModel):
    """Lightweight assistant response."""
    answer: str
    question_type: str

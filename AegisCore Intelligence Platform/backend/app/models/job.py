"""Background job and task processing models.

Provides Job, JobLog, and related models for async processing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import Base, TimestampMixin, UUIDMixin
from app.constants import JobStatus, JobKind


class Job(Base, UUIDMixin):
    """Background job for async processing.
    
    Supports various job types: uploads, reports, imports, scans.
    """
    
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_jobs_tenant_created", "tenant_id", "created_at"),
        Index("ix_jobs_status_kind", "status", "job_kind"),
    )
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    
    # Job type and payload
    job_kind: Mapped[str] = mapped_column(
        String(50),
        default=JobKind.UPLOAD_PROCESSING.value,
        nullable=False,
        index=True,
    )
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        default=JobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False
    )
    
    # Timing
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Progress
    progress_percent: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False
    )
    current_step: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Results
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Actor tracking
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    
    # Retry logic
    retry_count: Mapped[int] = mapped_column(default=0, server_default="0")
    max_retries: Mapped[int] = mapped_column(default=3, server_default="3")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relationships
    logs: Mapped[list["JobLog"]] = relationship(
        back_populates="job",
        order_by="JobLog.created_at.desc()",
    )
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_user_id])
    
    def mark_started(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.RUNNING.value
        self.started_at = datetime.now(datetime.timezone.utc)
    
    def mark_completed(self, result: Optional[dict] = None) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED.value
        self.completed_at = datetime.now(datetime.timezone.utc)
        self.progress_percent = 100
        if result:
            self.result = result
    
    def mark_failed(self, error: str, details: Optional[dict] = None) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED.value
        self.completed_at = datetime.now(datetime.timezone.utc)
        self.error_message = error
        if details:
            self.error_details = details
    
    def update_progress(self, percent: int, step: Optional[str] = None) -> None:
        """Update job progress."""
        self.progress_percent = min(100, max(0, percent))
        if step:
            self.current_step = step


class JobLog(Base, UUIDMixin):
    """Detailed log entries for job execution."""
    
    __tablename__ = "job_logs"
    __table_args__ = (
        Index("ix_job_logs_job", "job_id"),
    )
    
    job_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    log_level: Mapped[str] = mapped_column(
        String(20), default="INFO", nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    job: Mapped["Job"] = relationship(back_populates="logs")


class ScheduledJob(Base, UUIDMixin):
    """Recurring scheduled job definitions."""
    
    __tablename__ = "scheduled_jobs"
    __table_args__ = (
        Index("ix_scheduled_jobs_tenant", "tenant_id"),
        Index("ix_scheduled_jobs_enabled", "is_enabled"),
    )
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    job_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Schedule (cron expression or interval)
    schedule_type: Mapped[str] = mapped_column(
        String(20), default="cron", nullable=False
    )
    schedule_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Status
    is_enabled: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

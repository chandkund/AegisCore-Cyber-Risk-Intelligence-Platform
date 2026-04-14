from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oltp import PrioritizationFeedback, VulnerabilityFinding
from app.services.job_service import JobService


class FeedbackService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    def submit(
        self,
        *,
        finding_id: uuid.UUID,
        feedback_type: str,
        notes: str | None,
        actor_user_id: uuid.UUID | None,
        queue_retrain: bool = True,
    ) -> dict:
        finding = self.db.execute(
            select(VulnerabilityFinding).where(
                VulnerabilityFinding.id == finding_id,
                VulnerabilityFinding.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()
        if finding is None:
            raise ValueError("Finding not found")
        row = PrioritizationFeedback(
            tenant_id=self.tenant_id,
            finding_id=finding_id,
            feedback_type=feedback_type,
            notes=notes,
            actor_user_id=actor_user_id,
        )
        self.db.add(row)
        self.db.flush()
        job = None
        if queue_retrain:
            job = JobService(self.db, tenant_id=self.tenant_id).enqueue(
                job_kind="model_retrain",
                payload={"reason": "new_feedback", "feedback_id": str(row.id)},
                actor_user_id=actor_user_id,
            )
        self.db.commit()
        return {
            "feedback_id": str(row.id),
            "finding_id": str(row.finding_id),
            "queued_retrain_job_id": job.id if job else None,
        }

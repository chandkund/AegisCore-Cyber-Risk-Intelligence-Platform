"""Add policy rules, prioritization feedback, and background jobs.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-14 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Skip if tables already exist (created by initial schema migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if "policy_rules" not in existing_tables:
        op.create_table(
            "policy_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("action", sa.String(length=64), nullable=False, server_default="flag"),
            sa.Column("severity", sa.String(length=16), nullable=False, server_default="MEDIUM"),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="RESTRICT"),
        )
        op.create_index("ix_policy_rules_tenant_id", "policy_rules", ["tenant_id"])
        op.create_index("ix_policy_rules_tenant_enabled", "policy_rules", ["tenant_id", "is_enabled"])

    if "prioritization_feedback" not in existing_tables:
        op.create_table(
            "prioritization_feedback",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("feedback_type", sa.String(length=32), nullable=False),
            sa.Column("notes", sa.String(length=2000), nullable=True),
            sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["finding_id"], ["vulnerability_findings.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_prioritization_feedback_tenant_id", "prioritization_feedback", ["tenant_id"])
        op.create_index("ix_prioritization_feedback_finding", "prioritization_feedback", ["finding_id"])
        op.create_index(
            "ix_prioritization_feedback_tenant_created",
            "prioritization_feedback",
            ["tenant_id", "created_at"],
        )

    if "background_jobs" not in existing_tables:
        op.create_table(
            "background_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("job_kind", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="QUEUED"),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_background_jobs_tenant_id", "background_jobs", ["tenant_id"])
        op.create_index("ix_background_jobs_tenant_status", "background_jobs", ["tenant_id", "status"])
        op.create_index("ix_background_jobs_kind_created", "background_jobs", ["job_kind", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_background_jobs_kind_created", table_name="background_jobs")
    op.drop_index("ix_background_jobs_tenant_status", table_name="background_jobs")
    op.drop_index("ix_background_jobs_tenant_id", table_name="background_jobs")
    op.drop_table("background_jobs")

    op.drop_index("ix_prioritization_feedback_tenant_created", table_name="prioritization_feedback")
    op.drop_index("ix_prioritization_feedback_finding", table_name="prioritization_feedback")
    op.drop_index("ix_prioritization_feedback_tenant_id", table_name="prioritization_feedback")
    op.drop_table("prioritization_feedback")

    op.drop_index("ix_policy_rules_tenant_enabled", table_name="policy_rules")
    op.drop_index("ix_policy_rules_tenant_id", table_name="policy_rules")
    op.drop_table("policy_rules")

"""Add remediation ticket integration table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-14 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "remediation_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_ticket_id", sa.String(length=128), nullable=False),
        sa.Column("external_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["finding_id"], ["vulnerability_findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            "external_ticket_id",
            name="uq_remediation_tickets_provider_external_per_tenant",
        ),
    )
    op.create_index("ix_remediation_tickets_tenant_id", "remediation_tickets", ["tenant_id"])
    op.create_index("ix_remediation_tickets_finding", "remediation_tickets", ["finding_id"])
    op.create_index(
        "ix_remediation_tickets_provider_status",
        "remediation_tickets",
        ["provider", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_remediation_tickets_provider_status", table_name="remediation_tickets")
    op.drop_index("ix_remediation_tickets_finding", table_name="remediation_tickets")
    op.drop_index("ix_remediation_tickets_tenant_id", table_name="remediation_tickets")
    op.drop_table("remediation_tickets")

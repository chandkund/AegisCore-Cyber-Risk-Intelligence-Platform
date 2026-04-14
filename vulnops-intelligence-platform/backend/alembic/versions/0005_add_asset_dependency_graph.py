"""Add asset dependency graph for attack-path analysis.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-14 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asset_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dependency_type", sa.String(length=64), nullable=False, server_default="network"),
        sa.Column("trust_level", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("lateral_movement_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tenant_id",
            "source_asset_id",
            "target_asset_id",
            name="uq_asset_dependencies_tenant_source_target",
        ),
    )
    op.create_index("ix_asset_dependencies_tenant_id", "asset_dependencies", ["tenant_id"])
    op.create_index(
        "ix_asset_dependencies_tenant_source",
        "asset_dependencies",
        ["tenant_id", "source_asset_id"],
    )
    op.create_index(
        "ix_asset_dependencies_tenant_target",
        "asset_dependencies",
        ["tenant_id", "target_asset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_asset_dependencies_tenant_target", table_name="asset_dependencies")
    op.drop_index("ix_asset_dependencies_tenant_source", table_name="asset_dependencies")
    op.drop_index("ix_asset_dependencies_tenant_id", table_name="asset_dependencies")
    op.drop_table("asset_dependencies")

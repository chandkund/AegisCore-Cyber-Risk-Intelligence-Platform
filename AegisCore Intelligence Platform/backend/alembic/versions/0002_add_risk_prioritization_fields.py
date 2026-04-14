"""Add risk prioritization fields to vulnerability_findings and assets.

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    finding_cols = {c["name"] for c in inspector.get_columns("vulnerability_findings")}
    if "risk_score" not in finding_cols:
        op.add_column("vulnerability_findings", sa.Column("risk_score", sa.Numeric(5, 2), nullable=True))
    if "risk_factors" not in finding_cols:
        op.add_column(
            "vulnerability_findings",
            sa.Column("risk_factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    if "risk_calculated_at" not in finding_cols:
        op.add_column("vulnerability_findings", sa.Column("risk_calculated_at", sa.DateTime(timezone=True), nullable=True))

    finding_indexes = {i["name"] for i in inspector.get_indexes("vulnerability_findings")}
    if "ix_findings_risk_score" not in finding_indexes:
        op.create_index("ix_findings_risk_score", "vulnerability_findings", ["risk_score"], postgresql_using="btree")

    asset_cols = {c["name"] for c in inspector.get_columns("assets")}
    if "is_external" not in asset_cols:
        op.add_column("assets", sa.Column("is_external", sa.Boolean(), server_default="false", nullable=False))

    asset_indexes = {i["name"] for i in inspector.get_indexes("assets")}
    if "ix_assets_is_external" not in asset_indexes:
        op.create_index("ix_assets_is_external", "assets", ["is_external"], postgresql_using="btree")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    finding_indexes = {i["name"] for i in inspector.get_indexes("vulnerability_findings")}
    if "ix_findings_risk_score" in finding_indexes:
        op.drop_index("ix_findings_risk_score", table_name="vulnerability_findings")

    asset_indexes = {i["name"] for i in inspector.get_indexes("assets")}
    if "ix_assets_is_external" in asset_indexes:
        op.drop_index("ix_assets_is_external", table_name="assets")

    finding_cols = {c["name"] for c in inspector.get_columns("vulnerability_findings")}
    if "risk_calculated_at" in finding_cols:
        op.drop_column("vulnerability_findings", "risk_calculated_at")
    if "risk_factors" in finding_cols:
        op.drop_column("vulnerability_findings", "risk_factors")
    if "risk_score" in finding_cols:
        op.drop_column("vulnerability_findings", "risk_score")

    asset_cols = {c["name"] for c in inspector.get_columns("assets")}
    if "is_external" in asset_cols:
        op.drop_column("assets", "is_external")

"""Add indexes for prioritization/search/simulation workloads.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-14 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    finding_indexes = {i["name"] for i in inspector.get_indexes("vulnerability_findings")}
    cve_indexes = {i["name"] for i in inspector.get_indexes("cve_records")}

    if "ix_findings_status_risk_score" not in finding_indexes:
        op.create_index(
            "ix_findings_status_risk_score",
            "vulnerability_findings",
            ["status", "risk_score"],
            postgresql_using="btree",
        )
    if "ix_findings_cve_record_id" not in finding_indexes:
        op.create_index(
            "ix_findings_cve_record_id",
            "vulnerability_findings",
            ["cve_record_id"],
            postgresql_using="btree",
        )
    if "ix_cve_records_exploit_available" not in cve_indexes:
        op.create_index(
            "ix_cve_records_exploit_available",
            "cve_records",
            ["exploit_available"],
            postgresql_using="btree",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    finding_indexes = {i["name"] for i in inspector.get_indexes("vulnerability_findings")}
    cve_indexes = {i["name"] for i in inspector.get_indexes("cve_records")}

    if "ix_findings_status_risk_score" in finding_indexes:
        op.drop_index("ix_findings_status_risk_score", table_name="vulnerability_findings")
    if "ix_findings_cve_record_id" in finding_indexes:
        op.drop_index("ix_findings_cve_record_id", table_name="vulnerability_findings")
    if "ix_cve_records_exploit_available" in cve_indexes:
        op.drop_index("ix_cve_records_exploit_available", table_name="cve_records")

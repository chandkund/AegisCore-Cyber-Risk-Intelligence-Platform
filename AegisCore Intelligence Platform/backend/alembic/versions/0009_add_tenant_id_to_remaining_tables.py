"""Add tenant_id to remaining tables for complete isolation

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-15 14:30:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table_name, column_name):
    """Check if a column exists in a table."""
    insp = sa.inspect(conn)
    columns = {col["name"] for col in insp.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    """Add tenant_id columns and indexes for strict tenant isolation."""
    conn = op.get_bind()
    insp = sa.inspect(conn)
    
    # Add tenant_id to business_units (if not exists)
    if not _column_exists(conn, "business_units", "tenant_id"):
        op.add_column(
            "business_units",
            sa.Column(
                "tenant_id",
                sa.UUID(),
                sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
                nullable=True,
                index=True,
            ),
        )
        op.create_index("ix_business_units_tenant", "business_units", ["tenant_id"])
        op.create_unique_constraint(
            "uq_business_units_tenant_code", "business_units", ["tenant_id", "code"]
        )
        # Remove old unique constraint on code alone (if exists)
        constraints = {c["name"] for c in insp.get_unique_constraints("business_units")}
        if "uq_business_units_code" in constraints:
            op.drop_constraint("uq_business_units_code", "business_units", type_="unique")
    
    # Add tenant_id to teams (if not exists)
    if not _column_exists(conn, "teams", "tenant_id"):
        op.add_column(
            "teams",
            sa.Column(
                "tenant_id",
                sa.UUID(),
                sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
                nullable=True,
                index=True,
            ),
        )
        op.create_index("ix_teams_tenant", "teams", ["tenant_id"])
        op.create_unique_constraint(
            "uq_teams_tenant_name", "teams", ["tenant_id", "name"]
        )
    
    # Add tenant_id to locations (if not exists)
    if not _column_exists(conn, "locations", "tenant_id"):
        op.add_column(
            "locations",
            sa.Column(
                "tenant_id",
                sa.UUID(),
                sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
                nullable=True,
                index=True,
            ),
        )
        op.create_index("ix_locations_tenant", "locations", ["tenant_id"])
        op.create_unique_constraint(
            "uq_locations_tenant_name", "locations", ["tenant_id", "name"]
        )
    
    # Add tenant_id to sla_policies (if not exists)
    if not _column_exists(conn, "sla_policies", "tenant_id"):
        op.add_column(
            "sla_policies",
            sa.Column(
                "tenant_id",
                sa.UUID(),
                sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
                nullable=True,
                index=True,
            ),
        )
        op.create_index("ix_sla_policies_tenant", "sla_policies", ["tenant_id"])
        op.create_unique_constraint(
            "uq_sla_policies_tenant_name", "sla_policies", ["tenant_id", "name"]
        )
        # Remove old unique constraint on name alone (if exists)
        constraints = {c["name"] for c in insp.get_unique_constraints("sla_policies")}
        if "uq_sla_policies_name" in constraints:
            op.drop_constraint("uq_sla_policies_name", "sla_policies", type_="unique")
    
    # Add tenant_id to audit_log (nullable for system-level events, if not exists)
    if not _column_exists(conn, "audit_log", "tenant_id"):
        op.add_column(
            "audit_log",
            sa.Column(
                "tenant_id",
                sa.UUID(),
                sa.ForeignKey("organizations.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
        )
        op.create_index("ix_audit_log_tenant", "audit_log", ["tenant_id"])


def downgrade() -> None:
    """Remove tenant_id columns."""
    # audit_log
    op.drop_index("ix_audit_log_tenant", "audit_log")
    op.drop_column("audit_log", "tenant_id")
    
    # sla_policies
    op.drop_constraint("uq_sla_policies_tenant_name", "sla_policies", type_="unique")
    op.create_unique_constraint("uq_sla_policies_name", "sla_policies", ["name"])
    op.drop_index("ix_sla_policies_tenant", "sla_policies")
    op.drop_column("sla_policies", "tenant_id")
    
    # locations
    op.drop_constraint("uq_locations_tenant_name", "locations", type_="unique")
    op.drop_index("ix_locations_tenant", "locations")
    op.drop_column("locations", "tenant_id")
    
    # teams
    op.drop_constraint("uq_teams_tenant_name", "teams", type_="unique")
    op.drop_index("ix_teams_tenant", "teams")
    op.drop_column("teams", "tenant_id")
    
    # business_units
    op.drop_constraint("uq_business_units_tenant_code", "business_units", type_="unique")
    op.create_unique_constraint("uq_business_units_code", "business_units", ["code"])
    op.drop_index("ix_business_units_tenant", "business_units")
    op.drop_column("business_units", "tenant_id")

"""Add organization tenant isolation foundation.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-14 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "organizations" not in tables:
        op.create_table(
            "organizations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("name", name="uq_organizations_name"),
            sa.UniqueConstraint("code", name="uq_organizations_code"),
        )
    org_indexes = {ix["name"] for ix in insp.get_indexes("organizations")}
    if "ix_organizations_code" not in org_indexes:
        op.create_index("ix_organizations_code", "organizations", ["code"])

    default_tid = "00000000-0000-4000-8000-000000000001"
    bind.execute(
        sa.text(
            """
            INSERT INTO organizations (id, name, code, is_active)
            VALUES (:id, 'Default Organization', 'default', true)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": default_tid},
    )

    users_cols = {c["name"] for c in insp.get_columns("users")}
    assets_cols = {c["name"] for c in insp.get_columns("assets")}
    findings_cols = {c["name"] for c in insp.get_columns("vulnerability_findings")}
    if "tenant_id" not in users_cols:
        op.add_column("users", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    if "tenant_id" not in assets_cols:
        op.add_column("assets", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    if "tenant_id" not in findings_cols:
        op.add_column("vulnerability_findings", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))

    bind.execute(sa.text("UPDATE users SET tenant_id = :tid WHERE tenant_id IS NULL"), {"tid": default_tid})
    bind.execute(sa.text("UPDATE assets SET tenant_id = :tid WHERE tenant_id IS NULL"), {"tid": default_tid})
    bind.execute(
        sa.text(
            """
            UPDATE vulnerability_findings vf
            SET tenant_id = a.tenant_id
            FROM assets a
            WHERE vf.asset_id = a.id AND vf.tenant_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text("UPDATE vulnerability_findings SET tenant_id = :tid WHERE tenant_id IS NULL"),
        {"tid": default_tid},
    )

    op.alter_column("users", "tenant_id", nullable=False)
    op.alter_column("assets", "tenant_id", nullable=False)
    op.alter_column("vulnerability_findings", "tenant_id", nullable=False)

    users_fks = {fk["name"] for fk in insp.get_foreign_keys("users")}
    assets_fks = {fk["name"] for fk in insp.get_foreign_keys("assets")}
    findings_fks = {fk["name"] for fk in insp.get_foreign_keys("vulnerability_findings")}
    if "fk_users_tenant_id" not in users_fks:
        op.create_foreign_key("fk_users_tenant_id", "users", "organizations", ["tenant_id"], ["id"], ondelete="RESTRICT")
    if "fk_assets_tenant_id" not in assets_fks:
        op.create_foreign_key("fk_assets_tenant_id", "assets", "organizations", ["tenant_id"], ["id"], ondelete="RESTRICT")
    if "fk_vulnerability_findings_tenant_id" not in findings_fks:
        op.create_foreign_key(
            "fk_vulnerability_findings_tenant_id",
            "vulnerability_findings",
            "organizations",
            ["tenant_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    users_ix = {ix["name"] for ix in insp.get_indexes("users")}
    assets_ix = {ix["name"] for ix in insp.get_indexes("assets")}
    findings_ix = {ix["name"] for ix in insp.get_indexes("vulnerability_findings")}
    if "ix_users_tenant_id" not in users_ix:
        op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    if "ix_assets_tenant_id" not in assets_ix:
        op.create_index("ix_assets_tenant_id", "assets", ["tenant_id"])
    if "ix_vulnerability_findings_tenant_id" not in findings_ix:
        op.create_index("ix_vulnerability_findings_tenant_id", "vulnerability_findings", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_vulnerability_findings_tenant_id", table_name="vulnerability_findings")
    op.drop_index("ix_assets_tenant_id", table_name="assets")
    op.drop_index("ix_users_tenant_id", table_name="users")

    op.drop_constraint("fk_vulnerability_findings_tenant_id", "vulnerability_findings", type_="foreignkey")
    op.drop_constraint("fk_assets_tenant_id", "assets", type_="foreignkey")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")

    op.drop_column("vulnerability_findings", "tenant_id")
    op.drop_column("assets", "tenant_id")
    op.drop_column("users", "tenant_id")

    op.drop_index("ix_organizations_code", table_name="organizations")
    op.drop_table("organizations")

"""Add SaaS identity enhancements and invitations.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-15 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    users_indexes = {ix["name"] for ix in insp.get_indexes("users")}
    users_uniques = {c["name"] for c in insp.get_unique_constraints("users")}

    if "uq_users_email" in users_uniques:
        op.drop_constraint("uq_users_email", "users", type_="unique")
    if "ix_users_tenant_email" not in users_indexes:
        op.create_index("ix_users_tenant_email", "users", ["tenant_id", "email"])
    if "uq_users_tenant_email" not in users_uniques:
        op.create_unique_constraint("uq_users_tenant_email", "users", ["tenant_id", "email"])

    # Skip if table already exists (created by initial schema migration)
    tables = insp.get_table_names()
    if "organization_invitations" in tables:
        return

    op.create_table(
        "organization_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role_name", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_org_invites_token_hash"),
    )
    op.create_index("ix_org_invites_tenant_email", "organization_invitations", ["tenant_id", "email"])
    op.create_index("ix_org_invites_expires_at", "organization_invitations", ["expires_at"])

    bind.execute(
        sa.text(
            """
            INSERT INTO roles (id, name, description)
            VALUES (:id, 'platform_owner', 'Platform super administrator')
            ON CONFLICT (name) DO NOTHING
            """
        ),
        {"id": "ffffffff-0000-4000-8000-000000000001"},
    )


def downgrade() -> None:
    op.drop_index("ix_org_invites_expires_at", table_name="organization_invitations")
    op.drop_index("ix_org_invites_tenant_email", table_name="organization_invitations")
    op.drop_table("organization_invitations")

    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")
    op.drop_index("ix_users_tenant_email", table_name="users")
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    op.execute(sa.text("DELETE FROM roles WHERE name = 'platform_owner'"))

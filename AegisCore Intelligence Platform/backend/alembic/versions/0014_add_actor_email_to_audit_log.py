"""Add actor_email to audit log for login traceability.

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-18 01:15:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {c["name"] for c in insp.get_columns("audit_log")}
    if "actor_email" not in columns:
        op.add_column("audit_log", sa.Column("actor_email", sa.String(length=320), nullable=True))

    indexes = {i["name"] for i in insp.get_indexes("audit_log")}
    if "ix_audit_log_actor_email" not in indexes:
        op.create_index("ix_audit_log_actor_email", "audit_log", ["actor_email"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    indexes = {i["name"] for i in insp.get_indexes("audit_log")}
    if "ix_audit_log_actor_email" in indexes:
        op.drop_index("ix_audit_log_actor_email", table_name="audit_log")

    columns = {c["name"] for c in insp.get_columns("audit_log")}
    if "actor_email" in columns:
        op.drop_column("audit_log", "actor_email")

"""Initial OLTP tables and reporting star schema.

Revision ID: 0001
Revises:
Create Date: 2026-04-11

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.base import Base
from app.models import oltp  # noqa: F401
from app.models import reporting  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS reporting"))
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    op.execute(sa.text("DROP SCHEMA IF EXISTS reporting CASCADE"))

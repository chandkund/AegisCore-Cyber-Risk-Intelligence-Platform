"""Add require_password_change column to users table.

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-17 16:30:00.000000

This migration adds a column to track whether a user must change their
password on next login (used for auto-generated passwords like platform owner).

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add require_password_change column to users table."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)

    def column_exists(table_name, column_name):
        columns = inspector.get_columns(table_name)
        return any(col['name'] == column_name for col in columns)

    def index_exists(table_name, index_name):
        indexes = inspector.get_indexes(table_name)
        return any(idx['name'] == index_name for idx in indexes)

    # Add require_password_change column (if not exists)
    if not column_exists("users", "require_password_change"):
        op.add_column(
            "users",
            sa.Column(
                "require_password_change",
                sa.Boolean(),
                nullable=False,
                server_default="false"
            )
        )

    # Create index for efficient querying (if not exists)
    if not index_exists("users", "ix_users_require_password_change"):
        op.create_index(
            "ix_users_require_password_change",
            "users",
            ["require_password_change"],
        )


def downgrade() -> None:
    """Remove require_password_change column from users table."""
    op.drop_index("ix_users_require_password_change", "users")
    op.drop_column("users", "require_password_change")

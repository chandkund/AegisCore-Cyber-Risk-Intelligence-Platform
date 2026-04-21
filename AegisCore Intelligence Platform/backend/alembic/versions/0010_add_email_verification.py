"""Add email verification OTP table and email_verified column.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email verification OTP table and email_verified column."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Add email_verified column to users if not exists
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    if "email_verified" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "email_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    
    # Create email_verification_otps table if not exists
    tables = inspector.get_table_names()
    if "email_verification_otps" not in tables:
        op.create_table(
            "email_verification_otps",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("code_hash", sa.String(255), nullable=False),
            sa.Column(
                "expires_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "max_attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("5"),
            ),
            sa.Column(
                "is_used",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )


def downgrade() -> None:
    """Remove email verification OTP table and email_verified column."""
    # Drop email_verification_otps table
    op.drop_table("email_verification_otps")
    
    # Drop email_verified column from users
    op.drop_column("users", "email_verified")

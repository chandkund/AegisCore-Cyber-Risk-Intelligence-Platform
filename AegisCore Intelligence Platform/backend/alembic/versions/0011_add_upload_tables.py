"""Add upload tracking tables for ownership model.

Revision ID: 0011
Revises: 0010
Create Date: 2024-01-15 10:00:00.000000

"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create upload_imports and upload_files tables."""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    def _index_exists(table_name: str, index_name: str) -> bool:
        return any(ix["name"] == index_name for ix in inspector.get_indexes(table_name))

    # Create upload_imports table for data imports
    if "upload_imports" not in existing_tables:
        op.create_table(
            "upload_imports",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "uploaded_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("upload_type", sa.String(64), nullable=False),
            sa.Column("original_filename", sa.String(255), nullable=True),
            sa.Column("file_size_bytes", sa.Integer(), nullable=True),
            sa.Column("mime_type", sa.String(128), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="processing"),
            sa.Column("summary", postgresql.JSONB(), nullable=True),
            sa.Column("processing_time_ms", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        inspector = inspect(conn)

    if "upload_imports" in set(inspector.get_table_names()):
        if not _index_exists("upload_imports", "ix_upload_imports_tenant_created"):
            op.create_index("ix_upload_imports_tenant_created", "upload_imports", ["tenant_id", "created_at"])
        if not _index_exists("upload_imports", "ix_upload_imports_tenant_type"):
            op.create_index("ix_upload_imports_tenant_type", "upload_imports", ["tenant_id", "upload_type"])
        if not _index_exists("upload_imports", "ix_upload_imports_status"):
            op.create_index("ix_upload_imports_status", "upload_imports", ["status"])
        if not _index_exists("upload_imports", "ix_upload_imports_uploader"):
            op.create_index("ix_upload_imports_uploader", "upload_imports", ["uploaded_by_user_id"])

    # Create upload_files table for document storage
    if "upload_files" not in set(inspector.get_table_names()):
        op.create_table(
            "upload_files",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "uploaded_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("upload_type", sa.String(64), nullable=False, server_default="document"),
            sa.Column("original_filename", sa.String(255), nullable=False),
            sa.Column("storage_path", sa.String(500), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False),
            sa.Column("mime_type", sa.String(128), nullable=True),
            sa.Column("description", sa.String(1000), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        inspector = inspect(conn)

    if "upload_files" in set(inspector.get_table_names()):
        if not _index_exists("upload_files", "ix_upload_files_tenant_created"):
            op.create_index("ix_upload_files_tenant_created", "upload_files", ["tenant_id", "created_at"])
        if not _index_exists("upload_files", "ix_upload_files_tenant_type"):
            op.create_index("ix_upload_files_tenant_type", "upload_files", ["tenant_id", "upload_type"])
        if not _index_exists("upload_files", "ix_upload_files_uploader"):
            op.create_index("ix_upload_files_uploader", "upload_files", ["uploaded_by_user_id"])


def downgrade() -> None:
    """Drop upload tables."""
    op.drop_table("upload_files")
    op.drop_table("upload_imports")

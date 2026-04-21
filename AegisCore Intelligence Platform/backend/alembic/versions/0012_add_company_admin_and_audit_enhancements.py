"""Add company admin and audit enhancements for platform owner system.

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-17 14:00:00.000000

This migration enhances the schema to support:
1. Platform owner users with nullable tenant_id
2. Company primary admin tracking
3. Enhanced audit logging with actor roles
4. Storage computation support via upload_files

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Apply schema enhancements for platform owner system."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)

    def column_exists(table_name, column_name):
        """Check if a column exists in a table."""
        columns = inspector.get_columns(table_name)
        return any(col['name'] == column_name for col in columns)

    def index_exists(table_name, index_name):
        """Check if an index exists on a table."""
        indexes = inspector.get_indexes(table_name)
        return any(idx['name'] == index_name for idx in indexes)

    def constraint_exists(table_name, constraint_name):
        """Check if a foreign-key constraint exists."""
        constraints = inspector.get_foreign_keys(table_name)
        return any(c.get('name') == constraint_name for c in constraints)

    def unique_constraint_exists(table_name, constraint_name):
        """Check if a unique constraint exists."""
        constraints = inspector.get_unique_constraints(table_name)
        return any(c['name'] == constraint_name for c in constraints)

    # =============================================================================
    # 1. ENHANCE organizations TABLE (Companies)
    # =============================================================================

    # Add slug column for URL-friendly company names
    if not column_exists("organizations", "slug"):
        op.add_column(
            "organizations",
            sa.Column("slug", sa.String(64), nullable=True, unique=True)
        )

    # Add status column for lifecycle management (pending, active, suspended)
    if not column_exists("organizations", "status"):
        op.add_column(
            "organizations",
            sa.Column(
                "status",
                sa.String(20),
                nullable=True,
                server_default="pending"
            )
        )

    # Add primary_admin_user_id for company admin tracking
    if not column_exists("organizations", "primary_admin_user_id"):
        op.add_column(
            "organizations",
            sa.Column(
                "primary_admin_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True
            )
        )

    # Add updated_at timestamp
    if not column_exists("organizations", "updated_at"):
        op.add_column(
            "organizations",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.func.now()
            )
        )

    # Create indexes for organizations
    if not index_exists("organizations", "ix_organizations_slug"):
        op.create_index(
            "ix_organizations_slug",
            "organizations",
            ["slug"],
            unique=True
        )
    if not index_exists("organizations", "ix_organizations_status"):
        op.create_index(
            "ix_organizations_status",
            "organizations",
            ["status"]
        )
    if not index_exists("organizations", "ix_organizations_primary_admin"):
        op.create_index(
            "ix_organizations_primary_admin",
            "organizations",
            ["primary_admin_user_id"]
        )
    
    # =============================================================================
    # 2. MODIFY users TABLE - Make tenant_id NULLABLE for platform owners
    # =============================================================================
    
    # Drop existing unique constraint temporarily
    if unique_constraint_exists("users", "uq_users_tenant_email"):
        op.drop_constraint("uq_users_tenant_email", "users", type_="unique")

    # Drop whichever tenant FK name exists (legacy or newer migration naming)
    if constraint_exists("users", "users_tenant_id_fkey"):
        op.drop_constraint("users_tenant_id_fkey", "users", type_="foreignkey")
    elif constraint_exists("users", "fk_users_tenant_id"):
        op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    
    # Modify tenant_id to be nullable
    op.alter_column(
        "users",
        "tenant_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True
    )
    
    if not constraint_exists("users", "users_tenant_id_fkey"):
        op.create_foreign_key(
            "users_tenant_id_fkey",
            "users",
            "organizations",
            ["tenant_id"],
            ["id"],
            ondelete="RESTRICT"
        )

    # Recreate unique constraint with nullable support
    if not unique_constraint_exists("users", "uq_users_tenant_email"):
        op.create_unique_constraint(
            "uq_users_tenant_email",
            "users",
            ["tenant_id", "email"]
        )

    # =============================================================================
    # 3. ENHANCE audit_log TABLE
    # =============================================================================

    # Add actor_role column to preserve role at time of action
    # Note: index=True on the model creates ix_audit_log_actor_role automatically
    if not column_exists("audit_log", "actor_role"):
        op.add_column(
            "audit_log",
            sa.Column("actor_role", sa.String(64), nullable=True)
        )

    # Create composite index for company + time queries
    if not index_exists("audit_log", "ix_audit_log_company_time"):
        op.create_index(
            "ix_audit_log_company_time",
            "audit_log",
            ["tenant_id", "occurred_at"]
        )

    # =============================================================================
    # 4. ENSURE upload_files HAS ALL NEEDED FIELDS FOR STORAGE COMPUTATION
    # =============================================================================

    # Create index for storage aggregation queries
    if not index_exists("upload_files", "ix_upload_files_tenant_size"):
        op.create_index(
            "ix_upload_files_tenant_size",
            "upload_files",
            ["tenant_id", "file_size_bytes"]
        )
    
    # =============================================================================
    # 5. DATA MIGRATION: Set existing company statuses
    # =============================================================================
    
    # Set status based on existing is_active and approval_status
    op.execute("""
        UPDATE organizations
        SET status = CASE
            WHEN is_active = false THEN 'suspended'
            WHEN approval_status = 'approved' THEN 'active'
            ELSE 'pending'
        END
        WHERE status IS NULL;
    """)
    
    # Set slugs based on code (URL-friendly version)
    op.execute("""
        UPDATE organizations
        SET slug = LOWER(REGEXP_REPLACE(code, '[^a-zA-Z0-9]+', '-', 'g'))
        WHERE slug IS NULL;
    """)
    
    # Set updated_at for existing records
    op.execute("""
        UPDATE organizations
        SET updated_at = created_at
        WHERE updated_at IS NULL;
    """)


def downgrade() -> None:
    """Revert schema enhancements."""
    
    # =============================================================================
    # 1. REVERT upload_files indexes
    # =============================================================================
    op.drop_index("ix_upload_files_tenant_size", "upload_files")
    
    # =============================================================================
    # 2. REVERT audit_log enhancements
    # =============================================================================
    op.drop_index("ix_audit_log_company_time", "audit_log")
    # Note: ix_audit_log_actor_role is auto-managed by SQLAlchemy via index=True
    op.drop_column("audit_log", "actor_role")
    
    # =============================================================================
    # 3. REVERT users TABLE - Make tenant_id NOT NULL again
    # =============================================================================
    
    # NOTE: This will fail if there are users with NULL tenant_id
    # We need to handle platform_owner users first
    
    # Check if there are any NULL tenant_id users
    result = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM users WHERE tenant_id IS NULL")
    ).scalar()
    
    if result > 0:
        # Assign NULL users to first organization or create a placeholder
        op.execute("""
            UPDATE users
            SET tenant_id = (SELECT id FROM organizations ORDER BY created_at LIMIT 1)
            WHERE tenant_id IS NULL;
        """)
    
    # Drop constraint and foreign key
    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")
    op.drop_constraint("users_tenant_id_fkey", "users", type_="foreignkey")
    
    # Make tenant_id NOT NULL
    op.alter_column(
        "users",
        "tenant_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False
    )
    
    # Recreate foreign key and constraint
    op.create_foreign_key(
        "users_tenant_id_fkey",
        "users",
        "organizations",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT"
    )
    op.create_unique_constraint(
        "uq_users_tenant_email",
        "users",
        ["tenant_id", "email"]
    )
    
    # =============================================================================
    # 4. REVERT organizations TABLE
    # =============================================================================
    op.drop_index("ix_organizations_primary_admin", "organizations")
    op.drop_index("ix_organizations_status", "organizations")
    op.drop_index("ix_organizations_slug", "organizations")
    
    op.drop_column("organizations", "updated_at")
    op.drop_column("organizations", "primary_admin_user_id")
    op.drop_column("organizations", "status")
    op.drop_column("organizations", "slug")

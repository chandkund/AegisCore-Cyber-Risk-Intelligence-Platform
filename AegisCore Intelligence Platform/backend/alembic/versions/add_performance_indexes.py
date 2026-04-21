"""Add performance indexes for frequently queried columns.

Revision ID: add_performance_indexes
Revises: previous_revision
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = None  # Set to your previous migration
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes."""
    # Findings indexes
    op.create_index(
        'ix_findings_tenant_id_status',
        'findings',
        ['tenant_id', 'status']
    )
    op.create_index(
        'ix_findings_tenant_id_severity',
        'findings',
        ['tenant_id', 'severity']
    )
    op.create_index(
        'ix_findings_tenant_id_created_at',
        'findings',
        ['tenant_id', 'created_at']
    )
    op.create_index(
        'ix_findings_tenant_id_cve_id',
        'findings',
        ['tenant_id', 'cve_id']
    )
    op.create_index(
        'ix_findings_status_severity',
        'findings',
        ['status', 'severity']
    )

    # Assets indexes
    op.create_index(
        'ix_assets_tenant_id_criticality',
        'assets',
        ['tenant_id', 'criticality']
    )
    op.create_index(
        'ix_assets_tenant_id_created_at',
        'assets',
        ['tenant_id', 'created_at']
    )

    # Vulnerabilities indexes
    op.create_index(
        'ix_vulnerabilities_tenant_id_cvss_score',
        'vulnerabilities',
        ['tenant_id', 'cvss_score']
    )
    op.create_index(
        'ix_vulnerabilities_tenant_id_risk_score',
        'vulnerabilities',
        ['tenant_id', 'risk_score']
    )

    # Jobs indexes
    op.create_index(
        'ix_jobs_tenant_id_status',
        'jobs',
        ['tenant_id', 'status']
    )
    op.create_index(
        'ix_jobs_tenant_id_created_at',
        'jobs',
        ['tenant_id', 'created_at']
    )

    # Upload files indexes
    op.create_index(
        'ix_upload_files_tenant_id_created_at',
        'upload_files',
        ['tenant_id', 'created_at']
    )

    # Audit logs indexes
    op.create_index(
        'ix_audit_logs_tenant_id_created_at',
        'audit_logs',
        ['tenant_id', 'created_at']
    )
    op.create_index(
        'ix_audit_logs_action',
        'audit_logs',
        ['action']
    )

    # Users indexes
    op.create_index(
        'ix_users_tenant_id_role',
        'users',
        ['tenant_id', 'role']
    )
    op.create_index(
        'ix_users_email',
        'users',
        ['email']
    )

    # Tickets indexes
    op.create_index(
        'ix_tickets_finding_id',
        'tickets',
        ['finding_id']
    )
    op.create_index(
        'ix_tickets_tenant_id_status',
        'tickets',
        ['tenant_id', 'status']
    )

    # Policy rules indexes
    op.create_index(
        'ix_policy_rules_tenant_id_enabled',
        'policy_rules',
        ['tenant_id', 'is_enabled']
    )

    print("Performance indexes added successfully")


def downgrade():
    """Remove performance indexes."""
    # Findings
    op.drop_index('ix_findings_tenant_id_status', table_name='findings')
    op.drop_index('ix_findings_tenant_id_severity', table_name='findings')
    op.drop_index('ix_findings_tenant_id_created_at', table_name='findings')
    op.drop_index('ix_findings_tenant_id_cve_id', table_name='findings')
    op.drop_index('ix_findings_status_severity', table_name='findings')

    # Assets
    op.drop_index('ix_assets_tenant_id_criticality', table_name='assets')
    op.drop_index('ix_assets_tenant_id_created_at', table_name='assets')

    # Vulnerabilities
    op.drop_index('ix_vulnerabilities_tenant_id_cvss_score', table_name='vulnerabilities')
    op.drop_index('ix_vulnerabilities_tenant_id_risk_score', table_name='vulnerabilities')

    # Jobs
    op.drop_index('ix_jobs_tenant_id_status', table_name='jobs')
    op.drop_index('ix_jobs_tenant_id_created_at', table_name='jobs')

    # Upload files
    op.drop_index('ix_upload_files_tenant_id_created_at', table_name='upload_files')

    # Audit logs
    op.drop_index('ix_audit_logs_tenant_id_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')

    # Users
    op.drop_index('ix_users_tenant_id_role', table_name='users')
    op.drop_index('ix_users_email', table_name='users')

    # Tickets
    op.drop_index('ix_tickets_finding_id', table_name='tickets')
    op.drop_index('ix_tickets_tenant_id_status', table_name='tickets')

    # Policy rules
    op.drop_index('ix_policy_rules_tenant_id_enabled', table_name='policy_rules')

    print("Performance indexes removed")

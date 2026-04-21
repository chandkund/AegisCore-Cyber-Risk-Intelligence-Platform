from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import PlatformOwnerDep
from app.db.deps import get_db
from app.schemas.common import Paginated
from app.schemas.platform import (
    AdminPasswordReset,
    PlatformMetricsOut,
    PlatformStatsOut,
    TenantCreate,
    TenantDetailOut,
    TenantOut,
    TenantUpdate,
    TenantWithAdminsOut,
    TenantAdminOut,
)
from app.repositories.organization_repository import OrganizationRepository

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/tenants", response_model=Paginated[TenantOut])
def list_tenants(
    _: PlatformOwnerDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    approval_status: str | None = Query(None, description="Filter by approval status: pending, approved, rejected"),
):
    """List all tenants with optional approval status filter."""
    repo = OrganizationRepository(db)
    if approval_status:
        rows, total = repo.list_by_approval_status(status=approval_status, limit=limit, offset=offset)
    else:
        rows, total = repo.list(limit=limit, offset=offset)
    return Paginated(
        items=[
            TenantOut(
                id=str(r.id),
                name=r.name,
                code=r.code,
                is_active=r.is_active,
                approval_status=r.approval_status,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/tenants/{tenant_id}", response_model=TenantDetailOut)
def get_tenant(
    _: PlatformOwnerDep,
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get tenant details including approval information."""
    from app.repositories.user_repository import UserRepository

    repo = OrganizationRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    user_count = repo.get_user_count(tenant_id)

    # Get approver name if available
    approved_by_name = None
    if tenant.approved_by_user_id:
        approver = UserRepository(db).get_by_id(tenant.approved_by_user_id)
        approved_by_name = approver.full_name if approver else None

    return TenantDetailOut(
        id=str(tenant.id),
        name=tenant.name,
        code=tenant.code,
        is_active=tenant.is_active,
        approval_status=tenant.approval_status,
        approval_notes=tenant.approval_notes,
        approved_at=tenant.approved_at,
        approved_by=approved_by_name,
        created_at=tenant.created_at,
        user_count=user_count,
    )


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
def update_tenant(
    principal: PlatformOwnerDep,
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    db: Session = Depends(get_db),
):
    """Update tenant status and approval settings."""
    from datetime import datetime, timezone

    repo = OrganizationRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Update status fields
    if body.is_active is not None:
        tenant.is_active = body.is_active

    if body.approval_status is not None:
        tenant.approval_status = body.approval_status
        # If approving, record who and when
        if body.approval_status == "approved":
            tenant.approved_at = datetime.now(timezone.utc)
            tenant.approved_by_user_id = principal.id
        elif body.approval_status == "pending":
            # Reset approval info when setting back to pending
            tenant.approved_at = None
            tenant.approved_by_user_id = None

    if body.approval_notes is not None:
        tenant.approval_notes = body.approval_notes

    repo.update(tenant)
    db.commit()
    return TenantOut(
        id=str(tenant.id),
        name=tenant.name,
        code=tenant.code,
        is_active=tenant.is_active,
        approval_status=tenant.approval_status,
        created_at=tenant.created_at,
    )


@router.get("/stats", response_model=PlatformStatsOut)
def get_platform_stats(
    _: PlatformOwnerDep,
    db: Session = Depends(get_db),
):
    """Get platform-wide statistics including approval metrics."""
    stats = OrganizationRepository(db).get_platform_stats()
    return PlatformStatsOut(**stats)


@router.get("/metrics", response_model=PlatformMetricsOut)
def get_platform_metrics(
    _: PlatformOwnerDep,
    db: Session = Depends(get_db),
):
    """Get detailed platform metrics for dashboard."""
    stats = OrganizationRepository(db).get_detailed_platform_metrics()
    return PlatformMetricsOut(**stats)


@router.post("/tenants", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(
    principal: PlatformOwnerDep,
    body: TenantCreate,
    db: Session = Depends(get_db),
):
    """Manually create a company/tenant as platform owner.
    
    This allows the platform owner to create a company without going through
    the self-registration process, useful for enterprise sales or manual onboarding.
    """
    from app.services.auth_service import AuthService
    from app.core.security import hash_password
    from app.models.oltp import Organization, User
    from app.core import rbac

    # Check if code already exists
    existing = OrganizationRepository(db).get_by_code(body.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company code already exists",
        )

    # Create the organization
    org = Organization(
        name=body.name,
        code=body.code.strip().lower(),
        is_active=body.is_active,
        approval_status=body.approval_status,
        approved_at=datetime.now(timezone.utc) if body.approval_status == "approved" else None,
        approved_by_user_id=principal.id if body.approval_status == "approved" else None,
    )
    db.add(org)
    db.flush()

    # Create the admin user
    from app.repositories.user_repository import UserRepository
    
    # Check if email already exists
    if UserRepository(db).get_by_email(body.admin_email.strip().lower(), tenant_id=org.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin email already exists for this company",
        )

    admin_user = User(
        tenant_id=org.id,
        email=body.admin_email.strip().lower(),
        full_name=body.admin_full_name,
        hashed_password=hash_password(body.admin_password),
        is_active=True,
    )
    db.add(admin_user)
    db.flush()

    # Assign admin role
    admin_role = UserRepository(db).get_role_by_name(rbac.ROLE_ADMIN)
    if admin_role:
        UserRepository(db).add_role(admin_user.id, admin_role.id)

    db.commit()

    return TenantOut(
        id=str(org.id),
        name=org.name,
        code=org.code,
        is_active=org.is_active,
        approval_status=org.approval_status,
        created_at=org.created_at,
    )


@router.get("/tenants/{tenant_id}/admins", response_model=list[TenantAdminOut])
def get_tenant_admins(
    _: PlatformOwnerDep,
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get all admin users for a specific company.
    
    This helps platform owners manage and support company administrators.
    """
    repo = OrganizationRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    admins = repo.get_company_admins(tenant_id)
    return [
        TenantAdminOut(
            id=str(admin.id),
            email=admin.email,
            full_name=admin.full_name,
            is_active=admin.is_active,
            roles=[ur.role.name for ur in admin.roles if ur.role],
            created_at=admin.created_at,
            last_login_at=None,  # Would need to track last login
        )
        for admin in admins
    ]


@router.post("/tenants/{tenant_id}/admins/{admin_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_admin_password(
    _: PlatformOwnerDep,
    tenant_id: uuid.UUID,
    admin_id: uuid.UUID,
    body: AdminPasswordReset,
    db: Session = Depends(get_db),
):
    """Reset a company admin's password.
    
    This is an emergency access recovery mechanism for platform owners.
    The admin will be forced to change their password on next login if configured.
    """
    from app.repositories.user_repository import UserRepository
    from app.core.security import hash_password

    repo = OrganizationRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    user_repo = UserRepository(db)
    admin = user_repo.get_by_id(admin_id)
    if not admin or admin.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    # Verify the user is an admin
    is_admin = any(
        ur.role and ur.role.name == "admin" for ur in admin.roles
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not an admin",
        )

    # Reset password
    admin.hashed_password = hash_password(body.new_password)
    # TODO: Add require_password_change field to User model if needed
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Upload Governance Endpoints (Platform Owner)
# ============================================================================

@router.get("/uploads/imports", response_model=dict)
def list_all_import_uploads(
    _: PlatformOwnerDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    upload_type: str | None = Query(None, description="Filter by type: assets_import, vulnerabilities_import, mappings_import"),
    status: str | None = Query(None, description="Filter by status: processing, completed, failed, partial"),
):
    """List all data import uploads across all tenants.

    Platform Owner governance view for upload activity monitoring.
    Shows import history, processing status, and results.
    """
    from app.models.oltp import UploadImport

    query = db.query(UploadImport)

    if upload_type:
        query = query.filter(UploadImport.upload_type == upload_type)
    if status:
        query = query.filter(UploadImport.status == status)

    total = query.count()
    uploads = query.order_by(UploadImport.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(u.id),
                "tenant_id": str(u.tenant_id),
                "upload_type": u.upload_type,
                "original_filename": u.original_filename,
                "file_size_bytes": u.file_size_bytes,
                "status": u.status,
                "summary": u.summary,
                "processing_time_ms": u.processing_time_ms,
                "uploaded_by_user_id": str(u.uploaded_by_user_id) if u.uploaded_by_user_id else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "completed_at": u.completed_at.isoformat() if u.completed_at else None,
            }
            for u in uploads
        ],
    }


@router.get("/uploads/files", response_model=dict)
def list_all_file_uploads(
    _: PlatformOwnerDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    upload_type: str | None = Query(None, description="Filter by type: document, scan_report, evidence"),
):
    """List all file uploads across all tenants.

    Platform Owner governance view for file storage monitoring.
    Shows document/report uploads and storage usage.
    """
    from app.models.oltp import UploadFile

    query = db.query(UploadFile)

    if upload_type:
        query = query.filter(UploadFile.upload_type == upload_type)

    total = query.count()
    uploads = query.order_by(UploadFile.created_at.desc()).offset(offset).limit(limit).all()

    # Calculate storage stats
    total_size = db.query(UploadFile).with_entities(
        db.func.sum(UploadFile.file_size_bytes)
    ).scalar() or 0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "total_storage_bytes": total_size,
        "items": [
            {
                "id": str(u.id),
                "tenant_id": str(u.tenant_id),
                "upload_type": u.upload_type,
                "original_filename": u.original_filename,
                "storage_path": u.storage_path,
                "file_size_bytes": u.file_size_bytes,
                "mime_type": u.mime_type,
                "uploaded_by_user_id": str(u.uploaded_by_user_id) if u.uploaded_by_user_id else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in uploads
        ],
    }


@router.get("/tenants/{tenant_id}/uploads", response_model=dict)
def list_tenant_uploads(
    _: PlatformOwnerDep,
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all uploads for a specific tenant.

    Shows both data imports and file uploads for a company.
    Useful for support and troubleshooting.
    """
    from app.models.oltp import UploadImport, UploadFile

    # Get imports
    imports_query = db.query(UploadImport).filter(UploadImport.tenant_id == tenant_id)
    imports_total = imports_query.count()
    imports = imports_query.order_by(UploadImport.created_at.desc()).offset(offset).limit(limit).all()

    # Get files
    files_query = db.query(UploadFile).filter(UploadFile.tenant_id == tenant_id)
    files_total = files_query.count()
    files = files_query.order_by(UploadFile.created_at.desc()).offset(offset).limit(limit).all()

    # Calculate storage for this tenant
    tenant_storage = db.query(UploadFile).filter(
        UploadFile.tenant_id == tenant_id
    ).with_entities(
        db.func.sum(UploadFile.file_size_bytes)
    ).scalar() or 0

    return {
        "tenant_id": str(tenant_id),
        "storage_bytes": tenant_storage,
        "imports": {
            "total": imports_total,
            "items": [
                {
                    "id": str(i.id),
                    "upload_type": i.upload_type,
                    "original_filename": i.original_filename,
                    "status": i.status,
                    "summary": i.summary,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in imports
            ],
        },
        "files": {
            "total": files_total,
            "items": [
                {
                    "id": str(f.id),
                    "upload_type": f.upload_type,
                    "original_filename": f.original_filename,
                    "file_size_bytes": f.file_size_bytes,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in files
            ],
        },
    }


@router.get("/storage/stats", response_model=dict)
def get_storage_stats(
    _: PlatformOwnerDep,
    db: Session = Depends(get_db),
):
    """Get platform-wide storage statistics.

    Shows storage usage per tenant and total.
    Useful for capacity planning and billing.
    """
    from app.models.oltp import UploadFile

    # Total storage
    total_storage = db.query(UploadFile).with_entities(
        db.func.sum(UploadFile.file_size_bytes)
    ).scalar() or 0

    # File count
    total_files = db.query(UploadFile).count()

    # Storage by tenant
    tenant_storage = db.query(
        UploadFile.tenant_id,
        db.func.sum(UploadFile.file_size_bytes).label("total_bytes"),
        db.func.count(UploadFile.id).label("file_count"),
    ).group_by(UploadFile.tenant_id).all()

    return {
        "total_storage_bytes": total_storage,
        "total_files": total_files,
        "tenants": [
            {
                "tenant_id": str(ts.tenant_id),
                "storage_bytes": ts.total_bytes or 0,
                "file_count": ts.file_count,
            }
            for ts in tenant_storage
        ],
    }


# ============================================================================
# Audit Logs Endpoint (Platform Owner)
# ============================================================================

@router.get("/audit-logs", response_model=dict)
def get_audit_logs(
    _: PlatformOwnerDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: uuid.UUID | None = Query(None, description="Filter by tenant"),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    from_date: datetime | None = Query(None, description="Filter from date (ISO format)"),
    to_date: datetime | None = Query(None, description="Filter to date (ISO format)"),
):
    """Get platform-wide audit logs.

    Platform Owner view of all audit events across all tenants.
    Useful for security monitoring, compliance, and troubleshooting.
    """
    from app.models.oltp import AuditLog, Organization, User

    query = db.query(
        AuditLog,
        Organization.name.label("tenant_name"),
        User.email.label("actor_email"),
    ).outerjoin(
        Organization, AuditLog.tenant_id == Organization.id
    ).outerjoin(
        User, AuditLog.actor_user_id == User.id
    )

    # Apply filters
    if tenant_id:
        query = query.filter(AuditLog.tenant_id == tenant_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if from_date:
        query = query.filter(AuditLog.occurred_at >= from_date)
    if to_date:
        query = query.filter(AuditLog.occurred_at <= to_date)

    total = query.count()
    logs = query.order_by(AuditLog.occurred_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(log.AuditLog.id),
                "tenant_id": str(log.AuditLog.tenant_id) if log.AuditLog.tenant_id else None,
                "tenant_name": log.tenant_name,
                "actor_user_id": str(log.AuditLog.actor_user_id) if log.AuditLog.actor_user_id else None,
                "actor_email": log.actor_email,
                "action": log.AuditLog.action,
                "resource_type": log.AuditLog.resource_type,
                "resource_id": log.AuditLog.resource_id,
                "payload": log.AuditLog.payload,
                "occurred_at": log.AuditLog.occurred_at.isoformat() if log.AuditLog.occurred_at else None,
            }
            for log in logs
        ],
    }


@router.get("/audit-logs/summary", response_model=dict)
def get_audit_logs_summary(
    _: PlatformOwnerDep,
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90, description="Number of days to summarize"),
):
    """Get audit logs summary statistics.

    Shows action counts and trends for the specified period.
    """
    from app.models.oltp import AuditLog
    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Total actions in period
    total_actions = db.query(AuditLog).filter(AuditLog.occurred_at >= since).count()

    # Actions by type
    action_counts = db.query(
        AuditLog.action,
        db.func.count(AuditLog.id).label("count"),
    ).filter(
        AuditLog.occurred_at >= since
    ).group_by(AuditLog.action).all()

    # Actions by tenant
    tenant_counts = db.query(
        AuditLog.tenant_id,
        db.func.count(AuditLog.id).label("count"),
    ).filter(
        AuditLog.occurred_at >= since
    ).group_by(AuditLog.tenant_id).all()

    # Actions by day (for trend)
    daily_counts = db.query(
        db.func.date_trunc('day', AuditLog.occurred_at).label("day"),
        db.func.count(AuditLog.id).label("count"),
    ).filter(
        AuditLog.occurred_at >= since
    ).group_by(
        db.func.date_trunc('day', AuditLog.occurred_at)
    ).order_by("day").all()

    return {
        "period_days": days,
        "total_actions": total_actions,
        "actions_by_type": [
            {"action": ac.action, "count": ac.count}
            for ac in action_counts
        ],
        "actions_by_tenant": [
            {"tenant_id": str(tc.tenant_id) if tc.tenant_id else "platform", "count": tc.count}
            for tc in tenant_counts
        ],
        "daily_trend": [
            {"date": dc.day.isoformat() if dc.day else None, "count": dc.count}
            for dc in daily_counts
        ],
    }

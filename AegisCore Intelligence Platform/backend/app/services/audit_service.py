from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.oltp import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        actor_user_id: uuid.UUID | None,
        actor_email: str | None = None,
        actor_role: str | None = None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        tenant_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Record an audit log entry.

        Args:
            actor_user_id: The user who performed the action
            action: The action performed (e.g., "TENANT_CREATE", "FILE_UPLOAD")
            resource_type: The type of resource affected
            resource_id: Optional ID of the affected resource
            tenant_id: Optional tenant ID for platform owner actions
            payload: Optional additional data about the action

        Returns:
            The created AuditLog entry
        """
        row = AuditLog(
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            payload=payload,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def log_authentication(
        self,
        *,
        request: Request,
        action: str,  # "LOGIN_SUCCESS", "LOGIN_FAILURE", "LOGOUT", "MFA_SUCCESS", "MFA_FAILURE"
        actor_user_id: uuid.UUID | None = None,
        email: str | None = None,
        tenant_id: uuid.UUID | None = None,
        success: bool,
        failure_reason: str | None = None,
        mfa_method: str | None = None,
    ) -> AuditLog:
        """Log authentication events.
        
        Captures client IP, user agent, and other security-relevant information.
        """
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        payload = {
            "success": success,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }
        
        if failure_reason:
            payload["failure_reason"] = failure_reason
        if mfa_method:
            payload["mfa_method"] = mfa_method
            
        return self.record(
            actor_user_id=actor_user_id,
            actor_email=email,
            action=action,
            resource_type="authentication",
            resource_id=str(actor_user_id) if actor_user_id else None,
            tenant_id=tenant_id,
            payload=payload,
        )

    def log_user_management(
        self,
        *,
        request: Request,
        action: str,  # "USER_CREATE", "USER_UPDATE", "USER_DELETE", "USER_DISABLE"
        actor_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
        changes: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log user management events."""
        client_ip = self._get_client_ip(request)
        
        payload = {
            "client_ip": client_ip,
            "target_user_id": str(target_user_id),
        }
        
        if changes:
            # Don't log sensitive fields like passwords
            safe_changes = {k: v for k, v in changes.items() 
                          if k not in ("password", "password_hash", "secret")}
            payload["changes"] = safe_changes
            
        return self.record(
            actor_user_id=actor_user_id,
            action=action,
            resource_type="user",
            resource_id=str(target_user_id),
            tenant_id=tenant_id,
            payload=payload,
        )

    def log_data_access(
        self,
        *,
        request: Request,
        action: str,  # "READ", "WRITE", "DELETE"
        actor_user_id: uuid.UUID,
        resource_type: str,
        resource_id: str | None = None,
        tenant_id: uuid.UUID | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log data access events."""
        client_ip = self._get_client_ip(request)
        
        payload = {
            "client_ip": client_ip,
            "method": request.method,
            "path": str(request.url.path),
        }
        
        if query_params:
            payload["query_params"] = query_params
            
        return self.record(
            actor_user_id=actor_user_id,
            action=f"DATA_{action}",
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            payload=payload,
        )

    def log_security_event(
        self,
        *,
        request: Request,
        event_type: str,  # "SUSPICIOUS_ACTIVITY", "RATE_LIMIT_HIT", "CSRF_VIOLATION", etc.
        severity: str,  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
        actor_user_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log security-related events."""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        payload = {
            "severity": severity,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "path": str(request.url.path),
            "method": request.method,
        }
        
        if details:
            payload["details"] = details
            
        return self.record(
            actor_user_id=actor_user_id,
            action=f"SECURITY_{event_type}",
            resource_type="security",
            payload=payload,
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check for forwarded IP (behind proxy)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
            
        if request.client:
            return request.client.host
            
        return "unknown"

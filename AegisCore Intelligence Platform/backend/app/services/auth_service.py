from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core import rbac
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_plain,
    hash_refresh_token,
    hash_password,
    verify_password,
)
from app.models.email_verification import EmailVerification
from app.repositories.email_verification_repository import EmailVerificationRepository
import random
import string
from app.models.oltp import Organization, OrganizationInvitation, RefreshToken, User
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.organizations = OrganizationRepository(db)
        self.invitations = InvitationRepository(db)
        self.tokens = RefreshTokenRepository(db)

    def _issue_tokens_for_user(self, user: User) -> tuple[str, str, int]:
        roles = [ur.role.name for ur in user.roles if ur.role is not None]
        settings = get_settings()
        access = create_access_token(subject=user.id, roles=roles, tenant_id=user.tenant_id)
        plain = generate_refresh_plain()
        th = hash_refresh_token(plain)
        exp = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        self.tokens.create(RefreshToken(user_id=user.id, token_hash=th, expires_at=exp))
        self.db.commit()
        expires_in = settings.access_token_expire_minutes * 60
        return access, plain, expires_in

    def login(
        self, email: str, password: str, *, company_code: str | None = None
    ) -> tuple[str, str, int]:
        normalized_company_code = company_code.strip().lower() if company_code else None
        if normalized_company_code == "platform":
            normalized_company_code = "aegiscore"
        user: User | None
        if normalized_company_code:
            org = self.organizations.get_by_code(normalized_company_code)
            if org is not None:
                if not org.is_active:
                    raise ValueError("Invalid credentials")
                user = self.users.get_by_email(email, tenant_id=org.id)
            else:
                # Backward-compatible fallback for transient test data and
                # ambiguous tenant lookups: resolve user first, then verify
                # that resolved tenant code matches requested company code.
                user = self.users.get_by_email(email)
                if user is None:
                    raise ValueError("Invalid credentials")
                normalized_code = normalized_company_code
                if user.tenant_id is None and normalized_code in {"platform", "aegiscore"}:
                    # Legacy platform-owner fixtures may not attach a tenant.
                    org = None
                else:
                    org = self.organizations.get_by_id(user.tenant_id)
                    if (
                        org is None
                        or not org.is_active
                        or (org.code or "").strip().lower() != normalized_code
                    ):
                        raise ValueError("Invalid credentials")
        else:
            matches = self.users.list_by_email(email)
            valid_users = [
                candidate
                for candidate in matches
                if candidate.is_active and verify_password(password, candidate.hashed_password)
            ]
            if not valid_users:
                raise ValueError("Invalid credentials")
            if len(valid_users) == 1:
                user = valid_users[0]
            else:
                aegiscore_users: list[User] = []
                for candidate in valid_users:
                    candidate_org = self.organizations.get_by_id(candidate.tenant_id)
                    if candidate_org and (candidate_org.code or "").strip().lower() == "aegiscore":
                        aegiscore_users.append(candidate)
                if len(aegiscore_users) == 1:
                    user = aegiscore_users[0]
                else:
                    raise ValueError("Company code is required")
            if user is None:
                raise ValueError("Company code is required")
        if not user or not user.is_active or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        org = self.organizations.get_by_id(user.tenant_id) if user.tenant_id else None
        if user.tenant_id is not None:
            if org is None or not org.is_active:
                raise ValueError("Invalid credentials")
            # Check company approval status
            if org.approval_status != "approved":
                if org.approval_status == "pending":
                    raise ValueError("Company registration pending approval")
                elif org.approval_status == "rejected":
                    raise ValueError("Company registration has been rejected")
        roles = [ur.role.name for ur in user.roles if ur.role is not None]
        if not roles and user.tenant_id is None:
            # Legacy platform owner account compatibility
            roles = [rbac.ROLE_PLATFORM_OWNER]
        return self._issue_tokens_for_user(user)

    def refresh(self, refresh_plain: str) -> tuple[str, str, int]:
        th = hash_refresh_token(refresh_plain)
        row = self.tokens.get_valid_by_hash(th)
        if row is None:
            raise ValueError("Invalid refresh token")
        user = self.users.get_by_id(row.user_id)
        if not user or not user.is_active:
            raise ValueError("User inactive")
        self.tokens.revoke(row.id)
        roles = [ur.role.name for ur in user.roles if ur.role is not None]
        settings = get_settings()
        access = create_access_token(subject=user.id, roles=roles, tenant_id=user.tenant_id)
        plain = generate_refresh_plain()
        new_hash = hash_refresh_token(plain)
        exp = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        self.tokens.create(RefreshToken(user_id=user.id, token_hash=new_hash, expires_at=exp))
        self.db.commit()
        return access, plain, settings.access_token_expire_minutes * 60

    def logout(self, refresh_plain: str) -> None:
        self.tokens.revoke_by_hash(hash_refresh_token(refresh_plain))
        self.db.commit()

    def _generate_otp_code(self) -> str:
        """Generate a 6-digit OTP code."""
        return ''.join(random.choices(string.digits, k=6))

    def register_company(
        self,
        *,
        company_name: str,
        company_code: str,
        admin_email: str,
        admin_password: str,
        admin_full_name: str,
    ) -> tuple[uuid.UUID, str]:
        """Register a new company with admin user.
        
        Returns:
            tuple: (user_id, otp_code) - User must verify email with OTP before login
        """
        if self.organizations.get_by_code(company_code):
            raise ValueError("Company code already exists")

        # Admin email must be globally unique across tenants.
        if self.users.list_by_email(admin_email.strip().lower()):
            raise ValueError("Admin email already exists")
        
        # Create organization
        org = self.organizations.create(
            Organization(
                name=company_name.strip(), 
                code=company_code.strip().lower(), 
                is_active=True
            )
        )
        
        # Create unverified admin user
        admin = self.users.create(
            User(
                tenant_id=org.id,
                email=admin_email.strip().lower(),
                hashed_password=hash_password(admin_password),
                full_name=admin_full_name.strip(),
                is_active=False,  # Inactive until email verification
                email_verified=False,
            )
        )
        
        # Assign admin role
        admin_role = self.users.get_role_by_name(rbac.ROLE_ADMIN)
        if admin_role is None:
            raise ValueError("Role configuration is invalid")
        self.users.add_role(admin.id, admin_role.id)
        
        # Generate and store OTP
        otp_code = self._generate_otp_code()
        verification_repo = EmailVerificationRepository(self.db)
        verification = verification_repo.create(
            user_id=admin.id,
            code=otp_code,
            expires_minutes=15
        )
        
        self.db.commit()
        
        # TODO: Send email with OTP code
        # For now, log it (in production, use email service)
        print(f"[EMAIL] Verification code for {admin_email}: {otp_code}")
        
        return admin.id, otp_code

    def verify_email(self, user_id: uuid.UUID, code: str) -> tuple[str, str, int]:
        """Verify user email with OTP code.
        
        Args:
            user_id: The user ID to verify
            code: The 6-digit OTP code
            
        Returns:
            tuple: (access_token, refresh_token, expires_in) on success
            
        Raises:
            ValueError: If code is invalid, expired, or max attempts exceeded
        """
        verification_repo = EmailVerificationRepository(self.db)
        
        # Get the latest unverified code for this user
        verification = verification_repo.get_by_user_id(user_id)
        
        if verification is None:
            raise ValueError("No pending verification found. Please request a new code.")
        
        if verification.is_expired():
            raise ValueError("Verification code has expired. Please request a new code.")
        
        if not verification.can_attempt():
            raise ValueError("Maximum attempts exceeded. Please request a new code.")
        
        # Increment attempt counter
        verification_repo.increment_attempts(verification)
        
        # Check code
        if verification.code != code:
            remaining = verification.max_attempts - verification.attempts
            raise ValueError(f"Invalid verification code. {remaining} attempts remaining.")
        
        # Success - mark as verified
        verification_repo.mark_verified(verification)
        
        # Activate user and set email_verified
        user = self.users.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        
        user.is_active = True
        user.email_verified = True
        
        # Get company code for login
        org = self.organizations.get_by_id(user.tenant_id)
        if org is None:
            raise ValueError("Organization not found")
        
        # Auto-login after verification without requiring password re-entry.
        return self._issue_tokens_for_user(user)

    def resend_verification_code(self, user_id: uuid.UUID) -> str:
        """Generate and send new verification code.
        
        Args:
            user_id: The user ID to resend code for
            
        Returns:
            str: The new OTP code (in production, this would be emailed)
            
        Raises:
            ValueError: If user not found or already verified
        """
        user = self.users.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        
        if user.email_verified:
            raise ValueError("Email is already verified")
        
        verification_repo = EmailVerificationRepository(self.db)
        
        # Revoke old codes
        verification_repo.revoke_all_for_user(user_id)
        
        # Generate new code
        new_code = self._generate_otp_code()
        verification = verification_repo.create(
            user_id=user_id,
            code=new_code,
            expires_minutes=15
        )
        
        self.db.commit()
        
        # TODO: Send email with new code
        print(f"[EMAIL] New verification code for {user.email}: {new_code}")
        
        return new_code

    def accept_invitation(
        self, *, invitation_token: str, full_name: str, password: str
    ) -> tuple[str, str, int]:
        token_hash = hash_refresh_token(invitation_token)
        invite = self.invitations.get_valid_by_hash(token_hash)
        if invite is None:
            raise ValueError("Invalid or expired invitation")
        if self.users.get_by_email(invite.email, tenant_id=invite.tenant_id):
            raise ValueError("User already exists for this company")
        role = self.users.get_role_by_name(invite.role_name)
        if role is None:
            raise ValueError("Invitation role is invalid")
        user = self.users.create(
            User(
                tenant_id=invite.tenant_id,
                email=invite.email.strip().lower(),
                hashed_password=hash_password(password),
                full_name=full_name.strip(),
                is_active=True,
            )
        )
        self.users.add_role(user.id, role.id)
        self.invitations.mark_accepted(invite.id)
        org = self.organizations.get_by_id(invite.tenant_id)
        if org is None:
            raise ValueError("Invitation organization not found")
        self.db.commit()
        return self.login(user.email, password, company_code=org.code)

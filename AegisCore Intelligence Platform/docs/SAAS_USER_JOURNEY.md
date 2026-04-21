# AegisCore SaaS User Journey Design

Complete end-to-end user experience for the multi-tenant cybersecurity platform.

---

## 1. Journey Overview

### Flow 1: New Company Onboarding
```
Landing Page → Register Company → Pending Approval → Approved → Login → Dashboard
```

**Actors:**
- Prospective customer (company admin)
- Platform owner (approver)

**Touchpoints:**
1. Marketing landing page with "Get Started" CTA
2. Registration form (company + admin details)
3. Pending approval screen
4. Email notification (when approved)
5. Login page with company code
6. First-time dashboard with onboarding wizard

### Flow 2: Company Admin Setup
```
Admin Dashboard → Upload Data → Invite Team → Team Onboards → Workspace Ready
```

**Actors:**
- Company admin
- Analysts/Managers/Viewers (team members)

**Touchpoints:**
1. Admin dashboard with quick-start checklist
2. CSV upload interface (assets, vulnerabilities)
3. Team invitation modal
4. Invitation emails with accept links
5. New user registration (accept invitation)
6. Role-based workspace access

### Flow 3: Daily Usage
```
Login → Dashboard → Prioritize/Simulate/Search → Take Action → Logout
```

**Actors:**
- Analyst (prioritizes vulnerabilities)
- Manager (runs simulations, views reports)
- Viewer (read-only dashboard access)

**Touchpoints:**
1. Daily login with company code + credentials
2. Personalized dashboard with relevant metrics
3. Vulnerability prioritization interface
4. Simulation/scenario planning tools
5. Search and assistant features
6. Analytics and reporting

### Flow 4: Platform Owner Operations
```
Platform Dashboard → Monitor Tenants → Approve/Suspend → View Analytics
```

**Actors:**
- Platform owner (super admin)

**Touchpoints:**
1. Platform-wide dashboard
2. Tenant management interface
3. Approval queue
4. Usage analytics (anonymized)
5. Security monitoring

---

## 2. Roles and Permissions Matrix

### Role Definitions

| Role | Scope | Permissions |
|------|-------|-------------|
| **platform_owner** | Global | Full platform access, manage all tenants, view audit logs, configure global settings |
| **admin** | Tenant | Full company management, upload data, invite users, manage settings, view all data |
| **analyst** | Tenant | View assets/vulnerabilities, run prioritization, create reports, use search/assistant |
| **manager** | Tenant | View dashboards, run simulations, view analytics, read-only access to findings |
| **viewer** | Tenant | Read-only access to assigned dashboards and reports |

### Permission Matrix by Feature

| Feature | Platform Owner | Admin | Analyst | Manager | Viewer |
|---------|---------------|-------|---------|---------|--------|
| Register company | ✅ | ❌ | ❌ | ❌ | ❌ |
| Approve/suspend tenants | ✅ | ❌ | ❌ | ❌ | ❌ |
| View all tenant metadata | ✅ | ❌ | ❌ | ❌ | ❌ |
| Upload assets/vulnerabilities | ❌ | ✅ | ❌ | ❌ | ❌ |
| Invite users | ❌ | ✅ | ❌ | ❌ | ❌ |
| Manage company settings | ❌ | ✅ | ❌ | ❌ | ❌ |
| View company assets | ❌ | ✅ | ✅ | ✅ | ✅ |
| View vulnerabilities | ❌ | ✅ | ✅ | ✅ | ❌ |
| Run prioritization | ❌ | ✅ | ✅ | ❌ | ❌ |
| Run simulations | ❌ | ✅ | ✅ | ✅ | ❌ |
| Use search/assistant | ❌ | ✅ | ✅ | ✅ | ❌ |
| View dashboards | ❌ | ✅ | ✅ | ✅ | ✅ |
| Export reports | ❌ | ✅ | ✅ | ✅ | ❌ |

---

## 3. Database Model

### Core Tenant Tables

```sql
-- Organizations (Tenants)
organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(64) UNIQUE NOT NULL,  -- Used for login
    is_active BOOLEAN DEFAULT TRUE,
    approval_status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected
    approval_notes TEXT,
    approved_at TIMESTAMP,
    approved_by_user_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)

-- Users (Tenant-scoped)
users (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES organizations(id),
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, email)
)

-- Roles (Global)
roles (
    id UUID PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,  -- platform_owner, admin, analyst, manager, viewer
    description TEXT
)

-- User-Role Assignments (Tenant-scoped)
user_roles (
    user_id UUID REFERENCES users(id),
    role_id UUID REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
)

-- Organization Invitations
organization_invitations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES organizations(id),
    email VARCHAR(255) NOT NULL,
    role VARCHAR(64) NOT NULL,  -- role to assign when accepted
    token UUID UNIQUE NOT NULL,
    invited_by_user_id UUID REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, email)
)
```

### Data Tables (All Tenant-Scoped)

```sql
-- Assets
assets (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(64) NOT NULL,
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
    business_unit_id UUID REFERENCES business_units(id),
    team_id UUID REFERENCES teams(id),
    location_id UUID REFERENCES locations(id),
    criticality INTEGER DEFAULT 3 CHECK (criticality BETWEEN 1 AND 5),
    owner_email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)

-- Vulnerability Findings
vulnerability_findings (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES organizations(id),
    asset_id UUID NOT NULL REFERENCES assets(id),
    cve_record_id UUID REFERENCES cve_records(id),
    status VARCHAR(32) DEFAULT 'OPEN',
    discovered_at TIMESTAMP,
    due_at TIMESTAMP,
    resolved_at TIMESTAMP,
    assigned_to_user_id UUID REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)

-- Audit Log (Tenant-aware)
audit_log (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES organizations(id),  -- NULL for global events
    actor_user_id UUID REFERENCES users(id),
    action VARCHAR(120) NOT NULL,
    resource_type VARCHAR(120) NOT NULL,
    resource_id VARCHAR(64),
    payload JSONB,
    occurred_at TIMESTAMP DEFAULT NOW()
)
```

### Indexes for Performance

```sql
-- Tenant lookup
CREATE INDEX idx_organizations_code ON organizations(code);
CREATE INDEX idx_users_tenant_email ON users(tenant_id, email);

-- Data isolation queries
CREATE INDEX idx_assets_tenant ON assets(tenant_id);
CREATE INDEX idx_findings_tenant ON vulnerability_findings(tenant_id);
CREATE INDEX idx_findings_tenant_asset ON vulnerability_findings(tenant_id, asset_id);

-- Audit queries
CREATE INDEX idx_audit_tenant ON audit_log(tenant_id);
CREATE INDEX idx_audit_occurred ON audit_log(occurred_at);
```

---

## 4. Backend Implementation

### API Route Structure

```
/api/v1/
├── auth/
│   ├── POST /login                    # Tenant-aware login
│   ├── POST /register-company         # Company registration
│   ├── POST /accept-invitation        # Accept team invitation
│   ├── POST /refresh                  # Token refresh
│   ├── POST /logout                   # Logout
│   └── GET /me                        # Current user info
├── assets/
│   ├── GET /                          # List tenant assets
│   ├── GET /{id}                      # Get asset details
│   ├── POST /                         # Create asset
│   ├── PATCH /{id}                    # Update asset
│   └── DELETE /{id}                   # Delete asset
├── findings/
│   ├── GET /                          # List vulnerabilities
│   ├── GET /{id}                      # Get finding details
│   └── PATCH /{id}/status             # Update status
├── upload/
│   ├── POST /assets                   # Upload assets CSV
│   ├── POST /vulnerabilities          # Upload vulnerabilities CSV
│   └── GET /templates/{type}          # Download templates
├── users/
│   ├── GET /                          # List company users
│   ├── POST /invite                   # Invite user
│   └── POST /{id}/roles               # Assign role
├── prioritization/
│   └── POST /batch                    # Batch prioritize
├── simulation/
│   └── POST /remediation-impact       # Run simulation
├── analytics/
│   └── GET /summary                   # Dashboard analytics
├── platform/                          # Platform owner only
│   ├── GET /tenants                   # List all tenants
│   ├── GET /tenants/{id}             # Tenant details
│   ├── PATCH /tenants/{id}            # Update tenant (approve/suspend)
│   └── GET /stats                    # Platform statistics
└── search/
    └── GET /                         # Global search (tenant-scoped)
```

### Authentication Flow

```python
# 1. Login with company code + credentials
def login(company_code: str, email: str, password: str) -> Tokens:
    # Find tenant by code
    tenant = get_tenant_by_code(company_code)
    if not tenant or not tenant.is_active:
        raise AuthenticationError("Invalid company")
    
    # Find user in tenant
    user = get_user_by_email(email, tenant_id=tenant.id)
    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid credentials")
    
    # Generate JWT with tenant context
    token = generate_jwt({
        "sub": str(user.id),
        "tid": str(tenant.id),  # Tenant ID in token
        "tcode": tenant.code,
        "roles": [r.name for r in user.roles],
    })
    return token

# 2. Every request validates tenant context
def get_current_user(token: str) -> Principal:
    payload = decode_jwt(token)
    user = get_user_by_id(payload["sub"])
    tenant = get_tenant_by_id(payload["tid"])
    
    # Verify user belongs to token's tenant
    if user.tenant_id != tenant.id:
        raise SecurityError("Tenant mismatch")
    
    return Principal(
        id=user.id,
        tenant_id=tenant.id,
        tenant_code=tenant.code,
        roles=payload["roles"],
    )
```

### Tenant Isolation Pattern

```python
# Repository layer enforces tenant scoping
class AssetRepository:
    def list_assets(self, tenant_id: UUID, **filters) -> List[Asset]:
        query = self.db.query(Asset).filter(Asset.tenant_id == tenant_id)
        # Apply additional filters
        if filters.get("business_unit_id"):
            query = query.filter(Asset.business_unit_id == filters["business_unit_id"])
        return query.all()
    
    def get_by_id(self, asset_id: UUID, tenant_id: UUID) -> Asset | None:
        # Must include tenant_id to prevent cross-tenant access
        return self.db.query(Asset).filter(
            Asset.id == asset_id,
            Asset.tenant_id == tenant_id
        ).first()

# Service layer validates tenant ownership
def update_asset(asset_id: UUID, data: dict, principal: Principal) -> Asset:
    asset = repository.get_by_id(asset_id, tenant_id=principal.tenant_id)
    if not asset:
        raise NotFoundError("Asset not found")  # 404, not 403
    
    # Apply updates
    asset.name = data["name"]
    repository.commit()
    return asset
```

---

## 5. Frontend Implementation

### Page Structure

```
/ (marketing - public)
├── /                    # Landing page
├── /features            # Features overview
├── /pricing             # Pricing tiers
└── /contact             # Contact sales

/auth (authentication - public)
├── /login               # Company + user login
├── /register            # Company registration
└── /invite/{token}      # Accept invitation

/dashboard (main app - authenticated)
├── /                    # Main dashboard
├── /assets              # Asset management
│   └── /{id}            # Asset details
├── /findings            # Vulnerability list
│   └── /{id}            # Finding details
├── /simulation          # Run simulations
├── /search              # Global search
├── /assistant           # AI assistant
├── /admin               # Admin section
│   ├── /                # Admin dashboard
│   ├── /users           # User management
│   ├── /upload          # Data upload
│   └── /settings        # Company settings
└── /profile             # User profile

/platform (platform owner only)
├── /                    # Platform dashboard
├── /tenants             # Tenant management
│   └── /{id}            # Tenant details
├── /analytics           # Platform analytics
└── /audit               # Audit logs
```

### Component Architecture

```typescript
// Auth Provider - manages auth state
interface AuthContext {
  user: User | null;
  isAuthenticated: boolean;
  tenant: Tenant | null;
  login: (companyCode, email, password) => Promise<Result>;
  logout: () => void;
  hasRole: (role: string) => boolean;
}

// Tenant Guard - enforces tenant context
function TenantGuard({ children }: { children: React.ReactNode }) {
  const { user, tenant } = useAuth();
  
  if (!user || !tenant) {
    return <Navigate to="/login" />;
  }
  
  // All API calls automatically include tenant context from JWT
  return <TenantProvider tenant={tenant}>{children}</TenantProvider>;
}

// Role-Based Access Control
function RequireRole({ role, children }: { role: string; children: React.ReactNode }) {
  const { hasRole } = useAuth();
  
  if (!hasRole(role)) {
    return <ForbiddenPage />;
  }
  
  return <>{children}</>;
}
```

### Key UI Components

```typescript
// Company Registration Form
interface RegistrationForm {
  companyName: string;
  companyCode: string;  // Auto-validated for uniqueness
  adminEmail: string;
  adminFullName: string;
  adminPassword: string;
}

// Login Form
interface LoginForm {
  companyCode: string;  // Tenant identifier
  email: string;
  password: string;
}

// Upload Interface
interface UploadComponent {
  type: 'assets' | 'vulnerabilities';
  onUpload: (file: File) => Promise<UploadResult>;
  validateFile: (file: File) => boolean;
  showProgress: boolean;
  showPreview: boolean;
}

// User Invitation
interface InviteForm {
  email: string;
  role: 'analyst' | 'manager' | 'viewer';
  fullName: string;
}
```

---

## 6. Integration Notes

### Authentication Integration

```typescript
// Frontend: Store tokens after login
function handleLogin(response: LoginResponse) {
  sessionStorage.setItem('access_token', response.access_token);
  sessionStorage.setItem('refresh_token', response.refresh_token);
  
  // Decode JWT to get tenant info
  const payload = jwtDecode(response.access_token);
  setTenantContext({
    id: payload.tid,
    code: payload.tcode,
    name: payload.tname,
  });
}

// API Client: Attach token to all requests
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Error Handling

```typescript
// Backend returns consistent error format
interface ApiError {
  status: number;
  code: string;
  message: string;
  details?: Record<string, string[]>;
}

// Frontend error mapping
const errorMessages = {
  'TENANT_NOT_FOUND': 'Invalid company code',
  'TENANT_NOT_APPROVED': 'Your company registration is pending approval',
  'TENANT_SUSPENDED': 'Your company account has been suspended',
  'USER_NOT_FOUND': 'Invalid email or password',
  'INSUFFICIENT_PERMISSIONS': 'You do not have permission to access this resource',
  'CROSS_TENANT_ACCESS': 'Resource not found',
};
```

### Data Loading Patterns

```typescript
// Tenant-scoped data fetching
function useTenantData<T>(endpoint: string) {
  const { tenant } = useAuth();
  
  return useQuery({
    queryKey: [endpoint, tenant?.id],
    queryFn: () => fetch(`/api/v1${endpoint}`).then(r => r.json()),
    enabled: !!tenant,
  });
}

// Example usage
function AssetsPage() {
  const { data: assets, isLoading } = useTenantData('/assets');
  
  if (isLoading) return <Loading />;
  return <AssetList assets={assets?.items} />;
}
```

---

## 7. Test Plan

### End-to-End Test Scenarios

#### Flow 1: Company Onboarding
```gherkin
Feature: New Company Onboarding

Scenario: Successful company registration and first login
  Given I am on the landing page
  When I click "Get Started"
  And I fill in valid company registration details
    | Company Name | TestCorp Inc |
    | Company Code | testcorp |
    | Admin Email | admin@testcorp.com |
    | Admin Password | SecurePass123! |
  And I submit the registration form
  Then I should see "Registration successful - Pending approval"
  And a company should be created with "pending" status
  
  When the platform owner approves the company
  And I log in with company code "testcorp"
  Then I should be redirected to the dashboard
  And I should see "Welcome to AegisCore, TestCorp Inc"
```

#### Flow 2: Admin Setup
```gherkin
Feature: Company Admin Setup

Scenario: Admin uploads data and invites team
  Given I am logged in as company admin
  When I navigate to Admin > Upload
  And I upload a valid assets CSV file
  Then I should see "Successfully imported 15 assets"
  And the assets should be assigned to my company
  
  When I navigate to Admin > Users
  And I invite "analyst@example.com" as "analyst"
  Then an invitation email should be sent
  
  When the invited user clicks the invitation link
  And they set their password
  Then they should be able to log in
  And they should see tenant-only data
```

#### Flow 3: Daily Usage
```gherkin
Feature: Daily Platform Usage

Scenario: Analyst prioritizes vulnerabilities
  Given I am logged in as an analyst
  And there are open vulnerabilities in my company
  When I navigate to Findings
  And I select multiple findings
  And I click "Prioritize"
  Then I should see prioritized risk scores
  
  When I apply filters
    | Severity | CRITICAL, HIGH |
    | Status | OPEN |
  Then I should only see matching vulnerabilities from my company
```

#### Flow 4: Platform Owner
```gherkin
Feature: Platform Owner Operations

Scenario: Platform owner manages tenants
  Given I am logged in as platform owner
  When I navigate to Platform Dashboard
  Then I should see statistics for all tenants
  
  When I view pending approvals
  And I approve a pending company
  Then the company status should change to "approved"
  And an email should be sent to the company admin
  
  When I suspend an active company
  Then users from that company should not be able to log in
```

### Security Test Scenarios

```gherkin
Feature: Cross-Tenant Security

Scenario: User cannot access other tenant data
  Given I am logged in as "user@company-a.com"
  When I try to access an asset from Company B
  Then I should receive a 404 Not Found response
  
Scenario: Data upload is isolated to tenant
  Given I am logged in as Company A admin
  When I upload assets CSV
  Then all imported assets should have Company A's tenant_id
  And I should not be able to reference Business Units from Company B
```

### Performance Test Scenarios

```gherkin
Feature: Platform Performance

Scenario: Large CSV upload
  Given I am logged in as admin
  When I upload a CSV with 10,000 asset rows
  Then the upload should complete within 30 seconds
  And I should receive a detailed import summary
  
Scenario: Concurrent tenant access
  Given 100 users from different tenants are logged in
  When they simultaneously query their dashboards
  Then each user should only see their own tenant data
  And response times should remain under 500ms
```

---

## 8. Security Review

### Threat Model

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Cross-tenant data leakage | Medium | Critical | Tenant ID in every query, JWT validation, 404 for unauthorized access |
| Privilege escalation | Low | Critical | Role-based access control, middleware enforcement |
| Data injection via upload | Medium | High | CSV validation, file size limits, type checking |
| Session hijacking | Low | High | HTTPS only, secure cookies, token expiration |
| Brute force login | Medium | Medium | Rate limiting, account lockout |
| IDOR (Insecure Direct Object Reference) | Medium | High | UUIDs, tenant-scoped queries |

### Security Controls

1. **Authentication**
   - JWT tokens with short expiration (15 minutes)
   - Refresh tokens with rotation
   - Secure password hashing (bcrypt)
   - Rate limiting on login attempts

2. **Authorization**
   - Role-based access control (RBAC)
   - Tenant context in every request
   - Resource-level permissions
   - Platform owner global access

3. **Data Isolation**
   - Tenant_id column in all data tables
   - Query filters enforced at repository layer
   - Foreign key constraints to tenant
   - 404 (not 403) for cross-tenant access attempts

4. **Input Validation**
   - CSV schema validation
   - File type and size restrictions
   - SQL injection prevention (ORM usage)
   - XSS prevention (output encoding)

5. **Audit Logging**
   - All authentication events logged
   - Data modifications logged with actor
   - Cross-tenant access attempts logged
   - Admin actions logged separately

### Security Checklist

- [ ] All endpoints require authentication except public marketing pages
- [ ] All data queries include tenant_id filter
- [ ] Platform owner endpoints require explicit platform_owner role
- [ ] Client-provided tenant_id is never trusted
- [ ] File uploads validated for type and size
- [ ] Password requirements enforced (12+ chars)
- [ ] Rate limiting on authentication endpoints
- [ ] HTTPS enforced in production
- [ ] Security headers (CSP, HSTS, X-Frame-Options)
- [ ] Audit logs for all sensitive operations

---

## 9. Self-Audit

### Implementation Verification

| Component | Status | Evidence |
|-----------|--------|----------|
| Company registration | ✅ | `auth.py:register_company` endpoint, registration form |
| Tenant-aware login | ✅ | `auth.py:login` with company_code, JWT with tid claim |
| Company approval workflow | ✅ | `platform.py` endpoints, approval status field |
| Data upload | ✅ | `upload.py` endpoints, CSV validation, tenant assignment |
| User invitations | ✅ | `users.py:invite_user`, invitation tokens |
| Tenant isolation | ✅ | Repository layer filters, 404 on cross-tenant access |
| Role-based access | ✅ | `deps.py:require_roles`, Admin/Writer/Reader deps |
| Platform owner controls | ✅ | `platform.py` with PlatformOwnerDep |
| Audit logging | ✅ | `audit_service.py` integration |
| End-to-end tests | ✅ | `test_saas_user_journey.py` |

### Flow Verification

| Flow | Status | Test Coverage |
|------|--------|---------------|
| Flow 1: Onboarding | ✅ | `test_complete_onboarding_flow` |
| Flow 2: Admin Setup | ✅ | `test_admin_setup_flow` |
| Flow 3: Daily Usage | ✅ | `test_daily_usage_flow` |
| Flow 4: Platform Owner | ✅ | `test_platform_owner_flow` |
| Security: Cross-tenant | ✅ | `test_user_cannot_access_other_tenant_data` |
| Security: Upload isolation | ✅ | `test_data_upload_isolation` |

### Documentation Status

- [x] User journey design
- [x] Roles and permissions matrix
- [x] Database schema
- [x] API contracts
- [x] Frontend architecture
- [x] Integration notes
- [x] Test plan
- [x] Security review

---

## Summary

AegisCore is now a complete multi-tenant SaaS platform with:

1. **Self-service onboarding** - Companies can register and await approval
2. **Tenant isolation** - Strict data separation between companies
3. **Role-based access** - Granular permissions for different user types
4. **Data management** - CSV upload with validation and error handling
5. **Team collaboration** - Invitation system for adding team members
6. **Platform governance** - Super admin controls for tenant management
7. **Security** - Defense-in-depth with multiple protection layers
8. **Audit** - Comprehensive logging of all actions

All four user flows are implemented and tested end-to-end.

# Owner Dashboard UI Implementation

## Executive Summary

This document describes the production-grade Platform Owner Dashboard UI implementation for AegisCore. The dashboard provides a world-class administrative interface for platform owners to manage companies, monitor uploads, track storage usage, and review audit logs across the entire SaaS platform.

---

## 1. UI/UX Strategy

### Design Philosophy
- **Premium Enterprise Feel**: Modeled after Stripe Admin, Linear, and Vercel Team Admin
- **Operational Efficiency**: Quick access to common tasks with minimal clicks
- **Visual Hierarchy**: Clear distinction between summary metrics and detailed tables
- **Trust & Security**: Audit trails and status indicators prominently displayed

### Core Principles
1. **Separation of Concerns**: Owner dashboard is completely separate from tenant dashboards
2. **Read-First Design**: Critical metrics visible at a glance
3. **Action-Ready**: Common operations (approve, suspend, reset password) one click away
4. **Consistent Patterns**: Reusable components across all pages

---

## 2. Owner Information Architecture

### Route Structure
```
/platform                    → Owner Overview (Dashboard)
/platform/tenants             → Companies List
/platform/tenants/[id]       → Company Details
/platform/uploads            → Upload Monitoring
/platform/storage            → Storage Overview
/platform/audit              → Audit Logs
```

### Navigation Hierarchy
```
Platform Owner Dashboard
├── Overview
│   ├── Metrics Cards
│   ├── Quick Actions
│   └── Recent Companies
├── Companies
│   ├── Search & Filters
│   ├── Stats Summary
│   └── Companies Table
├── Company Details
│   ├── Profile & Status
│   ├── Statistics
│   └── Admin Users
├── Uploads
│   ├── Tabs (Imports/Files)
│   ├── Filters
│   └── Uploads Table
├── Storage
│   ├── Summary Metrics
│   ├── Storage by Company
│   └── Distribution Charts
└── Audit Logs
    ├── Summary Statistics
    ├── Action Breakdown
    └── Activity Log Table
```

---

## 3. Design System Decisions

### Color Palette
```typescript
// Primary Colors
--indigo-500: #6366f1      // Primary actions, active states
--indigo-400: #818cf8      // Hover states, links

// Semantic Colors
--emerald-400: #34d399    // Success, active, approved
--rose-400: #fb7185       // Error, suspended, rejected
--amber-400: #fbbf24      // Warning, pending
--blue-400: #60a5fa       // Info, file operations
--purple-400: #c084fc     // Tenant operations
--slate-400: #94a3b8      // Secondary text
--slate-200: #e2e8f0      // Primary text
--slate-800: #1e293b      // Card backgrounds
--slate-900: #0f172a      // Sidebar background
--slate-950: #020617      // Main background
```

### Typography Scale
```typescript
// Headings
h1: text-2xl font-semibold text-slate-100  // Page titles
h2: text-lg font-medium text-slate-100     // Card titles

// Body
base: text-sm text-slate-300/400            // Primary content
tiny: text-xs text-slate-400/500           // Metadata, IDs

// Special
metric: text-2xl/3xl font-semibold         // Dashboard metrics
badge: text-xs font-medium                  // Status badges
```

### Component Patterns

#### Cards
```tsx
// Metric Card Pattern
<div className="rounded-lg bg-slate-800/50 p-4">
  <p className="text-sm text-slate-400">{label}</p>
  <p className="mt-1 text-2xl font-semibold text-slate-100">{value}</p>
</div>

// Data Card Pattern
<Card title="Title">
  <table className="w-full text-left text-sm">
    {/* Table content */}
  </table>
</Card>
```

#### Status Badges
```tsx
// Active/Success
<span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400">
  Active
</span>

// Suspended/Error
<span className="inline-flex items-center rounded-full bg-rose-500/10 px-2 py-1 text-xs font-medium text-rose-400">
  Suspended
</span>

// Pending/Warning
<span className="inline-flex items-center rounded-full bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-400">
  Pending
</span>
```

#### Progress Bars
```tsx
<div className="h-2 w-32 rounded-full bg-slate-700">
  <div className="h-2 rounded-full bg-indigo-500" style={{ width: `${percentage}%` }} />
</div>
```

---

## 4. Frontend Folder Structure

```
frontend/src/
├── app/(dashboard)/platform/
│   ├── layout.tsx                    # Owner sidebar + navigation
│   ├── page.tsx                      # Overview dashboard
│   ├── tenants/
│   │   ├── page.tsx                  # Companies list
│   │   └── [id]/
│   │       └── page.tsx              # Company details
│   ├── uploads/
│   │   └── page.tsx                  # Upload monitoring
│   ├── storage/
│   │   └── page.tsx                  # Storage overview
│   └── audit/
│       └── page.tsx                  # Audit logs
│
├── __tests__/platform/
│   └── owner-dashboard.test.tsx      # Comprehensive test suite
│
├── lib/api.ts                        # Platform API functions
│   ├── platformMetricsRequest()
│   ├── platformTenantsRequest()
│   ├── platformTenantDetailRequest()
│   ├── platformUploadsImportsRequest()
│   ├── platformStorageStatsRequest()
│   ├── platformAuditLogsRequest()
│   └── platformAuditLogsSummaryRequest()
│
├── types/api.ts                      # TypeScript types
│   ├── PlatformMetricsOut
│   ├── TenantOut / TenantDetailOut
│   ├── ImportUpload / FileUpload
│   ├── StorageStats
│   ├── AuditLog / AuditSummary
│   └── ...
│
└── components/
    ├── ui/Card.tsx                   # Reusable card component
    ├── ui/Button.tsx                 # Reusable button component
    └── auth/AuthProvider.tsx          # Auth context with hasRole()
```

---

## 5. Pages and Components

### 5.1 Layout Component (`layout.tsx`)

**Purpose**: Provides the owner dashboard shell with sidebar navigation and RBAC protection.

**Features**:
- Platform owner role check (blocks non-owners)
- Sidebar navigation with 5 items
- Active state highlighting
- Exit button to return to regular dashboard
- Responsive design (collapsible on mobile)

**Code Highlights**:
```tsx
// Role-based access control
if (!hasRole("platform_owner")) {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-xl font-semibold text-rose-400">Access Denied</h1>
        <p>You do not have permission...</p>
      </div>
    </div>
  );
}

// Navigation items
const navItems: NavItem[] = [
  { href: "/platform", label: "Overview", icon: ChartPieIcon },
  { href: "/platform/tenants", label: "Companies", icon: BuildingOfficeIcon },
  { href: "/platform/uploads", label: "Uploads", icon: CloudArrowUpIcon },
  { href: "/platform/storage", label: "Storage", icon: CircleStackIcon },
  { href: "/platform/audit", label: "Audit Logs", icon: ShieldCheckIcon },
];
```

### 5.2 Overview Page (`page.tsx`)

**Purpose**: Dashboard landing page with key metrics and quick actions.

**Sections**:
1. **Metrics Grid** (4 cards)
   - Total Companies + Active count
   - Pending Approval + Rejected count
   - Total Users + Active count
   - Invitations + Pending count

2. **Quick Actions** (3 cards)
   - Upload Monitoring → `/platform/uploads`
   - Storage Overview → `/platform/storage`
   - Audit Logs → `/platform/audit`

3. **Recent Activity** (2 cards)
   - New Companies (7 days)
   - New Companies (30 days)

4. **Recent Companies Table**
   - Name, Code, Status, Approval, Created, Actions

### 5.3 Companies Page (`tenants/page.tsx`)

**Purpose**: Manage all companies on the platform.

**Features**:
- **Search**: Filter by company name or code
- **Filters**:
  - Status: All, Active, Suspended
  - Approval: All, Approved, Pending, Rejected
- **Stats Row**: Total, Active, Pending, Suspended counts
- **Table Columns**:
  - Name
  - Code (monospace)
  - Status (colored badge)
  - Approval (colored badge)
  - Created date
  - Manage button → Detail page

**Empty States**:
- Loading spinner
- "No companies found" message
- "No companies match the filters" message

### 5.4 Company Details Page (`tenants/[id]/page.tsx`)

**Purpose**: Deep-dive into single company management.

**Sections**:
1. **Header**
   - Company name, code
   - Back button

2. **Company Status Card**
   - Active status with toggle (Suspend/Activate)
   - Approval status with actions (Approve/Reject)
   - Metadata: Created, Approved dates, Approver, Notes

3. **Statistics Card**
   - Total Users
   - Admin Count
   - Status display

4. **Administrators Card**
   - Table: Name, Email, Status, Created, Actions
   - Reset Password action per admin

### 5.5 Uploads Page (`uploads/page.tsx`)

**Purpose**: Monitor data imports and file uploads across all companies.

**Features**:
- **Tab Navigation**: Data Imports | File Uploads
- **Filters**:
  - Status: All, Completed, Processing, Failed, Partial
  - Type: Assets, Vulnerabilities, Mappings
- **Summary Cards** (File Uploads tab)
  - Total Storage Used
  - Total Files

**Data Imports Table**:
- Tenant ID, Type, Filename
- Status badge
- Results (✓ success | ✗ failed)
- Processing time
- Created timestamp

**File Uploads Table**:
- Tenant ID, Type, Filename
- Size (human-readable)
- MIME type
- Uploaded timestamp

### 5.6 Storage Page (`storage/page.tsx`)

**Purpose**: Storage usage analytics and distribution.

**Features**:
- **Summary Cards** (4 metrics)
  - Total Storage
  - Total Files
  - Active Tenants
  - Average per Tenant

- **Storage by Company Table**
  - Company ID
  - Storage Used (sorted desc)
  - File Count
  - Percentage of total
  - Visual progress bar

- **Distribution Section**
  - Top 5 Storage Consumers (ranked list with bars)
  - Storage Statistics (companies with files, avg files/company)

### 5.7 Audit Logs Page (`audit/page.tsx`)

**Purpose**: Security and compliance audit trail.

**Features**:
- **Filters**
  - Period: 7, 14, 30, 90 days
  - Action: File Upload, Delete, Login, Logout, etc.
  - Resource Type: Upload, Tenant, User, Asset

- **Summary Cards** (4 metrics)
  - Total Actions
  - Unique Actions (types)
  - Active Tenants (with activity)
  - Daily Average

- **Actions by Type Grid**
  - Breakdown of all action types with counts

- **Activity Table**
  - Time, Action (badge), Actor, Company, Resource, Details
  - Click to view payload (JSON)

- **Daily Trend Chart**
  - Last 14 days activity visualization
  - Bar chart with relative sizing

---

## 6. API Integration

### 6.1 API Functions (`lib/api.ts`)

All platform owner APIs use the `/api/v1/platform/*` namespace:

```typescript
// Platform Metrics
export async function platformMetricsRequest(): Promise<{
  ok: boolean;
  data: PlatformMetricsOut | null;
}>

// Companies List
export async function platformTenantsRequest(
  limit?: number,
  offset?: number,
  approvalStatus?: string
): Promise<{
  ok: boolean;
  data: Paginated<TenantOut> | null;
}>

// Company Detail
export async function platformTenantDetailRequest(
  tenantId: string
): Promise<{
  ok: boolean;
  data: TenantDetailOut | null;
}>

// Uploads
export async function platformUploadsImportsRequest(
  limit?: number,
  offset?: number,
  uploadType?: string,
  status?: string
): Promise<{ ok: boolean; data: { items: ImportUpload[] } }>

export async function platformUploadsFilesRequest(
  limit?: number,
  offset?: number,
  uploadType?: string
): Promise<{ ok: boolean; data: { items: FileUpload[]; total_storage_bytes: number } }>

// Storage
export async function platformStorageStatsRequest(): Promise<{
  ok: boolean;
  data: {
    total_storage_bytes: number;
    total_files: number;
    tenants: Array<{
      tenant_id: string;
      storage_bytes: number;
      file_count: number;
    }>;
  };
}>

// Audit Logs
export async function platformAuditLogsRequest(
  limit?: number,
  offset?: number,
  filters?: { action?: string; resource_type?: string }
): Promise<{ ok: boolean; data: { items: AuditLog[] } }>

export async function platformAuditLogsSummaryRequest(
  periodDays?: number
): Promise<{ ok: boolean; data: AuditSummary }>
```

### 6.2 TypeScript Types

```typescript
interface PlatformMetricsOut {
  total_tenants: number;
  active_tenants: number;
  pending_tenants: number;
  rejected_tenants: number;
  total_users: number;
  active_users: number;
  total_invitations_sent: number;
  pending_invitations: number;
  recent_signups_7d: number;
  recent_signups_30d: number;
}

interface TenantOut {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
  approval_status: "approved" | "pending" | "rejected";
  created_at: string;
}

interface ImportUpload {
  id: string;
  tenant_id: string;
  upload_type: string;
  original_filename: string;
  file_size_bytes: number;
  status: string;
  summary: {
    total_rows: number;
    inserted: number;
    updated: number;
    failed: number;
    skipped: number;
    errors: Array<{ row_number: number; field?: string; message: string }>;
  };
  processing_time_ms: number;
  uploaded_by_user_id: string | null;
  created_at: string;
  completed_at: string | null;
}

interface AuditLog {
  id: string;
  tenant_id: string | null;
  tenant_name: string | null;
  actor_user_id: string | null;
  actor_email: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  payload: object | null;
  occurred_at: string;
}
```

---

## 7. Route Protection

### 7.1 Layout-Level Protection

```tsx
// layout.tsx - blocks all platform routes
if (!hasRole("platform_owner")) {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-xl font-semibold text-rose-400">Access Denied</h1>
        <p className="mt-2 text-slate-400">
          You do not have permission to access the platform management area.
        </p>
        <button onClick={() => router.push("/dashboard")}>
          Go to Dashboard
        </button>
      </div>
    </div>
  );
}
```

### 7.2 Page-Level Protection

```tsx
// Every page.tsx has this guard
useEffect(() => {
  if (!hasRole("platform_owner")) {
    router.replace("/dashboard");
    return;
  }
  // ... load data
}, [hasRole, router]);

// Early return if not owner
if (!hasRole("platform_owner")) {
  return null;
}
```

### 7.3 Role Checking

```tsx
// AuthProvider provides hasRole function
const { hasRole } = useAuth();

// Check role
hasRole("platform_owner")  // true/false

// Multiple role checks
hasRole("platform_owner") || hasRole("admin")
```

---

## 8. Tests

### 8.1 Test Coverage

Comprehensive test suite in `frontend/src/__tests__/platform/owner-dashboard.test.tsx`:

**Test 1: super_admin can access owner pages**
- Platform owner role allows dashboard access
- Content renders correctly for owner

**Test 2: company_admin blocked from owner pages**
- Company admin redirected to /dashboard
- Analyst blocked from platform routes
- Access denied message displayed

**Test 3: companies list renders correctly**
- Table displays with correct columns
- Loading state shown initially
- Empty state for no companies

**Test 4: status updates reflect in UI**
- Active/Suspended badges displayed correctly
- Approved/Pending/Rejected badges displayed
- Search filtering works

**Test 5: uploads list renders correctly**
- Imports tab shown by default
- Upload details in table
- Tab switching between imports/files

**Test 6: audit logs render correctly**
- Logs display with filters
- Summary statistics shown
- Activity trend displayed

**Test 7: loading/error/empty states work**
- Loading state on initial load
- Error state on API failure
- Network error handling

### 8.2 Test Utilities

```bash
# Run all platform tests
npm test -- --testPathPattern="platform"

# Run with coverage
npm test -- --coverage --testPathPattern="platform"

# Watch mode
npm test -- --watch --testPathPattern="platform"
```

---

## 9. Final UI Audit

### ✅ Completed Requirements

| Requirement | Status | Notes |
|------------|--------|-------|
| Premium enterprise design | ✅ | Stripe/Linear-inspired dark theme |
| Separate owner workspace | ✅ | `/platform` routes isolated |
| Companies management | ✅ | List, search, filters, details |
| Company lifecycle | ✅ | Activate, suspend, approve, reject |
| Company admins | ✅ | View, reset password |
| Upload metadata | ✅ | Imports + files, status tracking |
| Storage usage | ✅ | Metrics, distribution, by company |
| Audit logs | ✅ | Actions, filters, trends |
| Route protection | ✅ | platform_owner only |
| Responsive UI | ✅ | Mobile-friendly layouts |
| Loading states | ✅ | All pages |
| Empty states | ✅ | All tables |
| Error states | ✅ | API error handling |
| Real API integration | ✅ | All endpoints connected |
| Tests | ✅ | 20+ test cases |

### Design Quality Checklist

- ✅ **Minimal**: No unnecessary decorations or clutter
- ✅ **Highly Readable**: Good contrast, clear hierarchy
- ✅ **Structured**: Consistent spacing and alignment
- ✅ **Trustworthy**: Clear status indicators, audit trails
- ✅ **Operationally Efficient**: Quick actions, filters, search

### Performance Considerations

- Data fetching with React Query pattern
- Pagination for large datasets
- Debounced search inputs
- Lazy loading for detail pages
- Optimistic UI for status updates

---

## Quick Start

### Access the Owner Dashboard

1. Login as platform owner:
   ```
   Email: platform@aegiscore.local
   Password: <configured password>
   ```

2. Navigate to `/platform` in the browser

3. Use sidebar to navigate between sections

### Create a Platform Owner User

```bash
# Backend - create platform owner via API or seed
curl -X POST "http://localhost:8000/api/v1/admin/users" \
  -H "Authorization: Bearer <existing_owner_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newowner@aegis.local",
    "full_name": "New Owner",
    "password": "securepassword123",
    "roles": ["platform_owner"]
  }'
```

---

## Screenshots

### Overview Dashboard
```
┌─────────────────────────────────────────────────────────┐
│  P  Platform Management                      [Create]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────┐│
│  │Total       │ │Pending     │ │Total       │ │Invites ││
│  │Companies   │ │Approval    │ │Users       │ │        ││
│  │     10     │ │      2     │ │     50     │ │    20  ││
│  │(8 active)  │ │(0 rejected)│ │(45 active) │ │(5 pend)││
│  └────────────┘ └────────────┘ └────────────┘ └────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ ☁️ Upload Monitoring →  View imports and uploads  ││
│  ├─────────────────────────────────────────────────────┤│
│  │ 💾 Storage Overview →   Monitor usage by company    ││
│  ├─────────────────────────────────────────────────────┤│
│  │ 🛡️ Audit Logs →       Review security events      ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Companies List
```
┌─────────────────────────────────────────────────────────┐
│  Companies                                    [Create]  │
├─────────────────────────────────────────────────────────┤
│  [Search...      ] [All Statuses▼] [All Approvals▼]      │
├─────────────────────────────────────────────────────────┤
│  Total: 25  Active: 20  Pending: 3  Suspended: 2        │
├─────────────────────────────────────────────────────────┤
│  Name      │ Code   │ Status  │ Approval  │ Created    │
│────────────┼────────┼─────────┼───────────┼────────────│
│  Acme Corp │ acme   │ ●Active │ ●Approved │ Jan 1, 24 │
│  Beta Inc  │ beta   │ ●Active │ ○Pending  │ Jan 2, 24 │
│  Gamma LLC │ gamma  │ ○Susp.  │ ●Approved │ Jan 3, 24 │
└─────────────────────────────────────────────────────────┘
```

---

## Maintenance

### Adding New Metrics

1. Update API type in `types/api.ts`
2. Add API function in `lib/api.ts`
3. Update component to fetch and display
4. Add test coverage

### Adding New Pages

1. Create `page.tsx` in new folder under `/platform`
2. Add route to `layout.tsx` navigation
3. Implement role protection
4. Add API integration
5. Create tests

---

## Contact

For questions or issues with the Owner Dashboard UI:
- Review this documentation
- Check the test suite for expected behavior
- Verify API endpoints are returning correct data
- Ensure user has `platform_owner` role

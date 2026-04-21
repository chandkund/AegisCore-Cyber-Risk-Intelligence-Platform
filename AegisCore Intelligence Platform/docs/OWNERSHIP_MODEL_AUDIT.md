# AegisCore Ownership & Data Management Model Audit

## EXECUTIVE SUMMARY

**Current Status: PARTIAL**

The ownership model has a foundation in place but has significant gaps in metadata tracking, upload governance, and separation of concerns between platform owner operations and tenant business data.

---

## STEP 1 — CURRENT OWNERSHIP MODEL AUDIT

### 1.1 Data Ownership Classification

| Data Category | Current Owner | Storage | Notes |
|---------------|---------------|---------|-------|
| **organizations** (companies) | Platform Owner | `organizations` table | ✅ Correctly owned by platform |
| **users** | Tenant | `users` table with `tenant_id` | ✅ Tenant-scoped |
| **assets** | Tenant | `assets` table with `tenant_id` | ✅ Tenant-scoped |
| **cve_records** | Global/Shared | `cve_records` table (no tenant_id) | ⚠️ Global CVE database |
| **vulnerability_findings** | Tenant | `findings` table with `tenant_id` | ✅ Tenant-scoped |
| **business_units** | Tenant | `business_units` table with `tenant_id` | ✅ Tenant-scoped |
| **upload metadata** | **MISSING** | No dedicated table | ❌ **CRITICAL GAP** |
| **import_logs** | **MISSING** | No dedicated table | ❌ **CRITICAL GAP** |

### 1.2 What Data is Owned by Platform Owner?

**Currently Platform Owner Manages:**
- ✅ `organizations` table (company registration data)
- ✅ `roles` table (global role definitions)
- ✅ `audit_log` table (cross-tenant audit trail)
- ✅ Platform-wide metrics and statistics
- ⚠️ Can view all tenants via `/platform/tenants` endpoints

**Platform Owner Access via `/platform` endpoints:**
| Endpoint | Access | Description |
|----------|--------|-------------|
| `GET /platform/tenants` | PlatformOwner | List all companies |
| `GET /platform/tenants/{id}` | PlatformOwner | View company details |
| `PATCH /platform/tenants/{id}` | PlatformOwner | Update company status |
| `POST /platform/tenants` | PlatformOwner | Create company |

### 1.3 What Data is Owned by Tenant?

**Tenant Business Data (with `tenant_id` foreign key):**
- ✅ `assets` - Asset inventory
- ✅ `vulnerability_findings` - Asset-CVE mappings
- ✅ `business_units` - Organizational structure
- ✅ `teams` - Team definitions
- ✅ `locations` - Asset locations
- ✅ `policy_rules` - Custom policy rules
- ✅ `prioritization_feedback` - ML feedback data
- ✅ `background_jobs` - Async job queue
- ✅ `users` - Company users (tenant_id scoped)

**Shared/Global Data:**
- ⚠️ `cve_records` - Global CVE database (no tenant_id)

### 1.4 Is Data Currently Mixed?

| Mixing Risk | Status | Evidence |
|-------------|--------|----------|
| Owner accessing tenant business data directly | ✅ **NO** - Owner endpoints only touch `organizations` table | Platform endpoints use `OrganizationRepository` only |
| Tenant accessing other tenant data | ✅ **NO** - Tenant isolation enforced | All queries filtered by `tenant_id` in `UploadService` |
| Business data in owner tables | ✅ **NO** | `organizations` table has only registration metadata |
| Owner data in business tables | ✅ **NO** | No platform config in tenant tables |

### 1.5 Can Owner Incorrectly Access Tenant Data?

| Scenario | Possible? | Current Mitigation |
|----------|-----------|-------------------|
| Owner reads tenant assets via normal admin flow | ❌ **NO** | No endpoint exists |
| Owner modifies tenant vulnerabilities | ❌ **NO** | No endpoint exists |
| Owner views tenant user passwords | ❌ **NO** | `users` requires tenant context |
| Owner impersonates tenant | ❌ **NO** | `PlatformOwnerDep` ≠ tenant context |

**Verdict: Owner CANNOT accidentally access tenant business data through normal flows.**

### 1.6 Are Company Registration Records Separate from Tenant Business Data?

**Current State: ✅ YES, PROPERLY SEPARATED**

| Aspect | Registration Data | Business Data | Separation |
|--------|-------------------|---------------|------------|
| Table | `organizations` | `assets`, `findings`, etc. | ✅ Different tables |
| Schema | id, name, code, approval_status | asset_type, cve_id, status | ✅ No overlap |
| Access | Platform Owner | Tenant Admin/Analyst | ✅ Different roles |
| UI | Platform management | Tenant workspace | ⚠️ Same codebase, different pages |

### 1.7 Upload Metadata Tracking

**Current State: ❌ INADEQUATE**

| Upload Type | Metadata Stored | Location | Auditable? |
|-------------|-----------------|----------|------------|
| Data imports (assets/vulns/mappings) | ❌ **NO** | N/A | ❌ No record |
| Generic file uploads | ✅ Partial | `audit_log` table only | ✅ Via AuditService |

**Missing Critical Metadata:**
- ❌ Uploads table for data imports
- ❌ Import results/summaries not persisted
- ❌ File processing status not tracked
- ❌ No import history per tenant
- ❌ No upload classification (assets_import vs document)

---

## STEP 2 — CORRECT OWNERSHIP MODEL DEFINITION

### A. Platform Owner / Super Admin Data

| Data Type | Examples | Owner | Access Level |
|-----------|----------|-------|--------------|
| Company Registration | `organizations.name`, `code`, `approval_status` | Platform Owner | Full CRUD |
| Company Lifecycle | `is_active`, `created_at`, `approved_by_user_id` | Platform Owner | Full CRUD |
| Platform-wide Audit | `audit_log` entries across tenants | Platform Owner | Read-only |
| Upload Governance | Cross-tenant upload metadata | Platform Owner | Read-only |
| Storage Governance | Disk usage per tenant | Platform Owner | Read-only |
| Platform Config | Global settings, role definitions | Platform Owner | Full CRUD |

### B. Tenant Company Business Data

| Data Type | Examples | Owner | Access Level |
|-----------|----------|-------|--------------|
| Asset Inventory | `assets` table records | Tenant Admin | Full CRUD |
| Vulnerability Findings | `vulnerability_findings` | Tenant Analyst+ | Full CRUD |
| Organization Structure | `business_units`, `teams` | Tenant Admin | Full CRUD |
| Users & Roles | `users`, `user_roles` | Tenant Admin | Full CRUD (tenant scope) |
| Upload History | Tenant's uploads | Tenant Admin | Read-only own |
| Import Logs | Data import results | Tenant Analyst+ | Read-only own |

### C. Upload Metadata (New Required Table)

```sql
CREATE TABLE upload_imports (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES organizations(id),
    uploaded_by_user_id UUID REFERENCES users(id),
    upload_type VARCHAR(64) NOT NULL,  -- 'assets_import', 'vulnerabilities_import', etc.
    file_name VARCHAR(255),
    file_size_bytes INTEGER,
    mime_type VARCHAR(128),
    status VARCHAR(32) NOT NULL,  -- 'processing', 'completed', 'failed'
    summary JSONB,  -- { inserted: 5, updated: 2, failed: 1, errors: [...] }
    processing_time_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

**Who Can See What:**
| Actor | Access to Upload Metadata |
|-------|---------------------------|
| Platform Owner | All uploads across all tenants (read-only) |
| Tenant Admin | Own tenant uploads only (read-only) |
| Tenant Analyst | Own tenant uploads only (read-only) |
| Regular User | No access to upload metadata |

---

## STEP 3 — UPLOAD DESTINATION VERIFICATION

### 3.1 Assets Upload

| Aspect | Current State | Destination |
|--------|---------------|-------------|
| Endpoint | `POST /api/v1/upload/assets` | ✅ Correct |
| File Storage | Parsed in memory, NOT stored to disk | ✅ Data import pattern |
| Destination Table(s) | `assets`, `asset_attributes` | ✅ Correct |
| Tenant Ownership | ✅ Enforced via `UploadService.tenant_id` | ✅ Correct |

### 3.2 Vulnerability Upload

| Aspect | Current State | Destination |
|--------|---------------|-------------|
| Endpoint | `POST /api/v1/upload/vulnerabilities` | ✅ Correct |
| File Storage | Parsed in memory | ✅ Data import pattern |
| Destination Table(s) | `cve_records` | ✅ Correct |
| Tenant Ownership | ⚠️ `cve_records` is global, but findings link to tenant | ⚠️ Partial |

### 3.3 Mapping Upload

| Aspect | Current State | Destination |
|--------|---------------|-------------|
| Endpoint | `POST /api/v1/upload/mappings` | ✅ Correct |
| File Storage | Parsed in memory | ✅ Data import pattern |
| Destination Table(s) | `vulnerability_findings` | ✅ Correct |
| Tenant Ownership | ✅ Enforced via `tenant_id` | ✅ Correct |

### 3.4 Generic Document Upload

| Aspect | Current State | Destination |
|--------|---------------|-------------|
| Endpoint | `POST /api/v1/upload` | ✅ Correct (separate endpoint) |
| Disk Path | `/app/uploads/{file_id}{ext}` | ⚠️ **NOT tenant-scoped** |
| DB Metadata | ❌ No uploads table, only `audit_log` | ❌ **INADEQUATE** |
| Tenant Folder | ❌ No - all files in single directory | ❌ **SECURITY RISK** |
| Storage Quota | ❌ Not tracked per tenant | ❌ Missing |

### 3.5 Upload History / Audit Trail

| Aspect | Current State |
|----------|---------------|
| Data imports logged | ❌ Only in `audit_log` via `AuditService` |
| Generic uploads logged | ✅ Via `AuditService.record()` |
| Import summaries persisted | ❌ Only returned in API response, not stored |
| Failed upload tracking | ❌ No persistent failed upload log |
| Owner can see all uploads | ❌ No query interface for cross-tenant uploads |

### 3.6 Owner Access to Metadata

| Capability | Current State |
|------------|---------------|
| View upload metadata | ❌ No endpoint exists |
| View import summaries | ❌ Not persisted |
| View storage usage | ❌ No tracking |
| View failed uploads | ❌ No tracking |
| View processing status | ❌ Not tracked |

---

## STEP 4 — PROBLEMS FOUND

### Critical Issues (Fix Required)

| # | Issue | Impact | Severity |
|---|-------|--------|----------|
| 1 | **No `upload_imports` table** | Cannot track data import history, audit imports, or view processing status | **CRITICAL** |
| 2 | **Generic uploads not tenant-scoped on disk** | Files from all tenants mixed in `/app/uploads/` | **HIGH** |
| 3 | **No uploads table for file metadata** | Cannot query upload history, track storage usage | **HIGH** |
| 4 | **Import summaries not persisted** | Cannot review import results later | **MEDIUM** |
| 5 | **No upload classification** | Cannot distinguish assets_import from document_upload | **MEDIUM** |
| 6 | **Owner cannot view upload governance data** | No visibility into tenant upload activity | **MEDIUM** |
| 7 | **No storage quota tracking** | Cannot enforce per-tenant storage limits | **LOW** |

### Design Issues

| # | Issue | Current | Recommended |
|---|-------|---------|-------------|
| 8 | `cve_records` is global | No tenant_id | Keep global (correct for CVE database) |
| 9 | AuditLog.tenant_id is nullable | Can have orphaned logs | Ensure all tenant actions populate tenant_id |

---

## STEP 5 — CORRECT OWNERSHIP MODEL (Target State)

### Data Ownership Matrix

| Data | Platform Owner | Tenant Admin | Tenant Analyst | Notes |
|------|----------------|--------------|----------------|-------|
| Company Registration | CRUD | - | - | Owner manages lifecycle |
| Tenant Business Data | - | CRUD | RU | Tenant manages own data |
| Upload Metadata | R (all) | R (own) | R (own) | Owner sees governance view |
| Import Summaries | R (all) | R (own) | R (own) | For audit and debugging |
| Audit Logs | R (all) | R (own) | - | Cross-tenant for owner |
| Global CVE Data | R | R | R | Read-only for all |

### Upload Destination Matrix

| Upload Type | Storage | Path/Table | Metadata Table |
|-------------|---------|------------|----------------|
| assets_import | Memory → DB | `assets` table | `upload_imports` |
| vulnerabilities_import | Memory → DB | `cve_records` table | `upload_imports` |
| mappings_import | Memory → DB | `vulnerability_findings` | `upload_imports` |
| supporting_document | Disk | `/app/uploads/{tenant_id}/{file_id}` | `uploads` |
| scan_report | Disk | `/app/uploads/{tenant_id}/{file_id}` | `uploads` |

---

## STEP 6 — IMPLEMENTATION REQUIRED

### 6.1 Database Changes

1. **Create `upload_imports` table**
   - Track all data imports (assets, vulnerabilities, mappings)
   - Store import summaries
   - Link to tenant and uploader

2. **Create `uploads` table**
   - Track file uploads (documents, reports)
   - Store file metadata
   - Link to tenant and uploader

3. **Update generic upload endpoint**
   - Store files in tenant-scoped directories: `/app/uploads/{tenant_id}/`

### 6.2 Backend Changes

1. **Add upload governance endpoints**
   - `GET /platform/uploads` - List all uploads (owner)
   - `GET /platform/uploads/{tenant_id}` - List tenant uploads (owner)
   - `GET /platform/storage` - Storage usage stats

2. **Update upload service**
   - Persist import summaries to `upload_imports`
   - Classify uploads by type

3. **Update generic uploads endpoint**
   - Use tenant-scoped storage path
   - Record to `uploads` table

### 6.3 Frontend Changes

1. **Owner Dashboard**
   - Company management view (exists)
   - Upload governance view (new)
   - Storage overview (new)

2. **Tenant Workspace**
   - Upload history view (new)
   - Import results view (new)

---

## AUDIT CONCLUSION

### Current State: **PARTIAL**

**What's Working:**
- ✅ Company registration properly separated from tenant business data
- ✅ Tenant isolation enforced in business tables
- ✅ Owner cannot accidentally access tenant business data
- ✅ Data import endpoints correctly parse and import to database
- ✅ Audit logging exists via `AuditService`

**What's Broken/Missing:**
- ❌ No upload metadata tracking for data imports
- ❌ Generic uploads not tenant-scoped on disk
- ❌ No import summary persistence
- ❌ Owner has no visibility into upload activity
- ❌ No upload classification system
- ❌ No storage governance

**Overall Classification: PARTIAL**

The ownership model has the right foundation but requires the addition of proper upload metadata tracking and storage governance to be production-ready.

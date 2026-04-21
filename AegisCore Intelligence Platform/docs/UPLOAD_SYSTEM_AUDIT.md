# Upload System Audit Report

## Executive Summary

**VERDICT: NOT PRODUCTION-READY - MAJOR REDESIGN REQUIRED**

The current upload system has a critical disconnect between frontend and backend, lacks proper categorization, and does not meet production security or UX standards.

---

## STEP 1 — CURRENT UPLOAD SYSTEM AUDIT

### 1. Current Routes & Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/upload` | POST | Generic file storage | **MISALIGNED** |
| `/api/v1/upload/assets` | POST | CSV asset import | **Not used by frontend** |
| `/api/v1/upload/vulnerabilities` | POST | CSV vulnerability import | **Not used by frontend** |
| `/api/v1/upload/templates/{type}` | GET | Download templates | **Not used by frontend** |
| `/api/v1/uploads` | GET | List stored files | **Exists but disconnected** |
| `/api/v1/uploads/{file_id}` | GET | Download file | **Exists but disconnected** |
| `/api/v1/uploads/{file_id}` | DELETE | Delete file | **Admin only, not exposed** |

### 2. Frontend Upload Architecture

**File:** `frontend/src/app/(app)/uploads/page.tsx`
- Single generic `FileUpload` component
- No categorization
- No template downloads
- No import summaries

**File:** `frontend/src/components/upload/FileUpload.tsx`
- Sends to wrong endpoint: `/api/v1/upload` (generic storage)
- Does NOT use: `/api/v1/upload/assets` or `/api/v1/upload/vulnerabilities`
- No parsing or validation feedback
- Just stores file, doesn't import data

### 3. Backend Upload Architecture

**Two competing systems:**

**System A: uploads.py (Generic Storage)**
- Stores files to disk (`/app/uploads`)
- No parsing, no database import
- Used by frontend (wrong endpoint)

**System B: upload.py (Data Import)**
- Parses CSV and imports to database
- Tenant-scoped with validation
- Has templates
- NOT used by frontend

### 4. File Types Accepted

**Frontend claims:**
- CSV, JSON, XML, Nessus, SARIF, PDF, ZIP

**Backend System A accepts:**
- CSV, JSON, XML, Nessus, SARIF, PDF, ZIP (just stores)

**Backend System B accepts:**
- CSV only (for assets/vulnerabilities)

### 5. Tenant Safety Review

| Aspect | Status | Notes |
|--------|--------|-------|
| Authentication | ✅ | Requires valid JWT |
| Tenant scoping | ✅ | `UploadService` uses `tenant_context` |
| Role check | ✅ | `WriterDep` required |
| Cross-tenant contamination | ⚠️ | Low risk but no explicit checks |
| Audit logging | ✅ | `AuditService` records uploads |

### 6. Error Handling

| Aspect | Status |
|--------|--------|
| File size limits | ✅ (50MB System A, 10MB System B) |
| File type validation | ✅ |
| CSV parsing errors | ✅ (System B) |
| Import summaries | ✅ (System B) |
| Validation errors per row | ✅ (System B) |
| Frontend error display | ⚠️ Basic only |

### 7. Testing

| Type | Status |
|------|--------|
| Unit tests for upload service | ❌ None found |
| API endpoint tests | ❌ None found |
| Frontend component tests | ❌ None found |
| E2E upload tests | ❌ None found |

---

## PROBLEMS WITH CURRENT DESIGN

### Critical Issues

1. **FRONTEND/BACKEND DISCONNECT**
   - Frontend uploads to generic file storage endpoint
   - Backend has sophisticated CSV import endpoints that are unused
   - Data import functionality is completely inaccessible

2. **NO UPLOAD CATEGORIES**
   - Single generic upload box
   - Users can't distinguish between:
     - Asset inventory upload
     - Vulnerability scan upload
     - Document/report storage

3. **NO TEMPLATE DOWNLOADS**
   - Backend provides CSV templates
   - Frontend doesn't expose them
   - Users don't know expected CSV format

4. **NO IMPORT FEEDBACK**
   - Generic upload just stores file
   - No parsing results
   - No success/failure counts
   - No row-level validation errors

5. **MISSING UPLOAD TYPES**
   - Asset-vulnerability mapping upload exists in backend but not exposed
   - Scanner report parsing (Nessus, SARIF) not implemented
   - Document uploads mixed with data imports

### UX Issues

1. **No Clear Purpose**
   - Page title: "File Uploads"
   - Description: "Upload vulnerability scan results and reports"
   - But uploads just store files, don't process them

2. **No Progress Indication**
   - Simple "Uploading..." text
   - No progress bar for large files

3. **No Recent Uploads List**
   - Backend has list endpoint
   - Frontend doesn't display it

4. **No Download/Delete Actions**
   - Files stored but can't be managed

### Security Issues

1. **File Storage Path**
   - Files stored with UUID names
   - No virus scanning
   - No content validation beyond extension

2. **ZIP File Handling**
   - Accepts ZIP but doesn't validate contents
   - Potential zip bomb risk

---

## DECISION: IS ONE UPLOAD OPTION ENOUGH?

**NO - ABSOLUTELY NOT**

A single generic upload is NOT sufficient for a production vulnerability management platform. Here's why:

| Upload Category | Purpose | Validation | User |
|-----------------|---------|------------|------|
| **Assets** | Import asset inventory | Schema validation, BU/team lookup | Admin |
| **Vulnerabilities** | Import vulnerability data | CVE format, severity validation | Analyst |
| **Mappings** | Link vulns to assets | Asset/vuln existence check | Analyst |
| **Scan Reports** | Raw scanner output | Format-specific parsing | Analyst |
| **Documents** | Evidence, reports, PDFs | File size, virus scan | Any role |

Each category has:
- Different validation rules
- Different expected schemas
- Different database tables
- Different user permissions
- Different processing logic

---

## RECOMMENDED UPLOAD ARCHITECTURE

### 5 Upload Categories

1. **Assets Upload**
   - Endpoint: `POST /api/v1/uploads/assets`
   - Formats: CSV, JSON
   - Fields: name, type, hostname, IP, criticality, BU, team, location
   - Validation: BU/team must exist in tenant

2. **Vulnerabilities Upload**
   - Endpoint: `POST /api/v1/uploads/vulnerabilities`
   - Formats: CSV, JSON
   - Fields: CVE ID, title, severity, CVSS, description
   - Validation: CVE ID format, CVSS range

3. **Asset-Vulnerability Mapping**
   - Endpoint: `POST /api/v1/uploads/mappings`
   - Formats: CSV, JSON
   - Fields: asset_id/asset_name, CVE_id, status, discovered_date
   - Validation: Asset and CVE must exist

4. **Scanner Reports**
   - Endpoint: `POST /api/v1/uploads/scans`
   - Formats: Nessus (.nessus), SARIF (.sarif), XML, JSON
   - Processing: Format-specific parser
   - Result: Extracted findings → vulnerability records

5. **Supporting Documents**
   - Endpoint: `POST /api/v1/uploads/documents`
   - Formats: PDF, ZIP, TXT
   - Purpose: Evidence storage, executive reports
   - Result: File stored with metadata

### Frontend Structure

```
/uploads (page)
├── UploadCategories (tabbed/sectioned interface)
│   ├── AssetsUploadCard
│   │   ├── Template download button
│   │   ├── CSV/JSON upload area
│   │   ├── Validation preview
│   │   └── Import results
│   ├── VulnerabilitiesUploadCard
│   ├── MappingsUploadCard
│   ├── ScannerReportsCard
│   └── DocumentsUploadCard
├── RecentUploadsList
│   ├── File name, type, date
│   ├── Status (success/partial/failed)
│   ├── Records imported
│   └── Download/Delete actions
└── UploadGuidelines (sidebar)
```

---

## IMPLEMENTATION PLAN

### Phase 1: Fix Frontend/Backend Disconnect
1. Update frontend to use correct endpoints
2. Add template download buttons
3. Show import summaries

### Phase 2: Separate Upload Categories
1. Create 5 upload section components
2. Add format-specific validation
3. Add preview before import

### Phase 3: Add Missing Backend Features
1. Implement mapping upload endpoint
2. Add scan report parsers (Nessus, SARIF)
3. Add document upload with metadata

### Phase 4: Testing
1. Unit tests for each upload type
2. Integration tests
3. E2E tests
4. Security tests

---

## SECURITY REQUIREMENTS

1. **Tenant Isolation**
   - All imports scoped to authenticated tenant
   - Cross-tenant asset/vuln lookup blocked
   - Import audit logging

2. **File Validation**
   - Extension whitelist per upload type
   - MIME type validation
   - Size limits
   - Content scanning (future)

3. **Role-Based Access**
   - Assets: Admin only
   - Vulnerabilities: Analyst+
   - Mappings: Analyst+
   - Reports: Analyst+
   - Documents: Any authenticated

4. **Data Validation**
   - Schema validation before import
   - Referential integrity checks
   - Sanitize all string inputs
   - Validate date formats

---

## TEST REQUIREMENTS

### Unit Tests (Backend)
- `test_upload_service_assets.py`
- `test_upload_service_vulnerabilities.py`
- `test_upload_service_mappings.py`
- `test_upload_service_scans.py`
- `test_upload_service_documents.py`

### API Tests
- Each endpoint success/failure
- Validation error cases
- Tenant isolation cases
- Role permission cases

### Frontend Tests
- Component rendering
- File selection
- Upload progress
- Error display
- Success summary

### E2E Tests
- Full upload flow
- Import verification in dashboard
- Cross-tenant blocking

---

## FINAL VERDICT

**Current System: FAIL**
- Frontend uses wrong endpoint
- Data import functionality inaccessible
- No categorization
- No templates
- Missing test coverage

**After Redesign: EXPECTED PASS**
- Clear upload categories
- Proper endpoint usage
- Template downloads
- Import feedback
- Full test coverage
- Tenant-safe

---

## FILES TO MODIFY/CREATE

### Backend
1. `app/api/v1/endpoints/upload.py` - Expand with mapping endpoint
2. `app/services/upload_service.py` - Add mapping upload method
3. `tests/unit/test_upload_service_*.py` - Create test files
4. `tests/integration/test_upload_api.py` - Create integration tests

### Frontend
1. `app/(app)/uploads/page.tsx` - Redesign with categories
2. `components/upload/FileUpload.tsx` - Deprecate or specialize
3. `components/upload/AssetUploadCard.tsx` - New
4. `components/upload/VulnerabilityUploadCard.tsx` - New
5. `components/upload/MappingUploadCard.tsx` - New
6. `components/upload/ScannerUploadCard.tsx` - New
7. `components/upload/DocumentUploadCard.tsx` - New
8. `components/upload/RecentUploadsList.tsx` - New
9. `lib/api.ts` - Add upload API functions

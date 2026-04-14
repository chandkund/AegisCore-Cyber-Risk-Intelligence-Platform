# Governance, workspace, and row-level security (RLS)

## Workspace layout

| Asset | Suggested workspace | Audience |
|-------|---------------------|----------|
| Dataset `AegisCore Reporting` | `AegisCore — Production` | Certified; scheduled refresh |
| Report `AegisCore — Executive Risk` | Same | Leadership, risk committee |
| Dev copies | `AegisCore — Dev` | Builders only |

Enable **dataset certification** after validation against `verify_reporting_prereqs.sql` and a signed-off refresh run.

## Roles (Microsoft 365 / Fabric)

- **Members:** report consumers (view only).
- **Contributors:** authors.
- **Admins:** workspace settings, gateway credentials.

Avoid sharing **Edit** links broadly; use **Build permission** only for data modelers.

## Row-level security (RLS)

PostgreSQL **does not** enforce Power BI user identity. RLS is implemented in **DAX** on the published dataset.

### Pattern A — Business unit restriction

**Scenario:** Manager may only see their BU (`dim_business_unit.code`).

1. Create a **static RLS role** `BU_CORP_IT` with DAX filter on `Dim Business Unit`:

```dax
[code] = "CORP-IT"
```

2. Or use **dynamic RLS** with a **security table** ingested from HR/IdP (not in this repo): table `UserBU(UserEmail, BUCode)` related to `Dim Business Unit`, and:

```dax
Dim Business Unit[code] =
RELATED( UserBU[BUCode] )
-- Or use LOOKUPVALUE pattern filtered by USERNAME()
```

3. In Service, map **Azure AD UPN** to role membership via **Manage roles** → **Members** (AAD groups preferred).

### Pattern B — Analyst full access

Role `Analyst_All` with no table filters; assign to security group `SG-AegisCore-Analysts`.

### Testing

Use **View as** in Power BI Desktop with each role before publish.

## Service principal (automation)

For **unattended refresh** or **REST embed token** flows, register an Azure AD app, grant Power BI API permissions, and add the SPN as workspace Admin or Member per Microsoft guidance. Store secrets in Azure Key Vault — not in Git.

## Data classification

Treat **assignee email**, **asset hostname**, and **IP** as **internal**; restrict executive reports to aggregates where policy requires. Consider a **separate dataset** with assignee dimension excluded.

## Audit

- Enable **Power BI activity log** (tenant) for dataset refresh and view events.
- Correlate refresh times with ETL `etl_watermarks` for `reporting_daily` when investigating stale dashboards.

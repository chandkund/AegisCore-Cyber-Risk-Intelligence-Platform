# Dashboard pages specification

Executive-facing report: **`AegisCore — Executive Risk`**. Theme: dark-neutral or corporate; WCAG AA contrast for text.

## Page 1 — Executive summary

**Purpose:** Single-screen risk posture (mirrors Next.js dashboard intent).

| Visual | Field wells / logic |
|--------|---------------------|
| **Card** | `Open Findings` measure |
| **Card** | `Overdue Findings` measure |
| **Card** | `Critical or High Findings` measure |
| **Donut or bar** | `Dim Severity[severity_code]` × `Findings Count` |
| **Stacked bar** | `Fact Snapshot[status]` × `Findings Count` |
| **Table (top 10)** | `Dim Asset[name]`, `Findings Count`, `Max CVSS in Context` — sort by count desc |

**Slicers:** `Dim Business Unit[name]`, `Dim Team[name]` (optional), `Fact Snapshot[exploit_available]`.

## Page 2 — Business unit risk

**Purpose:** Parity with `/analytics` business-unit table.

| Visual | Details |
|--------|---------|
| **Matrix** | Rows: `Dim Business Unit[code]`, `Dim Business Unit[name]`; Values: `Findings Count`, `Critical or High Findings`, `Overdue Findings` |
| **Bar chart** | Axis: `Dim Business Unit[name]`; Value: `Critical or High Findings` |

Cross-highlight from Page 1 slicers.

## Page 3 — Asset exposure

**Purpose:** Top assets by open findings (similar to `top-assets` API concept).

| Visual | Details |
|--------|---------|
| **Table** | `Dim Asset[name]`, `Dim Asset[asset_type]`, `Dim Asset[criticality]`, `Findings Count`, `Max CVSS in Context`, `Avg Days Open` |
| **Scatter** | X: `Findings Count`; Y: `Max CVSS in Context`; Details: `Dim Asset[name]` |

Filter: `Open Findings` context or explicit status slicer.

## Page 4 — CVE / vulnerability concentration

| Visual | Details |
|--------|---------|
| **Table** | `Dim CVE[cve_id]`, `Dim Severity[severity_code]`, `Findings Count`, `Exploit Available Findings` |
| **Bar** | Top N `Dim CVE[cve_id]` by `Findings Count` |

## Page 5 — Aging & SLA

| Visual | Details |
|--------|---------|
| **Histogram / column** | Bin `Fact Snapshot[days_open]` (use group in Desktop or calculated column buckets) × `Findings Count` |
| **Card** | `Median Days Open` |
| **Table** | Findings with `is_overdue` = true: keys hidden, show `Dim Asset[name]`, `Dim CVE[cve_id]`, `days_open` |

## Page 6 — Assignee workload (optional)

| Visual | Details |
|--------|---------|
| **Matrix** | `Dim Assignee[full_name]` × `Findings Count`, `Overdue Findings` |

Hide page if PII policy restricts name distribution in executive workspace.

## Bookmarks & navigation

- **Bookmark** “Reset filters” clearing all slicers.
- **Buttons** on each page: **Back to summary**.

## Mobile layout

Use **Phone layout** for Page 1 only: stack cards vertically, single bar for severity.

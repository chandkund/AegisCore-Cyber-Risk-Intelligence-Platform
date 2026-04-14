# DAX measures (templates)

Place measures in a table named **`Measure Table`** (disconnected, hidden) or on `Fact Snapshot`. Use **`Fact Snapshot`** below; rename if your fact table differs.

Assumes **latest snapshot** model: one row per open/at-risk finding as of the latest ETL date.

## Core counts

```dax
Open Findings :=
VAR OpenStatuses = { "OPEN", "IN_PROGRESS" }
RETURN
CALCULATE(
    DISTINCTCOUNT( 'Fact Snapshot'[finding_oltp_id] ),
    'Fact Snapshot'[status] IN OpenStatuses
)
```

```dax
Findings Count := DISTINCTCOUNT( 'Fact Snapshot'[finding_oltp_id] )
```

```dax
Overdue Findings :=
CALCULATE(
    DISTINCTCOUNT( 'Fact Snapshot'[finding_oltp_id] ),
    'Fact Snapshot'[is_overdue] = TRUE
)
```

## Severity and exposure

```dax
Critical or High Findings :=
CALCULATE(
    DISTINCTCOUNT( 'Fact Snapshot'[finding_oltp_id] ),
    'Dim Severity'[severity_code] IN { "CRITICAL", "HIGH" }
)
```

```dax
Exploit Available Findings :=
CALCULATE(
    DISTINCTCOUNT( 'Fact Snapshot'[finding_oltp_id] ),
    'Fact Snapshot'[exploit_available] = TRUE
)
```

## Aging

```dax
Avg Days Open :=
AVERAGE( 'Fact Snapshot'[days_open] )
```

```dax
Median Days Open :=
MEDIAN( 'Fact Snapshot'[days_open] )
```

## CVSS / EPSS (context)

```dax
Max CVSS in Context :=
MAX( 'Fact Snapshot'[cvss_base_score] )
```

```dax
Avg EPSS in Context :=
AVERAGE( 'Fact Snapshot'[epss_score] )
```

## API parity notes

- FastAPI `/analytics/summary` aggregates **OLTP** live state; this model reflects **reporting snapshot** after ETL. Numbers align when ETL runs for “today” and definitions match (e.g. what counts as “open”).
- For **exact** API parity in BI, add calculated tables from REST (Power Query Web.Contents) in a **separate** composite model — out of scope for the default warehouse path.

## Time intelligence (history model only)

If using `Fact Snapshot History` with `Dim Date`:

```dax
Open Findings EoP :=
CALCULATE(
    DISTINCTCOUNT( 'Fact Snapshot History'[finding_oltp_id] ),
    'Fact Snapshot History'[status] IN { "OPEN", "IN_PROGRESS" },
    LASTDATE( 'Dim Date'[full_date] )
)
```

Adjust status list to match organizational definition of “open” vs `vw_open_findings_by_bu` (excludes `REMEDIATED`, `FALSE_POSITIVE`).

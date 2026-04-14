"""
Feature engineering and proxy labels for the risk prioritization model.

See `ml/docs/ASSUMPTIONS.md` for label semantics and leakage controls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np
import pandas as pd

# Column order must match training pipeline expectations (metadata persists names).
FEATURE_COLUMNS_ORDER = [
    "cvss",
    "epss",
    "exploit",
    "asset_criticality",
    "days_open",
    "days_until_due",
    "has_assignee",
    "severity_str",
    "status_str",
    "text_n_tokens",
]


@dataclass(frozen=True)
class RawFindingRow:
    finding_id: str
    status: str
    discovered_at: datetime
    due_at: datetime | None
    has_assignee: bool
    cvss: float | None
    epss: float | None
    exploit: bool
    severity: str
    cve_title: str | None
    asset_criticality: int
    asset_name: str
    asset_type: str


def _token_count(text: str) -> int:
    return len([t for t in text.split() if t])


def compute_proxy_label(row: RawFindingRow, ref_time: datetime) -> int:
    """
    Binary proxy: 1 = organization would likely prioritize remediation soon.

    This is a *training surrogate*, not ground truth exploit outcome.
    """
    cvss = float(row.cvss) if row.cvss is not None else 0.0
    sev = row.severity.upper()
    if sev == "CRITICAL":
        return 1
    if row.exploit and cvss >= 7.0:
        return 1
    if row.status in ("OPEN", "IN_PROGRESS") and row.due_at is not None:
        if row.due_at.tzinfo is None:
            due = row.due_at.replace(tzinfo=timezone.utc)
        else:
            due = row.due_at
        if due < ref_time:
            return 1
    if row.asset_criticality >= 4 and sev in ("HIGH", "CRITICAL"):
        return 1
    if row.exploit and sev == "HIGH":
        return 1
    return 0


def row_to_feature_dict(row: RawFindingRow, ref_time: datetime) -> dict[str, Any]:
    if row.discovered_at.tzinfo is None:
        disc = row.discovered_at.replace(tzinfo=timezone.utc)
    else:
        disc = row.discovered_at.astimezone(timezone.utc)
    ref = ref_time.astimezone(timezone.utc)
    days_open = max(0.0, (ref - disc).total_seconds() / 86400.0)

    if row.due_at is None:
        days_until_due = 3650.0
    else:
        due = row.due_at if row.due_at.tzinfo else row.due_at.replace(tzinfo=timezone.utc)
        days_until_due = (due - ref).total_seconds() / 86400.0

    text = f"{row.cve_title or ''} {row.asset_name} {row.asset_type}".strip()
    return {
        "cvss": float(row.cvss) if row.cvss is not None else np.nan,
        "epss": float(row.epss) if row.epss is not None else np.nan,
        "exploit": 1.0 if row.exploit else 0.0,
        "asset_criticality": float(row.asset_criticality),
        "days_open": days_open,
        "days_until_due": days_until_due,
        "has_assignee": 1.0 if row.has_assignee else 0.0,
        "severity_str": row.severity.upper(),
        "status_str": row.status.upper(),
        "text_n_tokens": float(_token_count(text)),
    }


def rows_from_db_records(
    records: Iterable[dict[str, Any]], ref_time: datetime | None = None
) -> tuple[pd.DataFrame, np.ndarray]:
    """Build X (features) and y (proxy labels) from ORM-like dict rows."""
    ref = ref_time or datetime.now(timezone.utc)
    raw_rows: list[RawFindingRow] = []
    for r in records:
        raw_rows.append(
            RawFindingRow(
                finding_id=str(r["finding_id"]),
                status=str(r["status"]),
                discovered_at=r["discovered_at"],
                due_at=r.get("due_at"),
                has_assignee=bool(r.get("has_assignee")),
                cvss=float(r["cvss"]) if r.get("cvss") is not None else None,
                epss=float(r["epss"]) if r.get("epss") is not None else None,
                exploit=bool(r.get("exploit")),
                severity=str(r["severity"]),
                cve_title=r.get("cve_title"),
                asset_criticality=int(r["asset_criticality"]),
                asset_name=str(r.get("asset_name") or ""),
                asset_type=str(r.get("asset_type") or ""),
            )
        )
    X = build_feature_matrix(raw_rows, ref)
    y = np.array([compute_proxy_label(rw, ref) for rw in raw_rows], dtype=np.int32)
    return X, y


def build_feature_matrix(rows: Iterable[RawFindingRow], ref_time: datetime) -> pd.DataFrame:
    data = [row_to_feature_dict(r, ref_time) for r in rows]
    df = pd.DataFrame(data)
    return df[FEATURE_COLUMNS_ORDER]

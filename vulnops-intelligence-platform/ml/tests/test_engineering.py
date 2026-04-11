from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from ml.features.engineering import RawFindingRow, compute_proxy_label, row_to_feature_dict


def test_proxy_label_critical():
    ref = datetime(2026, 6, 1, tzinfo=timezone.utc)
    row = RawFindingRow(
        finding_id="x",
        status="OPEN",
        discovered_at=ref - timedelta(days=10),
        due_at=None,
        has_assignee=False,
        cvss=5.0,
        epss=0.1,
        exploit=False,
        severity="CRITICAL",
        cve_title="t",
        asset_criticality=1,
        asset_name="a",
        asset_type="server",
    )
    assert compute_proxy_label(row, ref) == 1


def test_proxy_label_overdue():
    ref = datetime(2026, 6, 1, tzinfo=timezone.utc)
    row = RawFindingRow(
        finding_id="x",
        status="OPEN",
        discovered_at=ref - timedelta(days=40),
        due_at=ref - timedelta(days=1),
        has_assignee=True,
        cvss=4.0,
        epss=0.01,
        exploit=False,
        severity="MEDIUM",
        cve_title="t",
        asset_criticality=2,
        asset_name="a",
        asset_type="app",
    )
    assert compute_proxy_label(row, ref) == 1


def test_feature_dict_shapes():
    ref = datetime(2026, 6, 1, tzinfo=timezone.utc)
    row = RawFindingRow(
        finding_id="x",
        status="OPEN",
        discovered_at=ref - timedelta(days=5),
        due_at=ref + timedelta(days=5),
        has_assignee=False,
        cvss=None,
        epss=None,
        exploit=True,
        severity="HIGH",
        cve_title="hello world",
        asset_criticality=3,
        asset_name="db-01",
        asset_type="server",
    )
    d = row_to_feature_dict(row, ref)
    assert np.isnan(d["cvss"])
    assert d["exploit"] == 1.0
    assert d["text_n_tokens"] >= 1

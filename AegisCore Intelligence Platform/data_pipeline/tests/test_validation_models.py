from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from data_pipeline.validation.models import AssetSeedRow, CveSeedRow, FindingSeedRow


def test_cve_row_valid():
    row = CveSeedRow(
        cve_id="CVE-2024-12345",
        severity="HIGH",
        cvss_base_score="7.5",
        epss_score="0.12",
        exploit_available=True,
    )
    assert row.cve_id.startswith("CVE-")


def test_cve_row_rejects_bad_severity():
    with pytest.raises(ValidationError):
        CveSeedRow(cve_id="CVE-2024-1", severity="SEVERE")  # type: ignore[arg-type]


def test_asset_criticality_bounds():
    with pytest.raises(ValidationError):
        AssetSeedRow(
            id="a0000000-0000-4000-8000-000000000001",
            name="x",
            asset_type="server",
            business_unit_code="ENG",
            criticality=9,
        )


def test_finding_parses_iso_datetime():
    f = FindingSeedRow(
        id="d0000000-0000-4000-8000-000000000001",
        asset_id="c0000000-0000-4000-8000-000000000001",
        cve_id="CVE-2024-0001",
        status="OPEN",
        discovered_at="2026-01-01T00:00:00+00:00",
    )
    assert f.discovered_at.tzinfo is not None
    assert f.discovered_at == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_finding_seed_empty_due_at_string_becomes_none():
    f = FindingSeedRow(
        id="d0000000-0000-4000-8000-000000000002",
        asset_id="c0000000-0000-4000-8000-000000000002",
        cve_id="CVE-2024-0002",
        status="OPEN",
        discovered_at="2026-01-02T00:00:00+00:00",
        due_at="",
    )
    assert f.due_at is None

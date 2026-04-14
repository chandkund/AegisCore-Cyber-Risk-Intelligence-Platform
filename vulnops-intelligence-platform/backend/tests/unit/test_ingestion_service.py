from __future__ import annotations

from app.services.ingestion_service import IngestionService


def test_normalize_and_confidence_scoring():
    records = [
        {
            "hostname": "web-01",
            "cve": "CVE-2026-0001",
            "severity": "HIGH",
            "cvss3": 8.2,
            "exploit_status": "active",
        },
        {
            "hostname": "web-01",
            "cve": "NOT-A-CVE",
            "severity": "LOW",
        },
    ]
    normalized = IngestionService.normalize_batch("nessus", records)
    assert len(normalized) == 1
    assert normalized[0].cve_id == "CVE-2026-0001"
    assert normalized[0].source_confidence >= 0.9


def test_deduplicate_keeps_higher_confidence():
    records = [
        {
            "hostname": "db-01",
            "cve_id": "CVE-2026-1111",
            "severity": "MEDIUM",
        },
        {
            "hostname": "db-01",
            "cve_id": "CVE-2026-1111",
            "severity": "HIGH",
            "cvss_base_score": 7.5,
            "exploit_available": True,
        },
    ]
    normalized = IngestionService.normalize_batch("qualys", records)
    deduped = IngestionService.deduplicate(normalized)
    assert len(deduped) == 1
    assert deduped[0].severity in {"HIGH", "MEDIUM"}
    assert deduped[0].source_confidence >= normalized[0].source_confidence

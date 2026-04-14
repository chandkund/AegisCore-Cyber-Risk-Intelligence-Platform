from __future__ import annotations

from types import SimpleNamespace

from app.services.assistant_service import AssistantService
from app.services.policy_service import PolicyService
from app.services.secrets_service import SecretsService


def test_policy_match_rule_logic():
    conds = {
        "min_risk_score": 70,
        "status_in": ["OPEN", "IN_PROGRESS"],
        "is_external": True,
        "severity_in": ["CRITICAL", "HIGH"],
    }
    finding = SimpleNamespace(risk_score=82, status="OPEN", discovered_at=None)
    asset = SimpleNamespace(is_external=True)
    cve = SimpleNamespace(severity="HIGH")
    assert PolicyService._match_rule(conds, finding, asset, cve) is True


def test_assistant_enforces_evidence_citations():
    answer = "Top risk is CVE-2026-1234 on web-01."
    records = [{"finding_id": "f-1"}, {"finding_id": "f-2"}]
    out = AssistantService._enforce_citations(answer, records)
    assert "[ref:" in out
    assert "Evidence:" in out


def test_secrets_service_status_shape():
    svc = SecretsService()
    status = svc.provider_status()
    assert "provider" in status
    assert "configured" in status
    assert "details" in status

"""Comprehensive integration tests for all 5 advanced features.

Tests the complete integration of:
1. Auto-Prioritization Engine
2. AI Risk Explanation
3. Smart NLP Search
4. What-If Risk Simulation
5. AI Security Assistant
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.oltp import Asset, CveRecord, VulnerabilityFinding


def _auth_headers(api_client: TestClient, email: str, password: str) -> dict:
    """Helper to get auth headers."""
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(api_client: TestClient) -> dict:
    return _auth_headers(api_client, "admin@aegiscore.local", "AegisCore!demo2026")


@pytest.fixture
def test_dataset(db: Session) -> list[VulnerabilityFinding]:
    """Create comprehensive test dataset with risk scores."""
    findings = []
    
    # Create varied test data
    scenarios = [
        # (cvss, criticality, external, exploit, age_days, risk_score_approx)
        (9.5, 1, True, True, 30, 85),   # Critical external
        (8.0, 2, True, False, 60, 70),  # High external
        (7.5, 3, False, True, 10, 60),  # Medium internal with exploit
        (5.0, 4, False, False, 5, 35),  # Low internal
        (9.0, 1, False, True, 90, 80),  # Critical internal old
    ]
    
    for i, (cvss, crit, external, exploit, age_days, risk_score) in enumerate(scenarios):
        asset = Asset(
            id=uuid.uuid4(),
            name=f"test-asset-{i}",
            asset_type="server" if i % 2 == 0 else "workstation",
            business_unit_id=uuid.uuid4(),
            criticality=crit,
            is_external=external,
        )
        cve = CveRecord(
            id=uuid.uuid4(),
            cve_id=f"CVE-2024-{i:04d}",
            severity="CRITICAL" if cvss >= 9 else "HIGH" if cvss >= 7 else "MEDIUM",
            cvss_base_score=Decimal(str(cvss)),
            exploit_available=exploit,
        )
        finding = VulnerabilityFinding(
            id=uuid.uuid4(),
            asset_id=asset.id,
            cve_record_id=cve.id,
            status="OPEN",
            discovered_at=datetime.now(timezone.utc) - timedelta(days=age_days),
            risk_score=Decimal(str(risk_score)),
            risk_factors={
                "cvss": cvss / 10,
                "criticality": (6 - crit) / 5,
                "exposure": 1.0 if external else 0.0,
                "exploit": 1.0 if exploit else 0.0,
                "age": min(age_days / 90, 1.0),
            },
            risk_calculated_at=datetime.now(timezone.utc),
        )
        db.add_all([asset, cve, finding])
        findings.append(finding)
    
    db.commit()
    return findings


class TestFeature1Prioritization:
    """Feature 1: Auto-Prioritization Engine Integration Tests."""

    def test_get_prioritized_vulnerabilities(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test retrieving prioritized vulnerabilities."""
        r = api_client.get(
            "/api/v1/prioritization/vulnerabilities",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) > 0
        
        # Should be sorted by risk score descending
        if len(data["items"]) >= 2:
            assert data["items"][0]["risk_score"] >= data["items"][1]["risk_score"]

    def test_risk_score_endpoint(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test getting detailed risk score for a finding."""
        finding = test_dataset[0]
        r = api_client.get(
            f"/api/v1/prioritization/vulnerabilities/{finding.id}/risk-score",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["finding_id"] == str(finding.id)
        assert "factors" in data
        assert "contributing_factors" in data

    def test_top_risks_endpoint(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test getting top risks."""
        r = api_client.get(
            "/api/v1/prioritization/top-risks?limit=3&min_risk_score=60",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) <= 3
        
        # All should have high risk scores
        for item in data:
            assert item["risk_score"] >= 60


class TestFeature2Explanation:
    """Feature 2: AI Risk Explanation Integration Tests."""

    def test_get_explanation(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test getting risk explanation."""
        finding = test_dataset[0]  # Critical finding
        r = api_client.get(
            f"/api/v1/explanations/vulnerabilities/{finding.id}",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["finding_id"] == str(finding.id)
        assert "overall_assessment" in data
        assert "detailed_explanation" in data
        assert "remediation_priority_reason" in data
        assert data["severity_level"] in ["Critical", "High", "Medium", "Low"]

    def test_get_top_factors(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test getting top contributing factors."""
        finding = test_dataset[0]
        r = api_client.get(
            f"/api/v1/explanations/vulnerabilities/{finding.id}/factors",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["finding_id"] == str(finding.id)
        assert "top_factors" in data


class TestFeature3Search:
    """Feature 3: Smart NLP Search Integration Tests."""

    def test_basic_search(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test basic search functionality."""
        r = api_client.get(
            "/api/v1/search?q=critical",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert "total" in data
        assert data["query"] == "critical"

    def test_semantic_search_intents(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test search with natural language intents."""
        queries = [
            "external vulnerabilities",
            "high risk issues",
            "exploitable vulnerabilities",
            "critical severity",
        ]
        
        for query in queries:
            r = api_client.get(
                f"/api/v1/search?q={query}",
                headers=auth_headers_admin,
            )
            assert r.status_code == 200, f"Failed for query: {query}"
            data = r.json()
            assert isinstance(data["results"], list)

    def test_search_suggestions(self, api_client: TestClient, auth_headers_admin):
        """Test search suggestions."""
        r = api_client.get(
            "/api/v1/search/suggestions?q=crit",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)


class TestFeature4Simulation:
    """Feature 4: What-If Risk Simulation Integration Tests."""

    def test_simulate_remediation(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test simulating vulnerability remediation."""
        finding_ids = [str(f.id) for f in test_dataset[:2]]
        
        r = api_client.post(
            "/api/v1/simulate/remediation",
            headers=auth_headers_admin,
            json={
                "finding_ids": finding_ids,
                "scenario_name": "Test remediation",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["scenario_name"] == "Test remediation"
        assert "before_risk" in data
        assert "after_risk" in data
        assert "reduction_percentage" in data
        assert data["selected_count"] == 2

    def test_compare_scenarios(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test comparing multiple scenarios."""
        scenarios = [
            {
                "name": "Fix 2 vulns",
                "finding_ids": [str(f.id) for f in test_dataset[:2]],
            },
            {
                "name": "Fix 3 vulns",
                "finding_ids": [str(f.id) for f in test_dataset[:3]],
            },
        ]
        
        r = api_client.post(
            "/api/v1/simulate/compare",
            headers=auth_headers_admin,
            json={"scenarios": scenarios},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        
        # Should be sorted by reduction percentage
        assert data[0]["reduction_percentage"] >= data[1]["reduction_percentage"]

    def test_get_recommendations(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test getting high-impact recommendations."""
        r = api_client.get(
            "/api/v1/simulate/recommendations?limit=5",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        data = r.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) <= 5
        
        # Each recommendation should have reasoning
        for rec in data["recommendations"]:
            assert "finding_id" in rec
            assert "risk_score" in rec
            assert "reasoning" in rec

    def test_simulate_remediation_invalid_uuid(self, api_client: TestClient, auth_headers_admin):
        r = api_client.post(
            "/api/v1/simulate/remediation",
            headers=auth_headers_admin,
            json={"finding_ids": ["not-a-uuid"], "scenario_name": "invalid"},
        )
        assert r.status_code == 422

    def test_simulate_remediation_duplicate_ids(self, api_client: TestClient, auth_headers_admin, test_dataset):
        fid = str(test_dataset[0].id)
        r = api_client.post(
            "/api/v1/simulate/remediation",
            headers=auth_headers_admin,
            json={"finding_ids": [fid, fid], "scenario_name": "dupes"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["selected_count"] == 2


class TestFeature5Assistant:
    """Feature 5: AI Security Assistant Integration Tests."""

    def test_prioritization_question(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test assistant answering prioritization question."""
        r = api_client.post(
            "/api/v1/assistant/query",
            headers=auth_headers_admin,
            json={"question": "What should I fix first?"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert data["question_type"] == "prioritization"
        assert "supporting_records" in data
        assert "suggested_followups" in data

    def test_search_question(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test assistant answering search question."""
        r = api_client.post(
            "/api/v1/assistant/query",
            headers=auth_headers_admin,
            json={"question": "Show me critical vulnerabilities"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert data["question_type"] == "search"

    def test_simulation_question(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test assistant answering simulation question."""
        r = api_client.post(
            "/api/v1/assistant/query",
            headers=auth_headers_admin,
            json={"question": "What if I fix 3 vulnerabilities?"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert data["question_type"] == "simulation"
        # Should include simulation metrics
        assert "reduction" in data["answer"].lower() or "risk" in data["answer"].lower()

    def test_explanation_question(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test assistant answering explanation question."""
        r = api_client.post(
            "/api/v1/assistant/query",
            headers=auth_headers_admin,
            json={"question": "Why are external assets risky?"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert data["question_type"] == "explanation"

    def test_quick_query(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test lightweight quick query endpoint."""
        r = api_client.post(
            "/api/v1/assistant/quick",
            headers=auth_headers_admin,
            json={"question": "What are my top risks?"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "question_type" in data
        # Should not have full metadata
        assert "supporting_records" not in data

    def test_assistant_low_evidence_guardrail(self, api_client: TestClient, auth_headers_admin):
        r = api_client.post(
            "/api/v1/assistant/query",
            headers=auth_headers_admin,
            json={"question": "find vulnerability xyz_nonexistent_random_term_12345"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "Note: this answer is currently low-evidence" in data["answer"]


class TestCrossFeatureIntegration:
    """Cross-feature integration tests."""

    def test_end_to_end_workflow(self, api_client: TestClient, auth_headers_admin, test_dataset):
        """Test complete workflow across all features."""
        # 1. Get prioritized vulnerabilities
        r = api_client.get(
            "/api/v1/prioritization/vulnerabilities?limit=5",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        prioritized = r.json()
        assert len(prioritized["items"]) > 0
        top_finding_id = prioritized["items"][0]["id"]
        
        # 2. Get explanation for top finding
        r = api_client.get(
            f"/api/v1/explanations/vulnerabilities/{top_finding_id}",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        explanation = r.json()
        assert "overall_assessment" in explanation
        
        # 3. Search for similar issues
        cve_id = prioritized["items"][0]["cve_id"]
        r = api_client.get(
            f"/api/v1/search?q={cve_id}",
            headers=auth_headers_admin,
        )
        assert r.status_code == 200
        
        # 4. Simulate fixing top 3
        top_3_ids = [item["id"] for item in prioritized["items"][:3]]
        r = api_client.post(
            "/api/v1/simulate/remediation",
            headers=auth_headers_admin,
            json={"finding_ids": top_3_ids, "scenario_name": "Fix top 3"},
        )
        assert r.status_code == 200
        simulation = r.json()
        assert simulation["reduction_percentage"] >= 0
        
        # 5. Ask assistant about the workflow
        r = api_client.post(
            "/api/v1/assistant/query",
            headers=auth_headers_admin,
            json={"question": "What are my top 3 risks?"},
        )
        assert r.status_code == 200
        assistant_response = r.json()
        assert assistant_response["question_type"] == "prioritization"

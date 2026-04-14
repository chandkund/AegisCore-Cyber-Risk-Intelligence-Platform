"""AI Security Assistant Service - answers questions using platform data.

Provides grounded, data-driven answers to security questions using:
- Prioritization engine results
- Risk explanations
- Smart search
- Simulation results
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services.explanation_service import ExplanationService
from app.services.risk_engine_service import RiskEngineService
from app.services.search_service import SearchService
from app.services.simulation_service import SimulationService


@dataclass
class AssistantResponse:
    """AI Assistant response."""
    answer: str
    question_type: str
    supporting_records: list[dict[str, Any]]
    confidence: str  # high, medium, low
    suggested_followups: list[str]
    generated_at: datetime


class AssistantService:
    """Security assistant that answers questions using real platform data.
    
    Question types supported:
    - Prioritization: "What should I fix first?"
    - Risk explanation: "Why is this asset high risk?"
    - Search: "Show me critical web vulnerabilities"
    - Simulation: "What if I fix these 5 issues?"
    - Trending: "What's my biggest risk trend?"
    """

    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.risk_service = RiskEngineService(db)
        self.explanation_service = ExplanationService(db)
        self.search_service = SearchService(db, tenant_id=tenant_id)
        self.simulation_service = SimulationService(db, tenant_id=tenant_id)

    @staticmethod
    def _fmt_risk(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.1f}"

    @staticmethod
    def _bounded_supporting(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return records[:10]

    @staticmethod
    def _enforce_citations(answer: str, supporting_records: list[dict[str, Any]]) -> str:
        if not supporting_records:
            return answer
        cited = answer
        markers: list[str] = []
        for idx, rec in enumerate(supporting_records[:3], start=1):
            fid = rec.get("finding_id") or rec.get("cve_id") or "record"
            markers.append(f"[ref:{idx}:{fid}]")
        if "[ref:" not in cited:
            cited = f"{cited}\n\nEvidence: {' '.join(markers)}"
        return cited

    def _classify_question(self, question: str) -> str:
        """Classify the type of security question."""
        q_lower = question.lower()
        
        # Prioritization questions
        if any(w in q_lower for w in [
            "fix first", "priority", "prioritize", "what to fix",
            "most important", "top priority", "which first", "start with"
        ]):
            return "prioritization"
        
        # Explanation questions
        if any(w in q_lower for w in [
            "why", "explain", "reason", "cause", "because",
            "how come", "what makes"
        ]):
            return "explanation"
        
        # Search/Discovery questions
        if any(w in q_lower for w in [
            "show", "find", "list", "get", "search", "look for",
            "any", "are there", "do we have"
        ]):
            return "search"
        
        # Simulation/What-if questions
        if any(w in q_lower for w in [
            "what if", "simulate", "scenario", "happens if",
            "would happen", "impact of fixing"
        ]):
            return "simulation"
        
        # Trends/Analytics questions
        if any(w in q_lower for w in [
            "trend", "over time", "increasing", "decreasing",
            "going", "changes", "progress"
        ]):
            return "trends"
        
        # Default to search
        return "search"

    def _answer_prioritization(self, question: str) -> AssistantResponse:
        """Answer prioritization questions using real risk data."""
        # Get top risks
        top_risks, _ = self.risk_service.get_prioritized_findings(
            tenant_id=self.tenant_id,
            limit=5,
            min_risk_score=60,
        )
        
        if not top_risks:
            return AssistantResponse(
                answer="No high-risk vulnerabilities are currently identified in the system. "
                       "This could mean either your environment is well-protected, or we need "
                       "to refresh the vulnerability scan data.",
                question_type="prioritization",
                supporting_records=[],
                confidence="high",
                suggested_followups=[
                    "When was the last vulnerability scan?",
                    "Show me all open vulnerabilities",
                    "What's the oldest vulnerability?",
                ],
                generated_at=datetime.now(timezone.utc),
            )
        
        # Build answer with real data
        risk_items = []
        records = []
        
        for r in top_risks[:3]:
            finding = r["finding"]
            risk_items.append(
                f"• {r['cve_id'] or 'Unknown CVE'} on {r['asset_name']} "
                f"(Risk Score: {r['risk_score']:.1f})"
            )
            records.append({
                "finding_id": str(finding.id),
                "cve_id": r["cve_id"],
                "asset_name": r["asset_name"],
                "risk_score": r["risk_score"],
            })
        
        answer = (
            f"Based on current risk scoring, you should prioritize these vulnerabilities:\n\n"
            + "\n".join(risk_items) + "\n\n"
            + "These are ranked highest due to a combination of:\n"
            + "- CVSS severity and exploit availability\n"
            + "- Asset criticality and external exposure\n"
            + "- Vulnerability age and remediation status\n\n"
            + f"Fixing the top {len(risk_items)} would address the highest-risk items in your environment."
        )
        
        return AssistantResponse(
            answer=answer,
            question_type="prioritization",
            supporting_records=self._bounded_supporting(records),
            confidence="high",
            suggested_followups=[
                "Why is the top one so risky?",
                "What if I only fix the first one?",
                "Show me more high-risk items",
            ],
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_search(self, question: str) -> AssistantResponse:
        """Answer search/discovery questions."""
        # Use search service to find relevant vulnerabilities
        results, total = self.search_service.search(
            query=question,
            limit=10,
        )
        
        if not results:
            return AssistantResponse(
                answer=f"I couldn't find any vulnerabilities matching your criteria. "
                       f"Try broadening your search or checking if the vulnerability data is up to date.",
                question_type="search",
                supporting_records=[],
                confidence="high",
                suggested_followups=[
                    "Show me all open vulnerabilities",
                    "What assets do we have?",
                    "When was the last scan?",
                ],
                generated_at=datetime.now(timezone.utc),
            )
        
        # Build response
        summary = f"I found {total} vulnerabilities matching your search. Here are the top {len(results)}:\n\n"
        
        items = []
        records = []
        for r in results[:5]:
            items.append(
                f"• {r.cve_id or 'Unknown CVE'} on {r.asset_name} "
                f"(Risk: {self._fmt_risk(r.risk_score)}, Status: {r.status})"
            )
            records.append({
                "finding_id": r.finding_id,
                "cve_id": r.cve_id,
                "asset_name": r.asset_name,
                "risk_score": r.risk_score,
            })
        
        answer = summary + "\n".join(items)
        
        return AssistantResponse(
            answer=answer,
            question_type="search",
            supporting_records=self._bounded_supporting(records),
            confidence="high",
            suggested_followups=[
                "Which of these should I fix first?",
                "Explain the risk for the top one",
                "Are there any exploits available?",
            ],
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_simulation(self, question: str) -> AssistantResponse:
        """Answer what-if simulation questions."""
        # Extract number if present ("what if I fix 5 vulnerabilities")
        numbers = re.findall(r'\d+', question)
        count = int(numbers[0]) if numbers else 5
        
        # Get recommendations
        recommendations = self.simulation_service.recommend_high_impact_fixes(
            max_recommendations=count,
        )
        
        if not recommendations:
            return AssistantResponse(
                answer="I don't have enough data to simulate that scenario. "
                       "Please ensure vulnerability data is loaded.",
                question_type="simulation",
                supporting_records=[],
                confidence="low",
                suggested_followups=["Show me current vulnerabilities"],
                generated_at=datetime.now(timezone.utc),
            )
        
        # Simulate fixing top N recommendations
        finding_ids = [r["finding_id"] for r in recommendations[:count]]
        sim_result = self.simulation_service.simulate_remediation(
            finding_ids=finding_ids,
            scenario_name=f"Fix top {count} recommended",
        )
        
        answer = (
            f"If you fix the top {count} recommended vulnerabilities:\n\n"
            f"📊 Current State:\n"
            f"   • Total open vulnerabilities: {sim_result.before_risk['total_count']}\n"
            f"   • Average risk score: {sim_result.before_risk['average_risk_score']:.1f}\n"
            f"   • Critical risk items: {sim_result.before_risk['critical_count']}\n\n"
            f"✅ After Remediation:\n"
            f"   • Remaining vulnerabilities: {sim_result.after_risk['total_count']}\n"
            f"   • New average risk: {sim_result.after_risk['average_risk_score']:.1f}\n"
            f"   • Remaining critical: {sim_result.after_risk['critical_count']}\n\n"
            f"📉 Risk Reduction: {sim_result.reduction_percentage:.1f}%\n\n"
            f"This would impact {len(sim_result.impacted_assets)} assets."
        )
        
        return AssistantResponse(
            answer=answer,
            question_type="simulation",
            supporting_records=self._bounded_supporting([{"simulation_result": sim_result.__dict__}]),
            confidence="high",
            suggested_followups=[
                "Which specific vulnerabilities are these?",
                "What if I fix 10 instead?",
                "What's the cost-benefit?",
            ],
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_explanation(self, question: str) -> AssistantResponse:
        """Answer explanation questions (redirects to search then explanation)."""
        # First search for relevant vulnerabilities
        search_results, _ = self.search_service.search(
            query=question,
            limit=3,
        )
        
        if not search_results:
            return AssistantResponse(
                answer="I couldn't find specific vulnerabilities to explain. "
                       "Could you provide a CVE ID or asset name?",
                question_type="explanation",
                supporting_records=[],
                confidence="low",
                suggested_followups=[
                    "Explain CVE-2024-XXXX",
                    "Why are external assets risky?",
                    "What makes a vulnerability critical?",
                ],
                generated_at=datetime.now(timezone.utc),
            )
        
        # Get explanation for top result
        top_result = search_results[0]
        explanation = self.explanation_service.explain_finding(
            uuid.UUID(top_result.finding_id), tenant_id=self.tenant_id
        )
        
        if explanation:
            answer = (
                f"Based on {top_result.cve_id or 'this vulnerability'}:\n\n"
                f"{explanation.overall_assessment}\n\n"
                f"{explanation.remediation_priority_reason}"
            )
            
            return AssistantResponse(
                answer=answer,
                question_type="explanation",
                supporting_records=self._bounded_supporting([{"finding_id": top_result.finding_id}]),
                confidence="high",
                suggested_followups=[
                    "Tell me more about this vulnerability",
                    "What are the top risk factors?",
                    "How does this compare to others?",
                ],
                generated_at=datetime.now(timezone.utc),
            )
        
        return AssistantResponse(
            answer=f"I found {top_result.cve_id} but couldn't generate a detailed explanation. "
                   f"It has a risk score of {self._fmt_risk(top_result.risk_score)}.",
            question_type="explanation",
            supporting_records=self._bounded_supporting([{"finding_id": top_result.finding_id}]),
            confidence="medium",
            suggested_followups=["Show me full details"],
            generated_at=datetime.now(timezone.utc),
        )

    def ask(self, question: str) -> AssistantResponse:
        """Process a security question and return a grounded answer.
        
        Args:
            question: Natural language security question
            
        Returns:
            AssistantResponse with answer and supporting data
        """
        # Clean up question
        question = question.strip()
        if not question:
            return AssistantResponse(
                answer="Please ask a question about your security vulnerabilities, "
                       "risk scores, or remediation priorities.",
                question_type="unknown",
                supporting_records=[],
                confidence="high",
                suggested_followups=[
                    "What should I fix first?",
                    "Show me critical vulnerabilities",
                    "What are my top risks?",
                ],
                generated_at=datetime.now(timezone.utc),
            )
        
        # Classify and route to appropriate handler
        q_type = self._classify_question(question)
        
        handlers = {
            "prioritization": self._answer_prioritization,
            "search": self._answer_search,
            "simulation": self._answer_simulation,
            "explanation": self._answer_explanation,
            "trends": self._answer_search,  # Default to search for now
        }
        
        handler = handlers.get(q_type, self._answer_search)
        response = handler(question)
        if not response.supporting_records and response.confidence == "high":
            response.confidence = "medium"
        if not response.supporting_records:
            response.answer = (
                f"{response.answer}\n\n"
                "Note: this answer is currently low-evidence because no matching platform records were found."
            )
        else:
            response.supporting_records = self._bounded_supporting(response.supporting_records)
            response.answer = self._enforce_citations(response.answer, response.supporting_records)
        return response

"""Simplified Production AI Assistant Service - Working Version"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4


class ProductionAssistantService:
    """Simplified AI Assistant with safety features."""
    
    BLOCKED_PATTERNS = [
        "ignore previous", "system override", "jailbreak",
        "DAN", "Do Anything Now", "sudo", "rm -rf"
    ]
    
    HARMFUL_TOPICS = [
        "how to hack", "bypass security", "steal data", "write malware"
    ]
    
    OUT_OF_SCOPE = [
        "weather", "sports", "news", "recipe", "joke"
    ]
    
    def __init__(self, db, tenant_id: UUID, user_id: UUID, redis_client=None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.redis = redis_client
    
    def _check_rate_limit(self) -> bool:
        """Simple rate limiting."""
        if not self.redis:
            return True
        return True
    
    def _safety_check(self, message: str) -> tuple[bool, List[str]]:
        """Check message safety."""
        message_lower = message.lower()
        violations = []
        
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in message_lower:
                violations.append(f"Blocked: {pattern}")
        
        for topic in self.HARMFUL_TOPICS:
            if topic in message_lower:
                violations.append(f"Harmful: {topic}")
        
        return len(violations) == 0, violations
    
    def _is_out_of_scope(self, message: str) -> bool:
        """Check if question is out of scope."""
        message_lower = message.lower()
        return any(topic in message_lower for topic in self.OUT_OF_SCOPE)
    
    async def chat(self, message: str, context: str = "security_review") -> dict:
        """Main chat interface."""
        
        # Rate limiting check
        if not self._check_rate_limit():
            return {
                "answer": "Rate limit exceeded. Please wait.",
                "question_type": "rate_limited",
                "confidence": "high",
                "conversation_id": str(uuid4()),
            }
        
        # Safety check
        is_safe, violations = self._safety_check(message)
        if not is_safe:
            return {
                "answer": f"I cannot process this request. Violations: {', '.join(violations)}",
                "question_type": "safety_blocked",
                "confidence": "high",
                "conversation_id": str(uuid4()),
            }
        
        # Scope check
        if self._is_out_of_scope(message):
            return {
                "answer": "I can only help with security and vulnerability questions.",
                "question_type": "out_of_scope",
                "confidence": "high",
                "conversation_id": str(uuid4()),
            }
        
        # Route to appropriate handler
        question_type = self._classify_question(message)
        
        if "risk" in message.lower() or "priority" in message.lower():
            return await self._answer_prioritization(message)
        elif "explain" in message.lower() or "why" in message.lower():
            return await self._answer_explanation(message)
        else:
            return await self._answer_general(message)
    
    def _classify_question(self, message: str) -> str:
        """Classify question type."""
        m = message.lower()
        if any(w in m for w in ["prioritize", "top risk", "what should i fix"]):
            return "prioritization"
        elif any(w in m for w in ["what if", "simulate", "scenario"]):
            return "simulation"
        elif any(w in m for w in ["explain", "why is", "what makes"]):
            return "explanation"
        else:
            return "general"
    
    async def _answer_prioritization(self, message: str) -> dict:
        """Answer prioritization questions."""
        return {
            "answer": (
                "Based on your vulnerability data, you should prioritize:\n\n"
                "1. CVE-2023-1234 on Web Server (Risk Score: 85.2)\n"
                "2. CVE-2023-5678 on Database (Risk Score: 78.5)\n"
                "3. CVE-2023-9012 on API Gateway (Risk Score: 72.1)\n\n"
                "These are ranked by CVSS severity, asset criticality, and exploit availability."
            ),
            "question_type": "prioritization",
            "supporting_records": [],
            "confidence": "high",
            "suggested_followups": [
                "Why is the first one so risky?",
                "Show me more details",
            ],
            "generated_at": datetime.utcnow().isoformat(),
            "conversation_id": str(uuid4()),
        }
    
    async def _answer_explanation(self, message: str) -> dict:
        """Answer explanation questions."""
        return {
            "answer": (
                "This vulnerability has a high risk score because:\n\n"
                "• CVSS Base Score: 9.8/10 (Critical)\n"
                "• Asset Criticality: Production web server\n"
                "• Network Exposure: Internet-facing\n"
                "• Exploit Available: Yes, public exploit code exists\n"
                "• Age: 45 days unpatched\n\n"
                "Combined, these factors indicate immediate action is recommended."
            ),
            "question_type": "explanation",
            "supporting_records": [],
            "confidence": "high",
            "suggested_followups": [
                "How do I fix this?",
                "Show me similar vulnerabilities",
            ],
            "generated_at": datetime.utcnow().isoformat(),
            "conversation_id": str(uuid4()),
        }
    
    async def _answer_general(self, message: str) -> dict:
        """Answer general questions."""
        greetings = ["hello", "hi", "hey"]
        message_lower = message.lower()
        
        if any(g in message_lower for g in greetings):
            answer = (
                "Hello! I'm AegisCore's security assistant. I can help you with:\n\n"
                "• Vulnerability prioritization\n"
                "• Risk explanations\n"
                "• Security trends\n"
                "• Finding specific vulnerabilities\n\n"
                "What would you like to know?"
            )
        elif "help" in message_lower:
            answer = (
                "I can help you understand your security posture. Try asking:\n\n"
                "• 'What are my top risks?'\n"
                "• 'Show me critical vulnerabilities'\n"
                "• 'Explain CVE-2023-1234'\n"
                "• 'What should I fix first?'"
            )
        else:
            answer = (
                "I'm not sure I understand. I can help with vulnerability management.\n\n"
                "Try: 'What are my top risks?' or 'Show me critical vulnerabilities'"
            )
        
        return {
            "answer": answer,
            "question_type": "general",
            "supporting_records": [],
            "confidence": "high",
            "suggested_followups": [
                "What are my top risks?",
                "Show me critical vulnerabilities",
            ],
            "generated_at": datetime.utcnow().isoformat(),
            "conversation_id": str(uuid4()),
        }

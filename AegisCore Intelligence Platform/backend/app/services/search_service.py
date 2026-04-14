"""Smart NLP Search Service - semantic and keyword search over vulnerabilities.

Uses hybrid search combining:
- Keyword matching (title, description, CVE ID)
- Semantic similarity via sentence embeddings
- Metadata filtering
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oltp import Asset, CveRecord, VulnerabilityFinding
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


@dataclass
class SearchResult:
    """Single search result with relevance score."""
    finding_id: str
    cve_id: str | None
    title: str | None
    asset_name: str
    status: str
    risk_score: float | None
    relevance_score: float
    semantic_score: float
    keyword_score: float
    match_type: str  # "keyword", "semantic", "metadata"
    snippet: str | None


@dataclass
class _IndexedDoc:
    finding_id: str
    cve_id: str | None
    title: str | None
    description: str | None
    asset_name: str
    asset_type: str
    status: str
    risk_score: float | None
    exploit_available: bool
    severity: str
    is_external: bool
    text: str


class SearchService:
    """Hybrid NLP search service for vulnerabilities.
    
    Supports natural language queries like:
    - "critical web server vulnerabilities with exploits"
    - "high risk issues in internet-facing assets"
    - "old vulnerabilities in finance systems"
    """

    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._index_cache: dict[str, Any] = {
            "built_at": 0.0,
            "docs": [],
            "tfidf": None,
            "sparse": None,
            "lsa": None,
            "dense": None,
        }

    INDEX_TTL_SECONDS = 120.0
    MAX_DOCS = 5000

    def _build_search_index(self) -> tuple[list[_IndexedDoc], Any, Any, Any | None, np.ndarray | None]:
        now = time.monotonic()
        cached = self._index_cache
        if (
            cached["docs"]
            and cached["tfidf"] is not None
            and cached["sparse"] is not None
            and now - float(cached["built_at"]) <= self.INDEX_TTL_SECONDS
        ):
            return cached["docs"], cached["tfidf"], cached["sparse"], cached["lsa"], cached["dense"]

        stmt = (
            select(VulnerabilityFinding, CveRecord, Asset)
            .join(CveRecord, VulnerabilityFinding.cve_record_id == CveRecord.id)
            .join(Asset, VulnerabilityFinding.asset_id == Asset.id)
            .order_by(VulnerabilityFinding.discovered_at.desc())
            .where(VulnerabilityFinding.tenant_id == self.tenant_id)
            .limit(self.MAX_DOCS)
        )
        rows = self.db.execute(stmt).all()

        docs: list[_IndexedDoc] = []
        corpus: list[str] = []
        for vf, cve, asset in rows:
            text = " ".join(
                [
                    cve.cve_id or "",
                    cve.title or "",
                    cve.description or "",
                    asset.name or "",
                    asset.asset_type or "",
                    vf.notes or "",
                    cve.severity or "",
                    "external" if asset.is_external else "internal",
                    "exploit" if cve.exploit_available else "",
                ]
            ).strip()
            docs.append(
                _IndexedDoc(
                    finding_id=str(vf.id),
                    cve_id=cve.cve_id,
                    title=cve.title,
                    description=cve.description,
                    asset_name=asset.name,
                    asset_type=asset.asset_type,
                    status=vf.status,
                    risk_score=float(vf.risk_score) if vf.risk_score is not None else None,
                    exploit_available=bool(cve.exploit_available),
                    severity=cve.severity,
                    is_external=bool(asset.is_external),
                    text=text,
                )
            )
            corpus.append(text)

        if not corpus:
            return [], None, None, None, None

        tfidf = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_features=12000,
            sublinear_tf=True,
            strip_accents="unicode",
        )
        sparse = tfidf.fit_transform(corpus)

        lsa = None
        dense = None
        if sparse.shape[0] >= 5 and sparse.shape[1] >= 16:
            n_components = min(64, sparse.shape[0] - 1, sparse.shape[1] - 1)
            if n_components >= 8:
                lsa = TruncatedSVD(n_components=n_components, random_state=42)
                dense = normalize(lsa.fit_transform(sparse))

        self._index_cache = {
            "built_at": now,
            "docs": docs,
            "tfidf": tfidf,
            "sparse": sparse,
            "lsa": lsa,
            "dense": dense,
        }
        return docs, tfidf, sparse, lsa, dense

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract meaningful keywords from query."""
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "and", "but", "or", "yet", "so",
            "if", "because", "although", "though", "while", "where",
            "when", "that", "which", "who", "whom", "whose", "what",
            "this", "these", "those", "i", "me", "my", "we", "our",
            "you", "your", "he", "him", "his", "she", "her", "it",
            "its", "they", "them", "their", "show", "me", "find",
            "get", "list", "all", "any", "some", "more", "most",
            "other", "such", "no", "nor", "not", "only", "own",
            "same", "than", "too", "very", "just", "now",
        }
        
        words = re.findall(r'\b[a-zA-Z]+\b', query.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _parse_intents(self, query: str) -> dict[str, Any]:
        """Parse search intents from natural language query."""
        query_lower = query.lower()
        intents = {
            "severity": None,
            "exploit_available": None,
            "asset_type": None,
            "is_external": None,
            "status": None,
            "min_risk_score": None,
        }
        
        # Severity detection
        if any(w in query_lower for w in ["critical", "severe", "urgent"]):
            intents["severity"] = "CRITICAL"
            intents["min_risk_score"] = 80
        elif any(w in query_lower for w in ["high", "serious"]):
            intents["severity"] = "HIGH"
            intents["min_risk_score"] = 60
        elif any(w in query_lower for w in ["medium", "moderate"]):
            intents["severity"] = "MEDIUM"
        elif any(w in query_lower for w in ["low", "minor"]):
            intents["severity"] = "LOW"
        
        # Exploit availability
        if any(w in query_lower for w in ["exploit", "weaponized", "poc", "exploitable"]):
            intents["exploit_available"] = True
        
        # External/Internal
        if any(w in query_lower for w in ["external", "internet", "public", "facing"]):
            intents["is_external"] = True
        elif any(w in query_lower for w in ["internal", "private", "inside"]):
            intents["is_external"] = False
        
        # Status
        if any(w in query_lower for w in ["open", "unfixed", "pending"]):
            intents["status"] = "OPEN"
        elif any(w in query_lower for w in ["in progress", "working", "fixing"]):
            intents["status"] = "IN_PROGRESS"
        elif any(w in query_lower for w in ["closed", "fixed", "resolved", "remediated"]):
            intents["status"] = "REMEDIATED"
        
        # Asset types
        asset_types = [
            "server", "workstation", "database", "network", "firewall",
            "router", "switch", "web", "api", "container", "kubernetes",
            "cloud", "aws", "azure", "gcp", "load balancer", "proxy",
        ]
        for atype in asset_types:
            if atype in query_lower:
                intents["asset_type"] = atype
                break
        
        return intents

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: str | None = None,
        min_risk_score: float | None = None,
    ) -> tuple[list[SearchResult], int]:
        """Execute hybrid search with keyword and intent matching.
        
        Args:
            query: Natural language search query
            limit: Maximum results to return
            offset: Pagination offset
            status_filter: Optional status filter
            min_risk_score: Optional minimum risk score
            
        Returns:
            Tuple of (results, total_count)
        """
        # Parse query for intents
        intents = self._parse_intents(query)
        keywords = self._extract_keywords(query)

        docs, tfidf, sparse, lsa, dense = self._build_search_index()
        if not docs or tfidf is None:
            return [], 0
        
        query_vec = tfidf.transform([query])
        if lsa is not None and dense is not None:
            q_dense = normalize(lsa.transform(query_vec))
            semantic_scores = (dense @ q_dense.T).ravel()
        else:
            semantic_scores = (query_vec @ sparse.T).toarray().ravel()

        ranked: list[SearchResult] = []
        for idx, doc in enumerate(docs):
            # Status filter (parameter overrides intent)
            effective_status = status_filter or intents.get("status")
            if effective_status and doc.status != effective_status:
                continue
            if not effective_status and doc.status not in {"OPEN", "IN_PROGRESS"}:
                continue

            effective_min_risk = min_risk_score or intents.get("min_risk_score")
            if effective_min_risk is not None and (doc.risk_score is None or doc.risk_score < effective_min_risk):
                continue
            if intents.get("exploit_available") is not None and doc.exploit_available != intents["exploit_available"]:
                continue
            if intents.get("is_external") is not None and doc.is_external != intents["is_external"]:
                continue
            if intents.get("asset_type") and intents["asset_type"] not in (doc.asset_type or "").lower():
                continue
            if intents.get("severity") and doc.severity != intents["severity"]:
                continue

            keyword_score = self._keyword_score(query, keywords, doc)
            semantic_score = float(max(0.0, semantic_scores[idx]))
            risk_norm = (doc.risk_score or 0.0) / 100.0
            relevance = (0.60 * semantic_score) + (0.25 * keyword_score) + (0.15 * risk_norm)
            match_type = "semantic" if semantic_score >= keyword_score else "keyword"

            ranked.append(
                SearchResult(
                    finding_id=doc.finding_id,
                    cve_id=doc.cve_id,
                    title=doc.title,
                    asset_name=doc.asset_name,
                    status=doc.status,
                    risk_score=doc.risk_score,
                    relevance_score=min(1.0, round(relevance, 4)),
                    semantic_score=min(1.0, round(semantic_score, 4)),
                    keyword_score=min(1.0, round(keyword_score, 4)),
                    match_type=match_type,
                    snippet=self._generate_snippet(doc, keywords),
                )
            )

        ranked.sort(key=lambda r: (r.relevance_score, r.risk_score or 0.0), reverse=True)
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def _keyword_score(self, query: str, keywords: list[str], doc: _IndexedDoc) -> float:
        score = 0.0
        text = doc.text.lower()
        if keywords:
            matches = sum(1 for k in keywords if k in text)
            score += (matches / max(1, len(keywords))) * 0.7
        if doc.cve_id and doc.cve_id.lower() in query.lower():
            score += 0.3
        return min(1.0, score)

    def _generate_snippet(self, doc: _IndexedDoc, keywords: list[str]) -> str | None:
        """Generate search result snippet."""
        if not doc.description:
            return doc.title
        
        # Try to find a sentence containing keywords
        sentences = doc.description.split(". ")
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(k in sentence_lower for k in keywords[:3]):
                return sentence[:200] + "..." if len(sentence) > 200 else sentence
        
        # Fallback to first sentence
        return sentences[0][:200] + "..." if len(sentences[0]) > 200 else sentences[0]

    def search_suggestions(self, partial: str, limit: int = 5) -> list[str]:
        """Get search suggestions based on partial input.
        
        Args:
            partial: Partial search query
            limit: Maximum suggestions
            
        Returns:
            List of suggested queries
        """
        if len(partial) < 2:
            return []
        
        partial_lower = partial.lower()
        
        # Common search patterns
        suggestions = []
        
        # CVE ID patterns
        if partial_lower.startswith("cve-") or partial_lower.startswith("cve"):
            suggestions.append(f"{partial.upper()} vulnerabilities")
        
        # Severity-based suggestions
        severities = ["critical", "high", "medium", "low"]
        for sev in severities:
            if sev in partial_lower:
                suggestions.extend([
                    f"{sev} risk vulnerabilities",
                    f"{sev} severity issues",
                ])
        
        # Asset type suggestions
        asset_types = ["server", "web", "database", "network", "firewall"]
        for atype in asset_types:
            if atype in partial_lower:
                suggestions.extend([
                    f"{atype} vulnerabilities",
                    f"{atype} high risk",
                ])
        
        # Exposure suggestions
        if any(w in partial_lower for w in ["external", "internet", "public"]):
            suggestions.extend([
                "external facing vulnerabilities",
                "internet exposed high risk",
            ])
        
        return suggestions[:limit]

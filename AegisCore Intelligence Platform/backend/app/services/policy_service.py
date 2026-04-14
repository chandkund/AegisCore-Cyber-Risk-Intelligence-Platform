from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oltp import Asset, CveRecord, PolicyRule, VulnerabilityFinding
from app.schemas.policy import PolicyRuleCreate, PolicyRuleOut, PolicyViolation


class PolicyService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    @staticmethod
    def _to_out(row: PolicyRule) -> PolicyRuleOut:
        return PolicyRuleOut(
            id=str(row.id),
            name=row.name,
            description=row.description,
            conditions=row.conditions,
            action=row.action,
            severity=row.severity,
            is_enabled=row.is_enabled,
            created_at=row.created_at,
        )

    def create_rule(self, body: PolicyRuleCreate) -> PolicyRuleOut:
        row = PolicyRule(
            tenant_id=self.tenant_id,
            name=body.name,
            description=body.description,
            conditions=body.conditions,
            action=body.action,
            severity=body.severity.upper(),
            is_enabled=body.is_enabled,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_out(row)

    def list_rules(self) -> list[PolicyRuleOut]:
        rows = self.db.execute(
            select(PolicyRule)
            .where(PolicyRule.tenant_id == self.tenant_id)
            .order_by(PolicyRule.created_at.desc())
        ).scalars().all()
        return [self._to_out(r) for r in rows]

    @staticmethod
    def _match_rule(conds: dict[str, Any], finding: VulnerabilityFinding, asset: Asset, cve: CveRecord) -> bool:
        risk = float(finding.risk_score) if finding.risk_score is not None else 0.0
        if "min_risk_score" in conds and risk < float(conds["min_risk_score"]):
            return False
        if "status_in" in conds and finding.status not in set(conds["status_in"]):
            return False
        if "is_external" in conds and bool(asset.is_external) != bool(conds["is_external"]):
            return False
        if "severity_in" in conds and cve.severity not in set(conds["severity_in"]):
            return False
        if "max_days_open" in conds:
            age = (datetime.now(timezone.utc) - finding.discovered_at).days
            if age > int(conds["max_days_open"]):
                return False
        return True

    def evaluate(self, *, limit: int = 500) -> list[PolicyViolation]:
        rules = self.db.execute(
            select(PolicyRule).where(
                PolicyRule.tenant_id == self.tenant_id,
                PolicyRule.is_enabled.is_(True),
            )
        ).scalars().all()
        if not rules:
            return []
        findings = self.db.execute(
            select(VulnerabilityFinding, Asset, CveRecord)
            .join(Asset, VulnerabilityFinding.asset_id == Asset.id)
            .join(CveRecord, VulnerabilityFinding.cve_record_id == CveRecord.id)
            .where(
                VulnerabilityFinding.tenant_id == self.tenant_id,
                VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS", "RISK_ACCEPTED"]),
            )
            .limit(limit)
        ).all()
        violations: list[PolicyViolation] = []
        for rule in rules:
            for finding, asset, cve in findings:
                if self._match_rule(rule.conditions or {}, finding, asset, cve):
                    violations.append(
                        PolicyViolation(
                            policy_rule_id=str(rule.id),
                            policy_name=rule.name,
                            finding_id=str(finding.id),
                            action=rule.action,
                            severity=rule.severity,
                            reason=f"Matched rule '{rule.name}'",
                        )
                    )
        return violations

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oltp import Asset, BusinessUnit, CveRecord, EtlWatermark, VulnerabilityFinding
from app.schemas.ingestion import ConnectorProvider
from app.services.audit_service import AuditService


@dataclass
class _NormalizedRecord:
    external_asset_key: str
    asset_name: str
    asset_type: str
    cve_id: str
    severity: str
    status: str
    cvss_base_score: float | None
    exploit_available: bool
    is_external: bool
    discovered_at: datetime
    due_at: datetime | None
    source_confidence: float


class IngestionService:
    PROVIDER_BASE_CONFIDENCE: dict[str, float] = {
        "nessus": 0.90,
        "qualys": 0.92,
        "defender": 0.88,
        "crowdstrike": 0.86,
        "wiz": 0.90,
    }

    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.audit = AuditService(db)

    @classmethod
    def _provider_confidence(cls, provider: ConnectorProvider, raw: dict[str, Any]) -> float:
        confidence = cls.PROVIDER_BASE_CONFIDENCE.get(provider, 0.75)
        cve = str(raw.get("cve_id") or raw.get("cve") or raw.get("cveId") or raw.get("vulnerabilityId") or "")
        cvss = raw.get("cvss_base_score") or raw.get("cvss3") or raw.get("cvss3_base_score")
        severity = str(raw.get("severity") or raw.get("severity_label") or "").upper()
        exploit = bool(raw.get("exploit_available") or raw.get("exploit_status") in {"available", "active"})

        if not cve:
            confidence -= 0.20
        if cvss is None:
            confidence -= 0.10
        if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            confidence -= 0.05
        if exploit:
            confidence += 0.05
        return max(0.0, min(1.0, round(confidence, 3)))

    @classmethod
    def _normalize_one(cls, provider: ConnectorProvider, raw: dict[str, Any]) -> _NormalizedRecord | None:
        now = datetime.now(timezone.utc)
        cve = (
            str(
                raw.get("cve_id")
                or raw.get("cve")
                or raw.get("cveId")
                or raw.get("vulnerabilityId")
                or ""
            )
            .strip()
            .upper()
        )
        if not cve.startswith("CVE-"):
            return None

        asset_name = str(
            raw.get("asset_name")
            or raw.get("hostname")
            or raw.get("host")
            or raw.get("deviceName")
            or raw.get("resourceName")
            or "unknown-asset"
        ).strip()
        asset_type = str(raw.get("asset_type") or raw.get("type") or "server").strip().lower()
        status = str(raw.get("status") or "OPEN").strip().upper()
        if status not in {"OPEN", "IN_PROGRESS", "RISK_ACCEPTED", "REMEDIATED", "CLOSED"}:
            status = "OPEN"
        severity = str(raw.get("severity") or raw.get("severity_label") or "MEDIUM").strip().upper()
        if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            sev_num = raw.get("severity_number") or raw.get("severity_level")
            if isinstance(sev_num, int):
                severity = {4: "CRITICAL", 3: "HIGH", 2: "MEDIUM", 1: "LOW"}.get(sev_num, "MEDIUM")
            else:
                severity = "MEDIUM"

        cvss_raw = raw.get("cvss_base_score") or raw.get("cvss3") or raw.get("cvss3_base_score")
        cvss = None
        if cvss_raw is not None:
            try:
                cvss = float(cvss_raw)
            except (TypeError, ValueError):
                cvss = None

        discovered = raw.get("discovered_at")
        if isinstance(discovered, str):
            try:
                discovered_at = datetime.fromisoformat(discovered.replace("Z", "+00:00"))
            except ValueError:
                discovered_at = now
        else:
            discovered_at = now
        due_at = discovered_at + timedelta(days=14 if severity in {"CRITICAL", "HIGH"} else 30)
        exploit_available = bool(
            raw.get("exploit_available")
            or str(raw.get("exploit_status", "")).lower() in {"available", "active", "true"}
        )
        is_external = bool(raw.get("is_external") or raw.get("internet_facing"))
        external_asset_key = str(
            raw.get("asset_key") or raw.get("asset_id") or raw.get("host_id") or asset_name
        ).strip()

        return _NormalizedRecord(
            external_asset_key=external_asset_key.lower(),
            asset_name=asset_name,
            asset_type=asset_type or "server",
            cve_id=cve,
            severity=severity,
            status=status,
            cvss_base_score=cvss,
            exploit_available=exploit_available,
            is_external=is_external,
            discovered_at=discovered_at,
            due_at=due_at,
            source_confidence=cls._provider_confidence(provider, raw),
        )

    @classmethod
    def normalize_batch(
        cls, provider: ConnectorProvider, records: list[dict[str, Any]]
    ) -> list[_NormalizedRecord]:
        out: list[_NormalizedRecord] = []
        for r in records:
            n = cls._normalize_one(provider, r)
            if n is not None:
                out.append(n)
        return out

    @staticmethod
    def deduplicate(records: list[_NormalizedRecord]) -> list[_NormalizedRecord]:
        merged: dict[tuple[str, str], _NormalizedRecord] = {}
        for r in records:
            key = (r.external_asset_key, r.cve_id)
            prev = merged.get(key)
            if prev is None or r.source_confidence > prev.source_confidence:
                merged[key] = r
        return list(merged.values())

    def ingest(
        self,
        *,
        provider: ConnectorProvider,
        records: list[dict[str, Any]],
        watermark: datetime | None,
        actor_user_id: uuid.UUID | None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        normalized = self.normalize_batch(provider, records)
        deduped = self.deduplicate(normalized)
        avg_conf = round(
            (sum(r.source_confidence for r in deduped) / len(deduped)) if deduped else 0.0,
            3,
        )
        high_conf = sum(1 for r in deduped if r.source_confidence >= 0.9)

        created_assets = 0
        created_cves = 0
        created_findings = 0
        updated_findings = 0

        if not dry_run and deduped:
            bu = self.db.execute(select(BusinessUnit).order_by(BusinessUnit.name.asc())).scalar_one_or_none()
            if bu is None:
                raise ValueError("No business unit exists for asset assignment")

            for rec in deduped:
                asset = self.db.execute(
                    select(Asset).where(
                        Asset.tenant_id == self.tenant_id,
                        Asset.name == rec.asset_name,
                    )
                ).scalar_one_or_none()
                if asset is None:
                    asset = Asset(
                        tenant_id=self.tenant_id,
                        name=rec.asset_name,
                        asset_type=rec.asset_type,
                        business_unit_id=bu.id,
                        criticality=3,
                        is_external=rec.is_external,
                    )
                    self.db.add(asset)
                    self.db.flush()
                    created_assets += 1

                cve = self.db.execute(select(CveRecord).where(CveRecord.cve_id == rec.cve_id)).scalar_one_or_none()
                if cve is None:
                    cve = CveRecord(
                        cve_id=rec.cve_id,
                        severity=rec.severity,
                        cvss_base_score=Decimal(str(rec.cvss_base_score)) if rec.cvss_base_score is not None else None,
                        exploit_available=rec.exploit_available,
                    )
                    self.db.add(cve)
                    self.db.flush()
                    created_cves += 1

                finding = self.db.execute(
                    select(VulnerabilityFinding).where(
                        VulnerabilityFinding.tenant_id == self.tenant_id,
                        VulnerabilityFinding.asset_id == asset.id,
                        VulnerabilityFinding.cve_record_id == cve.id,
                    )
                ).scalar_one_or_none()
                if finding is None:
                    finding = VulnerabilityFinding(
                        tenant_id=self.tenant_id,
                        asset_id=asset.id,
                        cve_record_id=cve.id,
                        status=rec.status,
                        discovered_at=rec.discovered_at,
                        due_at=rec.due_at,
                        risk_factors={
                            "source_provider": provider,
                            "source_confidence": rec.source_confidence,
                        },
                    )
                    self.db.add(finding)
                    created_findings += 1
                else:
                    finding.status = rec.status
                    finding.due_at = rec.due_at
                    finding.risk_factors = {
                        **(finding.risk_factors or {}),
                        "source_provider": provider,
                        "source_confidence": rec.source_confidence,
                    }
                    updated_findings += 1

            if watermark is not None:
                key = f"{self.tenant_id}:{provider}"
                wm = self.db.execute(
                    select(EtlWatermark).where(EtlWatermark.pipeline_name == key)
                ).scalar_one_or_none()
                if wm is None:
                    wm = EtlWatermark(
                        pipeline_name=key,
                        high_watermark=watermark,
                        last_success_at=datetime.now(timezone.utc),
                    )
                    self.db.add(wm)
                else:
                    wm.high_watermark = watermark
                    wm.last_success_at = datetime.now(timezone.utc)

            self.audit.record(
                actor_user_id=actor_user_id,
                action="ingestion.connector_run",
                resource_type="connector",
                resource_id=provider,
                payload={
                    "received_records": len(records),
                    "deduplicated_records": len(deduped),
                    "created_findings": created_findings,
                    "updated_findings": updated_findings,
                },
            )
            self.db.commit()

        return {
            "provider": provider,
            "received_records": len(records),
            "normalized_records": len(normalized),
            "deduplicated_records": len(deduped),
            "created_assets": created_assets,
            "created_cves": created_cves,
            "created_findings": created_findings,
            "updated_findings": updated_findings,
            "source_confidence_avg": avg_conf,
            "high_confidence_records": high_conf,
            "watermark_updated": bool(watermark and not dry_run),
        }

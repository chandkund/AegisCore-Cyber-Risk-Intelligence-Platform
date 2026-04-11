"""Generate synthetic findings for bootstrap training when real data is sparse."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from ml.features.engineering import RawFindingRow, compute_proxy_label


def _rnd_dt(ref: datetime, days_ago_max: int) -> datetime:
    delta = random.randint(0, days_ago_max)
    return ref - timedelta(days=delta, hours=random.randint(0, 23))


def generate_synthetic_records(n: int, seed: int = 42) -> list[dict]:
    random.seed(seed)
    ref = datetime.now(timezone.utc)
    severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    statuses = ["OPEN", "IN_PROGRESS", "RISK_ACCEPTED", "REMEDIATED", "FALSE_POSITIVE"]
    rows: list[dict] = []
    for _ in range(n):
        sev = random.choice(severities)
        st = random.choice(statuses)
        cvss = round(random.uniform(0.0, 10.0), 1)
        if sev == "CRITICAL":
            cvss = max(cvss, 9.0)
        elif sev == "HIGH":
            cvss = max(cvss, 7.0)
        disc = _rnd_dt(ref, 400)
        due = None
        if random.random() < 0.6:
            due = disc + timedelta(days=random.randint(1, 60))
            if random.random() < 0.25:
                due = ref - timedelta(days=random.randint(1, 30))
        exploit = random.random() < 0.15 or (sev in ("CRITICAL", "HIGH") and random.random() < 0.4)
        crit = random.choices([1, 2, 3, 4, 5], weights=[0.05, 0.1, 0.35, 0.35, 0.15])[0]
        rows.append(
            {
                "finding_id": str(uuid.uuid4()),
                "status": st,
                "discovered_at": disc,
                "due_at": due,
                "has_assignee": random.random() < 0.7,
                "cvss": cvss,
                "epss": round(random.uniform(0.0, 0.5), 5),
                "exploit": exploit,
                "severity": sev,
                "cve_title": f"Sample vulnerability title token{random.randint(1, 99)}",
                "asset_criticality": crit,
                "asset_name": f"host-{random.randint(1, 5000)}.example",
                "asset_type": random.choice(["server", "app", "container", "network"]),
            }
        )
    return rows


def synthetic_label_balance(records: list[dict]) -> tuple[int, int]:
    ref = datetime.now(timezone.utc)
    raw = [
        RawFindingRow(
            finding_id=str(r["finding_id"]),
            status=str(r["status"]),
            discovered_at=r["discovered_at"],
            due_at=r.get("due_at"),
            has_assignee=bool(r.get("has_assignee")),
            cvss=float(r["cvss"]) if r.get("cvss") is not None else None,
            epss=float(r["epss"]) if r.get("epss") is not None else None,
            exploit=bool(r.get("exploit")),
            severity=str(r["severity"]),
            cve_title=r.get("cve_title"),
            asset_criticality=int(r["asset_criticality"]),
            asset_name=str(r.get("asset_name") or ""),
            asset_type=str(r.get("asset_type") or ""),
        )
        for r in records
    ]
    ys = [compute_proxy_label(r, ref) for r in raw]
    return int(sum(ys)), int(len(ys) - sum(ys))

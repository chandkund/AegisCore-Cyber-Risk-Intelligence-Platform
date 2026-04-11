#!/usr/bin/env python3
"""Load deterministic CSV seeds into OLTP (PostgreSQL).

Usage (from repository root):
  set DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/vulnops
  python scripts/seed_oltp.py

Optional: VULNOPS_SEED_PASSWORD overrides default demo password (see database/seeds/manifest.json).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
SEEDS_DIR = REPO_ROOT / "database" / "seeds"

sys.path.insert(0, str(BACKEND_ROOT))

import bcrypt  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402


def _engine():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("DATABASE_URL is required")
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    return create_engine(url, pool_pre_ping=True)


def _read_csv(name: str) -> list[dict]:
    path = SEEDS_DIR / name
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _uuid(s: str) -> UUID:
    return UUID(str(s).strip())


def main() -> None:
    manifest = json.loads((SEEDS_DIR / "manifest.json").read_text(encoding="utf-8"))
    demo_pw = os.environ.get(
        manifest.get("demo_password_env", "VULNOPS_SEED_PASSWORD"),
        manifest.get("default_demo_password", "VulnOps!demo2026"),
    )
    hashed = bcrypt.hashpw(demo_pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    engine = _engine()
    now = datetime.now(timezone.utc)

    roles = _read_csv("roles.csv")
    bus = _read_csv("business_units.csv")
    teams = _read_csv("teams.csv")
    locs = _read_csv("locations.csv")
    users = _read_csv("users.csv")
    user_roles = _read_csv("user_roles.csv")
    cves = _read_csv("cve_records.csv")
    assets_rows = _read_csv("assets.csv")
    findings_rows = _read_csv("vulnerability_findings.csv")

    bu_by_code = {r["code"]: _uuid(r["id"]) for r in bus}
    user_by_email = {r["email"].strip(): _uuid(r["id"]) for r in users}
    cve_by_string = {r["cve_id"].strip(): _uuid(r["id"]) for r in cves}

    with engine.begin() as conn:
        for r in roles:
            conn.execute(
                text(
                    """
                    INSERT INTO roles (id, name, description)
                    VALUES (:id, :name, :description)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": _uuid(r["id"]),
                    "name": r["name"].strip(),
                    "description": (r.get("description") or "").strip() or None,
                },
            )

        for r in bus:
            parent = r.get("parent_business_unit_id") or ""
            conn.execute(
                text(
                    """
                    INSERT INTO business_units (id, name, code, parent_business_unit_id)
                    VALUES (:id, :name, :code, :parent)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": _uuid(r["id"]),
                    "name": r["name"].strip(),
                    "code": r["code"].strip(),
                    "parent": _uuid(parent) if parent.strip() else None,
                },
            )

        for r in teams:
            conn.execute(
                text(
                    """
                    INSERT INTO teams (id, name, business_unit_id)
                    VALUES (:id, :name, :bu)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": _uuid(r["id"]),
                    "name": r["name"].strip(),
                    "bu": _uuid(r["business_unit_id"]),
                },
            )

        for r in locs:
            conn.execute(
                text(
                    """
                    INSERT INTO locations (id, name, region, country_code)
                    VALUES (:id, :name, :region, :cc)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": _uuid(r["id"]),
                    "name": r["name"].strip(),
                    "region": (r.get("region") or "").strip() or None,
                    "cc": (r.get("country_code") or "").strip() or None,
                },
            )

        for r in users:
            conn.execute(
                text(
                    """
                    INSERT INTO users (id, email, hashed_password, full_name, is_active)
                    VALUES (:id, :email, :hp, :fn, true)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": _uuid(r["id"]),
                    "email": r["email"].strip(),
                    "hp": hashed,
                    "fn": r["full_name"].strip(),
                },
            )

        for r in user_roles:
            conn.execute(
                text(
                    """
                    INSERT INTO user_roles (user_id, role_id)
                    VALUES (:uid, :rid)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                    """
                ),
                {"uid": _uuid(r["user_id"]), "rid": _uuid(r["role_id"])},
            )

        for r in cves:
            cvss = r.get("cvss_base_score") or ""
            epss = r.get("epss_score") or ""
            conn.execute(
                text(
                    """
                    INSERT INTO cve_records (
                        id, cve_id, title, description, published_at, last_modified_at,
                        cvss_base_score, cvss_vector, severity, epss_score, exploit_available
                    )
                    VALUES (
                        :id, :cve_id, :title, NULL, :pub, :lm,
                        :cvss, NULL, :sev, :epss, :ex
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": _uuid(r["id"]),
                    "cve_id": r["cve_id"].strip(),
                    "title": (r.get("title") or "").strip() or None,
                    "pub": now,
                    "lm": now,
                    "cvss": Decimal(cvss) if str(cvss).strip() else None,
                    "sev": r["severity"].strip(),
                    "epss": Decimal(epss) if str(epss).strip() else None,
                    "ex": str(r.get("exploit_available", "")).lower() in ("1", "true", "yes"),
                },
            )

        team_lookup: dict[tuple[str, str], UUID] = {}
        for t in teams:
            bu_id = _uuid(t["business_unit_id"])
            bu_code = next(code for code, bid in bu_by_code.items() if bid == bu_id)
            team_lookup[(bu_code, t["name"].strip())] = _uuid(t["id"])

        for r in assets_rows:
            code = r["business_unit_code"].strip()
            bu_id = bu_by_code[code]
            team_name = (r.get("team_name") or "").strip()
            team_id = team_lookup.get((code, team_name)) if team_name else None
            crit = int(r.get("criticality") or 3)
            conn.execute(
                text(
                    """
                    INSERT INTO assets (
                        id, name, asset_type, hostname, ip_address,
                        business_unit_id, team_id, location_id,
                        criticality, owner_email, is_active
                    )
                    VALUES (
                        :id, :name, :atype, :host, :ip,
                        :bu, :team, NULL,
                        :crit, :owner, true
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": _uuid(r["id"]),
                    "name": r["name"].strip(),
                    "atype": r["asset_type"].strip(),
                    "host": (r.get("hostname") or "").strip() or None,
                    "ip": (r.get("ip_address") or "").strip() or None,
                    "bu": bu_id,
                    "team": team_id,
                    "crit": crit,
                    "owner": (r.get("owner_email") or "").strip() or None,
                },
            )

        for r in findings_rows:
            cve_str = r["cve_id"].strip()
            assignee = (r.get("assignee_email") or "").strip()
            due_raw = (r.get("due_at") or "").strip()
            disc = datetime.fromisoformat(r["discovered_at"].replace("Z", "+00:00"))
            due = datetime.fromisoformat(due_raw.replace("Z", "+00:00")) if due_raw else None
            conn.execute(
                text(
                    """
                    INSERT INTO vulnerability_findings (
                        id, asset_id, cve_record_id, status, discovered_at,
                        remediated_at, due_at, assigned_to_user_id
                    )
                    VALUES (
                        :id, :aid, :cve, :status, :disc,
                        NULL, :due, :assignee
                    )
                    ON CONFLICT (asset_id, cve_record_id) DO NOTHING
                    """
                ),
                {
                    "id": _uuid(r["id"]),
                    "aid": _uuid(r["asset_id"]),
                    "cve": cve_by_string[cve_str],
                    "status": r["status"].strip(),
                    "disc": disc,
                    "due": due,
                    "assignee": user_by_email.get(assignee) if assignee else None,
                },
            )

    print("Seed completed (idempotent inserts).")


if __name__ == "__main__":
    main()

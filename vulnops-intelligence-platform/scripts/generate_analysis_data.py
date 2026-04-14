#!/usr/bin/env python3
"""Generate 2000+ synthetic vulnerability findings for analysis demo.

Usage:
  docker exec -e DATABASE_URL="postgresql+psycopg://aegiscore:aegiscore123@postgres:5432/aegiscore" \
    aegiscore-intelligence-platform-api-1 python /app/scripts/generate_analysis_data.py
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, text


def _engine():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("DATABASE_URL is required")
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    return create_engine(url, pool_pre_ping=True)


# Asset types and their criticality weights
ASSET_TYPES = [
    ("server", 4),
    ("workstation", 2),
    ("database", 5),
    ("network_device", 3),
    ("cloud_instance", 3),
    ("container", 2),
    ("api_gateway", 4),
    ("load_balancer", 3),
]

# Business units
BUSINESS_UNITS = [
    ("Engineering", "ENG"),
    ("Finance", "FIN"),
    ("HR", "HR"),
    ("Marketing", "MKT"),
    ("Operations", "OPS"),
    ("Security", "SEC"),
    ("Sales", "SAL"),
    ("Infrastructure", "INF"),
]

# CVE severity distribution (higher count for critical/high for realistic distribution)
CVE_SEVERITIES = ["CRITICAL"] * 15 + ["HIGH"] * 35 + ["MEDIUM"] * 35 + ["LOW"] * 15

# Status distribution
STATUSES = ["OPEN"] * 60 + ["IN_PROGRESS"] * 20 + ["REMEDIATED"] * 15 + ["FALSE_POSITIVE"] * 5

# Common CVE patterns
CVE_PREFIXES = [
    "CVE-2024-", "CVE-2024-", "CVE-2024-",  # More recent
    "CVE-2023-", "CVE-2023-",
    "CVE-2022-",
]

# Vulnerability categories with realistic names
VULN_CATEGORIES = [
    "Remote Code Execution",
    "SQL Injection",
    "Cross-Site Scripting",
    "Buffer Overflow",
    "Privilege Escalation",
    "Information Disclosure",
    "Denial of Service",
    "Authentication Bypass",
    "Path Traversal",
    "Insecure Deserialization",
    "Command Injection",
    "XML External Entity",
    "Server-Side Request Forgery",
    "Cross-Site Request Forgery",
    "Insecure Direct Object Reference",
]


def generate_cve_id(year: int = None) -> str:
    """Generate realistic CVE ID."""
    if year is None:
        year = random.choice([2024, 2024, 2024, 2023, 2023, 2022])
    return f"CVE-{year}-{random.randint(1000, 99999)}"


def generate_hostname(asset_type: str, index: int) -> str:
    """Generate realistic hostname."""
    prefixes = {
        "server": ["srv", "prod-srv", "dev-srv", "stg-srv"],
        "workstation": ["ws", "laptop", "desktop", "wks"],
        "database": ["db", "postgres", "mysql", "mongo", "redis"],
        "network_device": ["router", "switch", "firewall", "vpn"],
        "cloud_instance": ["ec2", "vm", "gcp", "azure"],
        "container": ["k8s", "docker", "pod", "container"],
        "api_gateway": ["api", "gateway", "apigw"],
        "load_balancer": ["lb", "nginx", "haproxy", "f5"],
    }
    prefix = random.choice(prefixes.get(asset_type, ["asset"]))
    return f"{prefix}-{index:04d}.{random.choice(['prod', 'dev', 'stg', 'test'])}.local"


def generate_ip() -> str:
    """Generate private IP address."""
    private_ranges = [
        (10, 0, 0, 1, 10, 255, 255, 254),
        (172, 16, 0, 1, 172, 31, 255, 254),
        (192, 168, 0, 1, 192, 168, 255, 254),
    ]
    r = random.choice(private_ranges)
    return f"{random.randint(r[0], r[4])}.{random.randint(r[1], r[5])}.{random.randint(r[2], r[6])}.{random.randint(r[3], r[7])}"


def generate_dates() -> tuple[datetime, datetime | None, datetime | None]:
    """Generate discovered, due, and remediated dates."""
    now = datetime.now(timezone.utc)
    
    # Discovered: within last 180 days
    discovered = now - timedelta(days=random.randint(1, 180))
    
    # Due date: 7-90 days after discovery
    due = discovered + timedelta(days=random.randint(7, 90))
    
    # Remediated: only for REMEDIATED status, within due date
    remediated = None
    if random.random() < 0.2:  # 20% remediated
        remediated = discovered + timedelta(days=random.randint(1, min(60, (due - discovered).days)))
    
    return discovered, due, remediated


def calculate_priority_score(asset_criticality: int, cve_severity: str) -> Decimal:
    """Calculate internal priority score based on asset criticality and CVE severity."""
    severity_weights = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 4, "LOW": 1}
    base_score = severity_weights.get(cve_severity, 5)
    
    # Add randomness and asset criticality multiplier
    score = (base_score * asset_criticality * random.uniform(0.8, 1.2))
    return Decimal(str(min(round(score, 4), 9999.9999)))


def main():
    print("🚀 Generating 2000+ synthetic vulnerability findings for analysis...")
    
    engine = _engine()
    now = datetime.now(timezone.utc)
    
    # Configuration
    NUM_ASSETS = 500
    NUM_CVES = 300
    NUM_FINDINGS = 2000
    
    with engine.begin() as conn:
        # Get existing data for reference
        existing_bu = conn.execute(text("SELECT id, code FROM business_units")).fetchall()
        existing_teams = conn.execute(text("SELECT id, business_unit_id FROM teams")).fetchall()
        existing_locs = conn.execute(text("SELECT id FROM locations")).fetchall()
        
        if not existing_bu:
            print("❌ No business units found. Run seed_oltp.py first!")
            return
        
        bu_map = {row[1]: row[0] for row in existing_bu}
        team_bu_pairs = [(row[0], row[1]) for row in existing_teams] if existing_teams else []
        loc_ids = [row[0] for row in existing_locs] if existing_locs else [None]
        
        # Create additional business units if needed
        bu_codes = list(bu_map.keys())
        for name, code in BUSINESS_UNITS:
            if code not in bu_codes:
                bu_id = uuid4()
                conn.execute(
                    text("""
                        INSERT INTO business_units (id, name, code, parent_business_unit_id)
                        VALUES (:id, :name, :code, NULL)
                        ON CONFLICT (code) DO NOTHING
                    """),
                    {"id": bu_id, "name": name, "code": code}
                )
                bu_map[code] = bu_id
        
        # Refresh BU map
        existing_bu = conn.execute(text("SELECT id, code FROM business_units")).fetchall()
        bu_map = {row[1]: row[0] for row in existing_bu}
        bu_ids = list(bu_map.values())
        
        print(f"✅ Using {len(bu_ids)} business units")
        
        # Generate Assets
        print(f"📦 Generating {NUM_ASSETS} assets...")
        asset_ids = []
        for i in range(NUM_ASSETS):
            asset_type, base_criticality = random.choice(ASSET_TYPES)
            asset_id = uuid4()
            hostname = generate_hostname(asset_type, i)
            bu_id = random.choice(bu_ids)
            
            conn.execute(
                text("""
                    INSERT INTO assets (id, name, asset_type, hostname, ip_address, 
                        business_unit_id, team_id, location_id, criticality, owner_email, is_active, created_at)
                    VALUES (:id, :name, :asset_type, :hostname, :ip, :bu_id, NULL, :loc_id, 
                        :criticality, :owner, true, :created)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": asset_id,
                    "name": f"{asset_type.replace('_', ' ').title()} {i+1:04d}",
                    "asset_type": asset_type,
                    "hostname": hostname,
                    "ip": generate_ip(),
                    "bu_id": bu_id,
                    "loc_id": random.choice(loc_ids),
                    "criticality": base_criticality + random.randint(-1, 1),
                    "owner": f"owner{i+1:04d}@aegiscore.local",
                    "created": now - timedelta(days=random.randint(30, 730)),
                }
            )
            asset_ids.append((asset_id, base_criticality))
        
        print(f"✅ Generated {len(asset_ids)} assets")
        
        # Generate CVE Records
        print(f"🔒 Generating {NUM_CVES} CVE records...")
        cve_ids = []
        for i in range(NUM_CVES):
            cve_id = generate_cve_id()
            severity = random.choice(CVE_SEVERITIES)
            cvss_score = random.uniform(0.1, 10.0)
            
            # EPSS score correlates with severity
            epss_weights = {"CRITICAL": 0.8, "HIGH": 0.5, "MEDIUM": 0.2, "LOW": 0.05}
            epss_score = min(epss_weights.get(severity, 0.3) * random.uniform(0.5, 1.5), 1.0)
            
            conn.execute(
                text("""
                    INSERT INTO cve_records (id, cve_id, title, description, severity, 
                        cvss_base_score, cvss_vector, epss_score, exploit_available, published_at, last_modified_at)
                    VALUES (:id, :cve_id, :title, :desc, :severity, :cvss, :vector, :epss, :exploit, :published, :modified)
                    ON CONFLICT (cve_id) DO NOTHING
                """),
                {
                    "id": uuid4(),
                    "cve_id": cve_id,
                    "title": f"{random.choice(VULN_CATEGORIES)} in {random.choice(['Apache', 'Nginx', 'Windows', 'Linux', 'Java', 'Python', 'Node.js', 'MySQL', 'PostgreSQL'])}",
                    "desc": f"{random.choice(VULN_CATEGORIES)} vulnerability in {random.choice(['Apache', 'Nginx', 'Windows', 'Linux', 'Java', 'Python', 'Node.js', 'MySQL', 'PostgreSQL'])} {random.randint(1, 20)}.{random.randint(0, 9)}",
                    "severity": severity,
                    "cvss": round(cvss_score, 2),
                    "vector": f"CVSS:3.1/AV:{random.choice(['N','A','L','P'])}/AC:{random.choice(['L','H'])}/PR:{random.choice(['N','L','H'])}/UI:{random.choice(['N','R'])}/S:{random.choice(['U','C'])}/C:{random.choice(['H','L','N'])}/I:{random.choice(['H','L','N'])}/A:{random.choice(['H','L','N'])}",
                    "epss": round(epss_score, 5),
                    "exploit": random.random() < 0.3,
                    "published": now - timedelta(days=random.randint(1, 365)),
                    "modified": now - timedelta(days=random.randint(0, 30)),
                }
            )
            cve_ids.append((cve_id, severity))
        
        # Get all CVE IDs from database
        all_cves = conn.execute(text("SELECT id, cve_id, severity FROM cve_records")).fetchall()
        cve_map = {row[1]: (row[0], row[2]) for row in all_cves}
        cve_list = list(cve_map.items())
        
        print(f"✅ Using {len(cve_list)} CVE records")
        
        # Generate Vulnerability Findings (2000+)
        print(f"🎯 Generating {NUM_FINDINGS} vulnerability findings...")
        findings_created = 0
        
        for i in range(NUM_FINDINGS):
            # Pick random asset and CVE
            asset_id, asset_criticality = random.choice(asset_ids)
            cve_id_str, (cve_record_id, cve_severity) = random.choice(cve_list)
            
            # Generate dates
            discovered, due, remediated = generate_dates()
            
            # Determine status
            status = random.choice(STATUSES)
            if remediated and status not in ["REMEDIATED", "FALSE_POSITIVE"]:
                status = "REMEDIATED"
            
            # Calculate priority score
            priority_score = calculate_priority_score(asset_criticality, cve_severity)
            
            # Assigned user (20% of findings)
            assigned_to = None
            if status in ["OPEN", "IN_PROGRESS"] and random.random() < 0.2:
                # Pick from seeded users
                user_rows = conn.execute(text("SELECT id FROM users LIMIT 3")).fetchall()
                if user_rows:
                    assigned_to = str(random.choice(user_rows)[0])
            
            conn.execute(
                text("""
                    INSERT INTO vulnerability_findings (
                        id, asset_id, cve_record_id, status, discovered_at, due_at, 
                        remediated_at, notes, assigned_to_user_id, internal_priority_score, created_at
                    )
                    VALUES (
                        :id, :asset_id, :cve_id, :status, :discovered, :due, 
                        :remediated, :notes, :assigned, :priority, :created
                    )
                    ON CONFLICT (asset_id, cve_record_id) DO NOTHING
                """),
                {
                    "id": uuid4(),
                    "asset_id": asset_id,
                    "cve_id": cve_record_id,
                    "status": status,
                    "discovered": discovered,
                    "due": due,
                    "remediated": remediated,
                    "notes": f"Auto-generated finding #{i+1}. {random.choice(['Requires immediate attention.', 'Scheduled for patching.', 'Under investigation.', 'Waiting for vendor fix.', 'Risk accepted.'])}",
                    "assigned": assigned_to,
                    "priority": priority_score,
                    "created": now,
                }
            )
            findings_created += 1
            
            if (i + 1) % 500 == 0:
                print(f"  Progress: {i+1}/{NUM_FINDINGS} findings...")
        
        print(f"✅ Created {findings_created} vulnerability findings")
    
    # Print summary statistics
    print("\n📊 Data Generation Summary:")
    print("=" * 50)
    
    with engine.begin() as conn:
        counts = {
            "Business Units": conn.execute(text("SELECT COUNT(*) FROM business_units")).scalar(),
            "Assets": conn.execute(text("SELECT COUNT(*) FROM assets")).scalar(),
            "CVE Records": conn.execute(text("SELECT COUNT(*) FROM cve_records")).scalar(),
            "Findings": conn.execute(text("SELECT COUNT(*) FROM vulnerability_findings")).scalar(),
            "Users": conn.execute(text("SELECT COUNT(*) FROM users")).scalar(),
        }
        
        for name, count in counts.items():
            print(f"  {name}: {count}")
    
    print("\n🎉 Analysis data generation complete!")
    print("\nYou can now:")
    print("  - View dashboard with real charts")
    print("  - Filter and paginate through findings")
    print("  - Test analytics APIs")
    print("  - Demonstrate risk prioritization ML features")


if __name__ == "__main__":
    main()

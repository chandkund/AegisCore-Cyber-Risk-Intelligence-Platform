from __future__ import annotations

import argparse
import os
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from data_pipeline.transformation.dates import date_key, dim_date_row, iter_date_range

PIPELINE_NAME = "reporting_daily"


def _engine() -> Engine:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    return create_engine(url, pool_pre_ping=True)


def ensure_dim_severity(engine: Engine) -> None:
    rows = [
        ("INFO", 1),
        ("LOW", 2),
        ("MEDIUM", 3),
        ("HIGH", 4),
        ("CRITICAL", 5),
    ]
    with engine.begin() as conn:
        for code, rank in rows:
            conn.execute(
                text(
                    """
                    INSERT INTO reporting.dim_severity (severity_code, rank)
                    VALUES (:code, :rank)
                    ON CONFLICT (severity_code) DO UPDATE SET rank = EXCLUDED.rank
                    """
                ),
                {"code": code, "rank": rank},
            )


def ensure_dim_dates(engine: Engine, start: date, end: date) -> None:
    with engine.begin() as conn:
        for d in iter_date_range(start, end):
            row = dim_date_row(d)
            conn.execute(
                text(
                    """
                    INSERT INTO reporting.dim_date (
                        date_key, full_date, year, quarter, month, week_of_year, day_of_week, is_weekend
                    ) VALUES (
                        :date_key, :full_date, :year, :quarter, :month, :week_of_year, :day_of_week, :is_weekend
                    )
                    ON CONFLICT (full_date) DO NOTHING
                    """
                ),
                row,
            )


def sync_dimensions_from_oltp(engine: Engine) -> None:
    stmts = [
        """
        INSERT INTO reporting.dim_business_unit (business_unit_id, name, code)
        SELECT id, name, code FROM business_units
        ON CONFLICT (business_unit_id) DO UPDATE
        SET name = EXCLUDED.name, code = EXCLUDED.code
        """,
        """
        INSERT INTO reporting.dim_team (team_id, name, bu_key)
        SELECT t.id, t.name, dbu.bu_key
        FROM teams t
        JOIN reporting.dim_business_unit dbu ON dbu.business_unit_id = t.business_unit_id
        ON CONFLICT (team_id) DO UPDATE
        SET name = EXCLUDED.name, bu_key = EXCLUDED.bu_key
        """,
        """
        INSERT INTO reporting.dim_asset (
            asset_id, name, asset_type, criticality, bu_key, team_key
        )
        SELECT
            a.id, a.name, a.asset_type, a.criticality,
            dbu.bu_key,
            dt.team_key
        FROM assets a
        JOIN reporting.dim_business_unit dbu ON dbu.business_unit_id = a.business_unit_id
        LEFT JOIN reporting.dim_team dt ON dt.team_id = a.team_id
        ON CONFLICT (asset_id) DO UPDATE SET
            name = EXCLUDED.name,
            asset_type = EXCLUDED.asset_type,
            criticality = EXCLUDED.criticality,
            bu_key = EXCLUDED.bu_key,
            team_key = EXCLUDED.team_key
        """,
        """
        INSERT INTO reporting.dim_cve (cve_record_id, cve_id, severity, cvss_base_score)
        SELECT id, cve_id, severity, cvss_base_score FROM cve_records
        ON CONFLICT (cve_record_id) DO UPDATE SET
            cve_id = EXCLUDED.cve_id,
            severity = EXCLUDED.severity,
            cvss_base_score = EXCLUDED.cvss_base_score
        """,
        """
        INSERT INTO reporting.dim_assignee_user (user_id, email, full_name)
        SELECT id, email, full_name FROM users WHERE is_active IS TRUE
        ON CONFLICT (user_id) DO UPDATE SET
            email = EXCLUDED.email,
            full_name = EXCLUDED.full_name
        """,
    ]
    with engine.begin() as conn:
        for sql in stmts:
            conn.execute(text(sql))


def load_fact_snapshot(engine: Engine, snapshot_date: date) -> int:
    dk = date_key(snapshot_date)
    snapshot_end = datetime.combine(snapshot_date, time(23, 59, 59), tzinfo=timezone.utc)
    delete_sql = text("DELETE FROM reporting.fact_vulnerability_snapshot WHERE snapshot_date = :d")
    insert_sql = text(
        """
        INSERT INTO reporting.fact_vulnerability_snapshot (
            snapshot_date,
            date_key,
            finding_oltp_id,
            asset_key,
            cve_key,
            bu_key,
            team_key,
            assignee_user_key,
            severity_key,
            status,
            cvss_base_score,
            epss_score,
            days_open,
            is_overdue,
            exploit_available,
            loaded_at
        )
        SELECT
            :snapshot_date::date,
            :date_key,
            vf.id,
            da.asset_key,
            dc.cve_key,
            dbu.bu_key,
            dt.team_key,
            du.user_key,
            ds.severity_key,
            vf.status,
            cr.cvss_base_score,
            cr.epss_score,
            GREATEST(
                0,
                (
                    :snapshot_date::date
                    - (vf.discovered_at AT TIME ZONE 'UTC')::date
                )::int
            ),
            CASE
                WHEN vf.due_at IS NOT NULL
                     AND (vf.due_at AT TIME ZONE 'UTC') < :snapshot_end
                     AND vf.status NOT IN ('REMEDIATED', 'FALSE_POSITIVE')
                THEN TRUE
                ELSE FALSE
            END,
            cr.exploit_available,
            now()
        FROM vulnerability_findings vf
        JOIN assets a ON a.id = vf.asset_id
        JOIN cve_records cr ON cr.id = vf.cve_record_id
        JOIN reporting.dim_asset da ON da.asset_id = a.id
        JOIN reporting.dim_cve dc ON dc.cve_record_id = cr.id
        JOIN reporting.dim_business_unit dbu ON dbu.business_unit_id = a.business_unit_id
        LEFT JOIN reporting.dim_team dt ON dt.team_id = a.team_id
        JOIN reporting.dim_severity ds ON ds.severity_code = cr.severity
        LEFT JOIN reporting.dim_assignee_user du ON du.user_id = vf.assigned_to_user_id
        WHERE
            (vf.discovered_at AT TIME ZONE 'UTC') <= :snapshot_end
            AND (
                vf.remediated_at IS NULL
                OR (vf.remediated_at AT TIME ZONE 'UTC')::date > :snapshot_date::date
            )
        ON CONFLICT (snapshot_date, finding_oltp_id) DO UPDATE SET
            date_key = EXCLUDED.date_key,
            asset_key = EXCLUDED.asset_key,
            cve_key = EXCLUDED.cve_key,
            bu_key = EXCLUDED.bu_key,
            team_key = EXCLUDED.team_key,
            assignee_user_key = EXCLUDED.assignee_user_key,
            severity_key = EXCLUDED.severity_key,
            status = EXCLUDED.status,
            cvss_base_score = EXCLUDED.cvss_base_score,
            epss_score = EXCLUDED.epss_score,
            days_open = EXCLUDED.days_open,
            is_overdue = EXCLUDED.is_overdue,
            exploit_available = EXCLUDED.exploit_available,
            loaded_at = EXCLUDED.loaded_at
        """
    )
    with engine.begin() as conn:
        conn.execute(delete_sql, {"d": snapshot_date})
        conn.execute(
            insert_sql,
            {
                "snapshot_date": snapshot_date,
                "date_key": dk,
                "snapshot_end": snapshot_end,
            },
        )
        cnt = conn.execute(
            text(
                "SELECT COUNT(*) FROM reporting.fact_vulnerability_snapshot WHERE snapshot_date = :d"
            ),
            {"d": snapshot_date},
        ).scalar_one()
        return int(cnt)


def update_watermark(engine: Engine, high_watermark: datetime) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO etl_watermarks (pipeline_name, last_success_at, high_watermark)
                VALUES (:name, now(), :hwm)
                ON CONFLICT (pipeline_name) DO UPDATE SET
                    last_success_at = now(),
                    high_watermark = EXCLUDED.high_watermark
                """
            ),
            {"name": PIPELINE_NAME, "hwm": high_watermark},
        )


def run(snapshot_date: date, dim_start: date, dim_end: date) -> int:
    engine = _engine()
    ensure_dim_severity(engine)
    ensure_dim_dates(engine, dim_start, dim_end)
    sync_dimensions_from_oltp(engine)
    rows = load_fact_snapshot(engine, snapshot_date)
    update_watermark(engine, datetime.now(timezone.utc))
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="Build reporting star schema snapshot from OLTP.")
    p.add_argument("--snapshot-date", required=True, help="YYYY-MM-DD")
    p.add_argument(
        "--dim-start",
        help="Start date for dim_date backfill (YYYY-MM-DD), default: snapshot date - 30d",
    )
    p.add_argument(
        "--dim-end",
        help="End date for dim_date backfill (YYYY-MM-DD), default: snapshot date",
    )
    args = p.parse_args()
    snap = date.fromisoformat(args.snapshot_date)
    dim_end = date.fromisoformat(args.dim_end) if args.dim_end else snap
    dim_start = date.fromisoformat(args.dim_start) if args.dim_start else snap - timedelta(days=30)
    n = run(snap, dim_start, dim_end)
    print(f"Loaded {n} fact rows for {snap}")


if __name__ == "__main__":
    main()

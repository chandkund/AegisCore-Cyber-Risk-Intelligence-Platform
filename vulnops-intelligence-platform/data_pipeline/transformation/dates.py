from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def date_key(d: date) -> int:
    return d.year * 10_000 + d.month * 100 + d.day


def iter_date_range(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def dim_date_row(d: date) -> dict:
    q = (d.month - 1) // 3 + 1
    week = d.isocalendar().week
    dow = d.weekday()
    return {
        "date_key": date_key(d),
        "full_date": d,
        "year": d.year,
        "quarter": q,
        "month": d.month,
        "week_of_year": week,
        "day_of_week": dow,
        "is_weekend": dow >= 5,
    }


def month_bounds_utc(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end

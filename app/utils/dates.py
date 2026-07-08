from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def now_in_timezone(timezone_name: str) -> datetime:
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)


def today(timezone_name: str) -> date:
    return now_in_timezone(timezone_name).date()


def period_bounds(period: str | None, reference_date: date) -> tuple[date | None, date | None]:
    normalized = (period or "all").strip().lower()
    if normalized == "today":
        return reference_date, reference_date
    if normalized == "tomorrow":
        tomorrow = reference_date + timedelta(days=1)
        return tomorrow, tomorrow
    if normalized == "yesterday":
        yesterday = reference_date - timedelta(days=1)
        return yesterday, yesterday
    if normalized == "this_month":
        start = reference_date.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, next_month - timedelta(days=1)
    if normalized == "last_week":
        start_of_this_week = reference_date - timedelta(days=reference_date.weekday())
        start = start_of_this_week - timedelta(days=7)
        return start, start + timedelta(days=6)
    if normalized == "semester":
        start_month = 1 if reference_date.month <= 6 else 7
        start = reference_date.replace(month=start_month, day=1)
        return start, reference_date
    return None, None


def day_name_for_period(period: str | None, reference_date: date) -> str:
    start, _ = period_bounds(period, reference_date)
    target_date = start or reference_date
    return target_date.strftime("%A")


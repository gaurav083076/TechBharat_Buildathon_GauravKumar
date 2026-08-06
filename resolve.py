from __future__ import annotations

from datetime import date, datetime, timedelta

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def resolve_date(due_raw: str | None, meeting_date: str) -> str | None:
    if not due_raw:
        return None

    base = datetime.strptime(meeting_date, "%Y-%m-%d").date()
    text = due_raw.lower().strip()

    if "end of the quarter" in text or "end of quarter" in text:
        q_end_month = ((base.month - 1) // 3 + 1) * 3
        result = date(base.year, q_end_month, 1) + relativedelta(day=31)
        return result.isoformat()

    if "end of the week" in text or "end of week" in text:
        days_ahead = (4 - base.weekday()) % 7
        return (base + timedelta(days=days_ahead)).isoformat()

    if "tomorrow" in text:
        return (base + timedelta(days=1)).isoformat()

    if "today" in text:
        return base.isoformat()

    for name, idx in _WEEKDAYS.items():
        if name in text:
            days_ahead = (idx - base.weekday()) % 7
            if days_ahead == 0 or "next" in text:
                days_ahead += 7
            return (base + timedelta(days=days_ahead)).isoformat()

    try:
        parsed = dateutil_parser.parse(due_raw, default=datetime.combine(base, datetime.min.time()))
        return parsed.date().isoformat()
    except (ValueError, OverflowError):
        return None


def resolve_owner(owner_raw: str, contacts: list[dict]) -> dict | None:
    if not owner_raw:
        return None

    needle = owner_raw.strip().lower()
    matches = [
        c for c in contacts
        if needle in c["name"].lower() or c["name"].lower().split()[0] == needle
    ]

    if len(matches) == 1:
        return matches[0]
    return None
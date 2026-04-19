from __future__ import annotations

from datetime import date, timedelta

from ..automation_models import SourceConfig

_WEEKDAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def resolve_publication_date(*, source: SourceConfig, job_date: str) -> str | None:
    schedule = source.schedule or {}
    publication_days = schedule.get("publication_days") or []
    if not publication_days:
        return job_date

    allowed_weekdays = {
        _WEEKDAY_NAMES[str(day).strip().casefold()]
        for day in publication_days
        if str(day).strip().casefold() in _WEEKDAY_NAMES
    }
    if not allowed_weekdays:
        return job_date

    candidate = date.fromisoformat(job_date)
    if candidate.weekday() in allowed_weekdays:
        return candidate.isoformat()

    fallback = bool(schedule.get("fallback_to_previous_publication_day", True))
    if not fallback:
        return None

    for _ in range(7):
        candidate -= timedelta(days=1)
        if candidate.weekday() in allowed_weekdays:
            return candidate.isoformat()
    return None

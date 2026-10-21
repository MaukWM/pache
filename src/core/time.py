"""Shared datetime helpers."""

from datetime import UTC, datetime


def ensure_utc(dt: datetime) -> datetime:
    """Normalize a datetime to tz-aware UTC.

    Naive values are taken as UTC (MySQL and SQLite hand back naive datetimes for our
    timezone-aware columns, and the app stores UTC). Aware values are converted, so an
    offset like ``+09:00`` lands on the right instant rather than its wall-clock digits.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)

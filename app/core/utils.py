from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current time in UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """If a datetime has no timezone, treat it as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value

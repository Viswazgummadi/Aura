from datetime import datetime, timezone

def to_rfc3339(dt: datetime) -> str | None:
    """
    Converts a timezone-aware datetime object to RFC 3339 (ISO 8601 with Z suffix for UTC).
    Raises an error if the datetime is naive.
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        raise ValueError("Datetime passed to to_rfc3339() must be timezone-aware")

    dt = dt.astimezone(timezone.utc)
    return dt.isoformat(timespec='microseconds').replace('+00:00', 'Z')

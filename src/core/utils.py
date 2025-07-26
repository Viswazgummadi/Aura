from datetime import datetime, timezone

def to_rfc3339(dt: datetime) -> str | None:
    """
    Converts a datetime object to an RFC 3339 formatted string (ISO 8601 with Z for UTC).
    Ensures the datetime is timezone-aware and in UTC.
    """
    if dt is None:
        return None
    
    # If naive, assume UTC for simplicity (or raise error, depending on strictness)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
        
    return dt.isoformat(timespec='microseconds').replace('+00:00', 'Z')
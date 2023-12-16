from datetime import datetime, timezone


def sleep_until(arrival: datetime, buffer: int = 1):
    """Return the number of seconds until the nominated datetime is reached (plus `buffer`),
    or None if the datetime is in the past.
    """
    now = datetime.now(timezone.utc)
    if arrival <= now:
        return None
    pause = (arrival - now).seconds + buffer
    return pause


def infer_system_symbol(waypoint_symbol):
    """Infer the System symbol from a passed-in Waypoint symbol.
    """
    return "-".join(waypoint_symbol.split("-")[0:-1])

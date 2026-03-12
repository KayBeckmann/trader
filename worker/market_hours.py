from datetime import datetime, time
from zoneinfo import ZoneInfo

_NYSE_TZ = ZoneInfo("America/New_York")
_OPEN = time(9, 30)
_CLOSE = time(16, 0)


def is_market_open() -> bool:
    """True wenn NYSE aktuell geöffnet ist (Mo–Fr, 09:30–16:00 ET)."""
    now = datetime.now(_NYSE_TZ)
    if now.weekday() >= 5:  # Samstag=5, Sonntag=6
        return False
    return _OPEN <= now.time() < _CLOSE

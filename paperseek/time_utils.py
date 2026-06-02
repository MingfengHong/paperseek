from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None  # type: ignore[assignment]


PAPERSEEK_DEFAULT_TZ = timezone(timedelta(hours=8))


def paperseek_timezone(timezone_name: Optional[str] = None):
    configured = (timezone_name or os.environ.get("PAPERSEEK_TIMEZONE", "")).strip()
    if configured and ZoneInfo is not None:
        try:
            return ZoneInfo(configured)
        except Exception:
            pass

    try:
        local_tz = datetime.now().astimezone().tzinfo
        if local_tz is not None:
            return local_tz
    except Exception:
        pass
    return PAPERSEEK_DEFAULT_TZ


def paperseek_now(timezone_name: Optional[str] = None) -> datetime:
    return datetime.now(paperseek_timezone(timezone_name))


def paperseek_now_iso(timezone_name: Optional[str] = None) -> str:
    return paperseek_now(timezone_name).isoformat(timespec="seconds")

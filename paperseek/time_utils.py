from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None  # type: ignore[assignment]


PAPERSEEK_DEFAULT_TZ = timezone(timedelta(hours=8))
NAMED_FALLBACK_TIMEZONES = {
    "asia/shanghai": PAPERSEEK_DEFAULT_TZ,
    "asia/chongqing": PAPERSEEK_DEFAULT_TZ,
    "asia/harbin": PAPERSEEK_DEFAULT_TZ,
    "asia/taipei": PAPERSEEK_DEFAULT_TZ,
    "asia/hong_kong": PAPERSEEK_DEFAULT_TZ,
    "utc": timezone.utc,
    "etc/utc": timezone.utc,
}


def paperseek_timezone(timezone_name: Optional[str] = None):
    configured = (timezone_name or os.environ.get("PAPERSEEK_TIMEZONE", "")).strip()
    if configured and ZoneInfo is not None:
        try:
            return ZoneInfo(configured)
        except Exception:
            pass
    if configured:
        named = NAMED_FALLBACK_TIMEZONES.get(configured.lower())
        if named is not None:
            return named
        offset = _parse_utc_offset(configured)
        if offset is not None:
            return offset

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


def _parse_utc_offset(value: str):
    cleaned = value.strip().upper().replace("UTC", "").replace("GMT", "")
    if not cleaned:
        return None
    sign = 1
    if cleaned[0] == "+":
        cleaned = cleaned[1:]
    elif cleaned[0] == "-":
        sign = -1
        cleaned = cleaned[1:]
    else:
        return None
    if ":" in cleaned:
        hour_text, minute_text = cleaned.split(":", 1)
    else:
        hour_text, minute_text = cleaned, "0"
    try:
        hours = int(hour_text)
        minutes = int(minute_text)
    except ValueError:
        return None
    if hours < 0 or minutes < 0 or hours > 23 or minutes > 59:
        return None
    return timezone(sign * timedelta(hours=hours, minutes=minutes))

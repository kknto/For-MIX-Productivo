import os
from datetime import datetime

import pytz

DEFAULT_TIMEZONE = "America/Cancun"


def get_timezone_name() -> str:
    return (
        os.getenv("APP_TIMEZONE", "").strip()
        or os.getenv("TZ", "").strip()
        or DEFAULT_TIMEZONE
    )


def get_timezone():
    try:
        return pytz.timezone(get_timezone_name())
    except Exception:
        return pytz.timezone(DEFAULT_TIMEZONE)


def get_now() -> datetime:
    return datetime.now(get_timezone())


def now_str() -> str:
    return get_now().strftime("%Y-%m-%d %H:%M:%S")

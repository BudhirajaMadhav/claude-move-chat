#!/usr/bin/env python3
"""Self-check for timestamp handling in search-chat.py. Run: python3 test_search_chat.py"""

import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "search-chat.py"
spec = importlib.util.spec_from_file_location("search_chat", TARGET)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


def test_utc_to_ist():
    # Session logs store UTC. 10:24 UTC is 15:54 IST on the same day.
    assert sc.format_timestamp("2026-09-15T10:24:48.187Z") == "2026-09-15 15:54"


def test_ist_rolls_the_date_forward():
    # 20:00 UTC is 01:30 IST on the next day.
    assert sc.format_timestamp("2026-09-15T20:00:00.000Z") == "2026-09-16 01:30"


def test_missing_or_bad_timestamp():
    assert sc.format_timestamp("") == ""
    assert sc.format_timestamp("not-a-date") == ""
    assert sc.parse_timestamp(None) is None


def test_relative_time_handles_aware_datetimes():
    now = datetime.now(sc.IST)
    assert sc.relative_time(now - timedelta(seconds=5)) == "just now"
    assert sc.relative_time(now - timedelta(hours=3)) == "3h ago"
    assert sc.relative_time(now - timedelta(days=2)) == "2d ago"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all checks passed")

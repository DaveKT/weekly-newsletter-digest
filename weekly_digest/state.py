"""Persistent state for interim (--since-last-run) reports.

This is deliberately separate from the scheduled weekly run, which is purely
date-window based and never reads or writes this file. Running an interim report
therefore cannot shift what the next scheduled digest produces.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# Lives in the project root (next to mysecrets), not inside the package.
STATE_PATH = Path(__file__).resolve().parent.parent / ".reeder_interim_state.json"


def read_last_interim() -> datetime | None:
    """Timestamp of the last interim run, or None if there isn't one yet."""
    if not STATE_PATH.exists():
        return None
    try:
        data = json.loads(STATE_PATH.read_text())
        return datetime.fromisoformat(data["last_run"])
    except (ValueError, KeyError, OSError):
        return None


def write_last_interim(when: datetime) -> None:
    STATE_PATH.write_text(json.dumps({"last_run": when.isoformat()}))

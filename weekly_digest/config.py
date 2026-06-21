"""Configuration and date helpers for the weekly digest pipeline.

All secrets and tunables come from environment variables (see mysecrets.example).
Nothing here reads a file directly; run.sh sources `mysecrets` before invoking
the package, so the variables are already in the environment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


def _clean(v: str | None) -> str:
    return (v or "").strip()


@dataclass
class Config:
    # OpenRouter / summarization
    openrouter_api_key: str
    openrouter_model: str
    openrouter_base_url: str
    # Gmail
    gmail_client_id: str
    gmail_client_secret: str
    gmail_refresh_token: str
    gmail_label: str
    # Reeder
    reeder_feed_url: str
    # Output / metadata
    output_dir: Path
    compiled_for: str
    # Coverage window (inclusive Monday .. Sunday)
    coverage_start: date
    coverage_end: date

    @property
    def issue_number(self) -> str:
        d = self.coverage_start
        return f"{d.year % 100:02d}{d.timetuple().tm_yday + 1:03d}"


def previous_week(today: date | None = None) -> tuple[date, date]:
    """Return (Monday, Sunday) of the just-completed week.

    If today is Sunday, the window is the Mon..Sun that ends today's-eve, i.e.
    the most recent fully-completed Mon..Sun. Matches the skill's default.
    """
    today = today or date.today()
    # Monday of the current week:
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday, last_sunday


def _parse_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def load_config() -> Config:
    """Build Config from environment, applying the date-window overrides.

    DIGEST_WEEK_START / DIGEST_WEEK_END (YYYY-MM-DD) override the default
    previous-week window when set together.
    """
    start_env = _clean(os.environ.get("DIGEST_WEEK_START"))
    end_env = _clean(os.environ.get("DIGEST_WEEK_END"))
    if start_env and end_env:
        cov_start, cov_end = _parse_date(start_env), _parse_date(end_env)
    else:
        cov_start, cov_end = previous_week()

    out = _clean(os.environ.get("DIGEST_OUTPUT_DIR")) or "~/Desktop"
    cfg = Config(
        openrouter_api_key=_clean(os.environ.get("OPENROUTER_API_KEY")),
        openrouter_model=_clean(os.environ.get("OPENROUTER_MODEL")) or "anthropic/claude-sonnet-4.6",
        openrouter_base_url=_clean(os.environ.get("OPENROUTER_BASE_URL")) or "https://openrouter.ai/api/v1",
        gmail_client_id=_clean(os.environ.get("GMAIL_CLIENT_ID")),
        gmail_client_secret=_clean(os.environ.get("GMAIL_CLIENT_SECRET")),
        gmail_refresh_token=_clean(os.environ.get("GMAIL_REFRESH_TOKEN")),
        gmail_label=_clean(os.environ.get("GMAIL_LABEL")) or "News Letter",
        reeder_feed_url=_clean(os.environ.get("REEDER_FEED_URL")),
        output_dir=Path(out).expanduser(),
        compiled_for=_clean(os.environ.get("DIGEST_COMPILED_FOR")) or "Your Name",
        coverage_start=cov_start,
        coverage_end=cov_end,
    )
    return cfg


def require(cfg: Config, *names: str) -> None:
    """Raise a clear error if any required config value is empty."""
    missing = [n for n in names if not getattr(cfg, n)]
    if missing:
        raise SystemExit(
            "Missing required configuration: "
            + ", ".join(missing)
            + ".\nSet them in your `mysecrets` file (see mysecrets.example)."
        )

"""Full-text extraction for link-only newsletters and thin Reeder items.

Uses trafilatura to fetch and extract readable article text. Best-effort:
on any failure the original body is kept, so a flaky URL never aborts the run.
"""
from __future__ import annotations

import trafilatura

from .models import Story

# Below this many characters of body text, try to fetch the linked article.
THIN_THRESHOLD = 600
# Cap extracted text so a single 100k-char article doesn't blow up token cost.
MAX_CHARS = 40_000


def _extract_url(url: str) -> str:
    if not url:
        return ""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        text = trafilatura.extract(
            downloaded, include_comments=False, include_tables=False
        )
        return (text or "").strip()
    except Exception:
        return ""


def enrich(stories: list[Story]) -> list[Story]:
    """For thin stories, fetch full article text from primary_url in place."""
    for s in stories:
        if len(s.body_text.strip()) >= THIN_THRESHOLD:
            if len(s.body_text) > MAX_CHARS:
                s.body_text = s.body_text[:MAX_CHARS]
            continue
        if not s.primary_url:
            continue
        full = _extract_url(s.primary_url)
        if len(full) > len(s.body_text.strip()):
            s.body_text = full[:MAX_CHARS]
    return stories

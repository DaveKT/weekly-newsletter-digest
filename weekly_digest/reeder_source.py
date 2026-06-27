"""Fetch read-later articles from the Reeder shared JSON Feed.

Filtering is by **save date** (when the item was added to the read-later tag),
not the article's publish date — Reeder stores that timestamp in `_reeder.date`
(an Apple Core Data epoch, seconds since 2001-01-01 UTC). The displayed/citation
date stays the article's publish date.

Two modes:
  - default (weekly): items saved within cfg's Mon-Sun coverage window.
  - since=<datetime>: items saved after that instant (interim reports).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from . import reeder_read_later as rrl
from .config import Config
from .models import Story, canonicalize_url, publication_from_domain

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def _html_to_text(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _parse_published(raw: str) -> date | None:
    if not raw:
        return None
    txt = raw.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(txt).date()
    except ValueError:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _saved_at(raw_item: dict, published: date | None) -> datetime | None:
    """When the item was added to the read-later tag (aware UTC datetime).

    Prefers Reeder's `_reeder.date` save timestamp; falls back to the article
    publish date (at midnight UTC) when that field is absent.
    """
    d = (raw_item.get("_reeder") or {}).get("date")
    if isinstance(d, (int, float)):
        return APPLE_EPOCH + timedelta(seconds=d)
    if published:
        return datetime(published.year, published.month, published.day, tzinfo=timezone.utc)
    return None


def fetch(cfg: Config, since: datetime | None = None) -> list[Story]:
    """Return Reeder Stories. Filter by save date.

    If `since` is None, include items saved within cfg's [coverage_start,
    coverage_end] window. If `since` is an aware datetime, include items saved
    strictly after it.
    """
    feed = rrl.fetch_feed(cfg.reeder_feed_url)
    raw_items = feed.get("items", [])
    articles = rrl.parse_items(feed)  # 1:1 with raw_items, same order

    stories: list[Story] = []
    for a, raw in zip(articles, raw_items):
        if not a.title or not a.url:
            continue
        published = _parse_published(a.date_published)
        saved = _saved_at(raw, published)
        if saved is None:
            continue
        if since is not None:
            if saved <= since:
                continue
        elif not (cfg.coverage_start <= saved.date() <= cfg.coverage_end):
            continue

        body = a.content_html or ""
        if "<" in body and ">" in body:
            body = _html_to_text(body)
        body = body or (a.summary or "")

        url = canonicalize_url(a.url) or a.url
        stories.append(
            Story(
                source="reeder",
                publication=publication_from_domain(url),
                authors=list(a.authors) if a.authors else [],
                published=published or saved.date(),
                title=a.title.strip(),
                body_text=body,
                primary_url=url,
                urls=[url] if url else [],
            )
        )
    return stories

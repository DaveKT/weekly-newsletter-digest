"""Fetch read-later articles from the Reeder shared JSON Feed and filter to
the coverage week. Reuses the standalone reeder_read_later fetcher.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from . import reeder_read_later as rrl
from .config import Config
from .models import Story, canonicalize_url, publication_from_domain


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


def fetch(cfg: Config) -> list[Story]:
    """Return Reeder Stories whose publish date is within the coverage window."""
    feed = rrl.fetch_feed(cfg.reeder_feed_url)
    articles = rrl.parse_items(feed)

    stories: list[Story] = []
    for a in articles:
        published = _parse_published(a.date_published)
        if not published:
            continue
        if not (cfg.coverage_start <= published <= cfg.coverage_end):
            continue
        if not a.title or not a.url:
            continue

        body = a.content_html or ""
        if "<" in body and ">" in body:
            body = _html_to_text(body)
        body = body or (a.summary or "")

        url = canonicalize_url(a.url) or a.url
        authors = list(a.authors) if a.authors else []
        publication = publication_from_domain(url)

        stories.append(
            Story(
                source="reeder",
                publication=publication,
                authors=authors,
                published=published,
                title=a.title.strip(),
                body_text=body,
                primary_url=url,
                urls=[url] if url else [],
            )
        )
    return stories

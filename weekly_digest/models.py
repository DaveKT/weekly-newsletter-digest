"""Shared data model and helpers used by both the Gmail and Reeder sources."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlparse, urlunparse


@dataclass
class Story:
    """A single editorial item from either source, before summarization."""
    source: str                      # "gmail" or "reeder"
    publication: str
    authors: list[str]
    published: date
    title: str
    body_text: str
    primary_url: str
    urls: list[str] = field(default_factory=list)


# Sender-domain / fragment -> publication name. Mirrors the skill's mapping.
DOMAIN_PUBLICATION = {
    "macstories.net": "MacStories",
    "tidbits.com": "TidBITS",
    "sixcolors.com": "Six Colors",
    "substack.com": "Substack",
    "ghost.io": "404 Media",
    "404media.co": "404 Media",
    "memberful.com": "MacSparky Labs",
    "emails.hbr.org": "Harvard Business Review",
    "hbr.org": "Harvard Business Review",
    "arstechnica.com": "Ars Technica",
    "theverge.com": "The Verge",
    "wired.com": "Wired",
    "nytimes.com": "The New York Times",
}


_TLD_SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu"}


def publication_from_domain(value: str) -> str:
    """Best-effort publication name from a URL, email, or bare host."""
    host = value.lower().strip()
    if "://" in host:
        host = urlparse(host).netloc or host
    if "@" in host:
        host = host.split("@", 1)[1]
    host = host.split("/")[0].split(":")[0]   # drop any path/port remnants
    if host.startswith("www."):
        host = host[4:]
    for needle, name in DOMAIN_PUBLICATION.items():
        if needle in host:
            return name
    # Fall back to the registrable label, handling multi-part TLDs (e.g. .co.uk).
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 3 and parts[-2] in _TLD_SECOND_LEVEL:
        label = parts[-3]
    elif len(parts) >= 2:
        label = parts[-2]
    else:
        label = host
    return label.replace("-", " ").title() if label else "Unknown"


_TRACKER_HOSTS = ("substack.com", "list-manage.com", "mailchimp", "sendgrid",
                  "beehiiv.com", "ct.sendgrid", "click.")


def canonicalize_url(url: str) -> str:
    """Strip query/fragment and normalize, so trackers don't leak into output.

    Returns "" for obvious redirect/tracker URLs that can't be cleaned.
    """
    if not url:
        return ""
    try:
        p = urlparse(url.strip())
    except ValueError:
        return ""
    if p.scheme not in ("http", "https"):
        return ""
    host = (p.netloc or "").lower()
    path = p.path or ""
    # Substack redirect form: substack.com/redirect/<id>
    if "substack.com" in host and "/redirect/" in path:
        return ""
    cleaned = urlunparse((p.scheme, p.netloc, path.rstrip("/"), "", "", ""))
    return cleaned


def normalize_for_dedup(url: str) -> str:
    """Aggressive normalization for cross-source dedup comparison."""
    c = canonicalize_url(url)
    if not c:
        return ""
    p = urlparse(c)
    host = p.netloc.lower().lstrip("www.")
    return f"{host}{p.path.rstrip('/').lower()}"


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation/whitespace for title-similarity dedup."""
    t = (title or "").lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()

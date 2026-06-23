"""Assemble fetched stories + summarized sections into the build_pdf content dict.

Handles cross-source dedup (Gmail wins), date ordering, byline/bibliography
formatting, issue numbering, and the cover/closing metadata.
"""
from __future__ import annotations

from datetime import date

from .config import Config
from .models import Story, normalize_for_dedup, normalize_title

_MONTHS = ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]
_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"]


def _md(d: date) -> str:                      # "May 11"
    return f"{_MONTHS[d.month]} {d.day}"


def _mdy(d: date) -> str:                     # "May 11, 2026"
    return f"{_MONTHS[d.month]} {d.day}, {d.year}"


def _weekday_md(d: date) -> str:              # "Monday, May 11"
    return f"{_WEEKDAYS[d.weekday()]}, {_md(d)}"


def _weekday_mdy(d: date) -> str:             # "Sunday, May 17, 2026"
    return f"{_WEEKDAYS[d.weekday()]}, {_mdy(d)}"


def dedup_and_order(gmail: list[Story], reeder: list[Story]) -> list[Story]:
    """Gmail wins: drop any Reeder story matching a Gmail one by URL or title.
    Return the combined list ordered by publish date (earliest first).
    """
    gmail_urls = {normalize_for_dedup(u) for s in gmail for u in s.urls}
    gmail_urls.discard("")
    gmail_titles = {normalize_title(s.title) for s in gmail}

    kept_reeder = []
    for s in reeder:
        if normalize_for_dedup(s.primary_url) in gmail_urls:
            continue
        if normalize_title(s.title) in gmail_titles:
            continue
        kept_reeder.append(s)

    combined = gmail + kept_reeder
    combined.sort(key=lambda s: (s.published, s.publication.lower()))
    return combined


def _byline(story: Story) -> str:
    authors = ", ".join(a for a in story.authors if a).strip()
    pub = story.publication
    date = _mdy(story.published)
    if authors and authors.lower() != pub.lower():
        return f"By {authors} · {pub} · {date}"
    return f"{pub} · {date}"


def _bibliography(stories: list[Story]) -> list[dict]:
    groups: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for s in stories:
        key = (s.publication, s.published.isoformat())
        if key not in groups:
            groups[key] = {"heading": f"{s.publication} — {_mdy(s.published)}",
                           "entries": []}
            order.append(key)
        author = ", ".join(a for a in s.authors if a) or s.publication
        citation = f"{author}. {s.title}. {_mdy(s.published)}."
        groups[key]["entries"].append(
            {"citation": citation, "url": s.primary_url or ""}
        )
    return [groups[k] for k in order]


def build_content(cfg: Config, stories: list[Story], sections: list[dict],
                  toc: list[dict]) -> dict:
    """Combine everything into the dict build_pdf expects."""
    full_sections = []
    for story, sec in zip(stories, sections):
        full_sections.append({
            "kicker": sec["kicker"],
            "headline": sec["headline"],
            "byline": _byline(story),
            "deck": sec["deck"],
            "subsections": sec["subsections"],
        })

    compiled = date.today()
    issue = cfg.issue_number
    return {
        "cover": {
            "subtitle": "A curated meta-newsletter of the week's reading",
            "issue_number": issue,
            "coverage_start": _weekday_md(cfg.coverage_start),
            "coverage_end": _weekday_mdy(cfg.coverage_end),
            "compiled_date": _mdy(compiled),
            "compiled_for": cfg.compiled_for,
        },
        "toc": toc,
        "sections": full_sections,
        "briefer_notes": [],
        "bibliography": _bibliography(stories),
        "closing_line": (
            f"End of Issue {issue}. Compiled {_mdy(compiled)} from "
            f"newsletter-tagged emails and read-later articles received between "
            f"{_weekday_md(cfg.coverage_start)} and {_weekday_mdy(cfg.coverage_end)}."
        ),
    }

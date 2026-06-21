#!/usr/bin/env python3
"""Fetch read-later articles from a Reeder shared JSON Feed.

Step one of a larger automation. The new Reeder publishes a public JSON Feed
(JSON Feed 1.1, hosted on reederapp.net) for any shared tag, e.g. "Later".
This module fetches that feed, normalizes each entry into an Article, tracks
already-seen IDs across runs, and emits only new items so downstream steps
process each article once.

Note: a Reeder shared feed contains only the last 50 items added to the tag.
Run frequently enough that fewer than 50 new items accumulate between runs,
otherwise older entries roll off before being captured.

Usage:
    python reeder_read_later.py --url "https://reederapp.net/..." --format csv
    python reeder_read_later.py --url "..." --all          # ignore state
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
import urllib.error
import urllib.request
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path

USER_AGENT = "reeder-read-later-fetch/1.0"


@dataclass
class Article:
    id: str
    url: str
    title: str
    summary: str
    content_html: str
    date_published: str
    authors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def fetch_feed(url: str, timeout: float = 30.0) -> dict:
    """Retrieve, decompress, and decode the JSON Feed at url.

    Reeder serves the shared feed via a 302 redirect to a compressed body.
    urllib follows the redirect automatically but does not decompress, so the
    Content-Encoding header (with a gzip magic-byte fallback) is handled here.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/feed+json, application/json, */*",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        encoding = (resp.headers.get("Content-Encoding") or "").lower()

    if encoding == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    elif encoding == "deflate":
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)  # raw deflate
    elif encoding == "br":
        raise RuntimeError(
            "feed is Brotli-encoded; install the 'brotli' package and decode, "
            "or request identity encoding"
        )

    return json.loads(raw.decode("utf-8"))


def parse_items(feed: dict) -> list[Article]:
    """Normalize JSON Feed items into Article records (handles 1.0 and 1.1)."""
    articles: list[Article] = []
    for it in feed.get("items", []):
        authors = [a["name"] for a in it.get("authors", []) if a.get("name")]
        if not authors and isinstance(it.get("author"), dict):  # 1.0 fallback
            name = it["author"].get("name")
            if name:
                authors.append(name)
        articles.append(
            Article(
                id=str(it.get("id") or it.get("url") or ""),
                url=it.get("url", ""),
                title=(it.get("title") or "").strip(),
                summary=(it.get("summary") or "").strip(),
                content_html=it.get("content_html") or it.get("content_text") or "",
                date_published=it.get("date_published", ""),
                authors=authors,
                tags=it.get("tags", []),
            )
        )
    return articles


def load_seen(state_path: Path) -> set[str]:
    if state_path.exists():
        return set(json.loads(state_path.read_text()))
    return set()


def save_seen(state_path: Path, seen: set[str]) -> None:
    state_path.write_text(json.dumps(sorted(seen)))


def filter_new(articles: list[Article], seen: set[str]) -> list[Article]:
    return [a for a in articles if a.id and a.id not in seen]


def write_jsonl(articles: list[Article], out: Path) -> None:
    with out.open("w", encoding="utf-8") as f:
        for a in articles:
            f.write(json.dumps(asdict(a), ensure_ascii=False) + "\n")


def write_csv(articles: list[Article], out: Path) -> None:
    fields = ["id", "url", "title", "summary", "date_published", "authors", "tags"]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for a in articles:
            row = asdict(a)
            row["authors"] = "; ".join(a.authors)
            row["tags"] = "; ".join(a.tags)
            w.writerow({k: row[k] for k in fields})


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True, help="Reeder shared JSON Feed URL (reederapp.net)")
    p.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    p.add_argument("--output", type=Path, default=Path("read_later"),
                   help="Output path without extension")
    p.add_argument("--state", type=Path, default=Path(".reeder_seen.json"),
                   help="Tracks processed item IDs so each run emits only new entries")
    p.add_argument("--all", action="store_true",
                   help="Ignore state and emit every item currently in the feed")
    args = p.parse_args(argv)

    try:
        feed = fetch_feed(args.url)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"fetch failed: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"feed is not valid JSON: {e}", file=sys.stderr)
        return 1

    articles = parse_items(feed)
    seen = set() if args.all else load_seen(args.state)
    new = filter_new(articles, seen)

    out = args.output.with_suffix(".jsonl" if args.format == "jsonl" else ".csv")
    (write_jsonl if args.format == "jsonl" else write_csv)(new, out)

    if not args.all:
        save_seen(args.state, seen | {a.id for a in articles if a.id})

    print(f"feed items: {len(articles)}  new: {len(new)}  written: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
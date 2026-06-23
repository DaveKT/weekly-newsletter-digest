"""Weekly digest pipeline entry point: python3 -m weekly_digest

Fetches Gmail + Reeder content for the prior week, summarizes via Claude
through OpenRouter, and renders the locked PDF to the output directory.
"""
from __future__ import annotations

import sys
import traceback

from . import assemble, extract, gmail_source, reeder_source, summarize
from .build_pdf import build_pdf
from .config import load_config, require


def _log(msg: str) -> None:
    print(f"[digest] {msg}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    cfg = load_config()
    require(cfg, "openrouter_api_key", "reeder_feed_url",
            "gmail_client_id", "gmail_client_secret", "gmail_refresh_token")
    _log(f"coverage {cfg.coverage_start} .. {cfg.coverage_end}  issue {cfg.issue_number}")

    gmail_stories = []
    try:
        gmail_stories = gmail_source.fetch(cfg)
        _log(f"gmail: {len(gmail_stories)} editorial emails")
    except Exception as e:
        _log(f"gmail fetch FAILED ({e}); continuing without it")
        traceback.print_exc()

    reeder_stories = []
    try:
        reeder_stories = reeder_source.fetch(cfg)
        _log(f"reeder: {len(reeder_stories)} items in window")
    except Exception as e:
        _log(f"reeder fetch FAILED ({e}); continuing without it")
        traceback.print_exc()

    stories = assemble.dedup_and_order(gmail_stories, reeder_stories)
    _log(f"after dedup/order: {len(stories)} stories")
    if not stories:
        _log("no qualifying content this week; not producing an empty PDF.")
        return 2

    extract.enrich(stories)

    sections = []
    for i, s in enumerate(stories, 1):
        _log(f"summarizing {i}/{len(stories)}: {s.publication} — {s.title[:60]}")
        try:
            sections.append(summarize.summarize_story(cfg, s))
        except Exception as e:
            _log(f"  summarize failed ({e}); using fallback section")
            sections.append(summarize.fallback_section(s))

    toc = summarize.build_toc(cfg, sections)
    _log(f"toc: {len(toc)} entries")

    content = assemble.build_content(cfg, stories, sections, toc)

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg.output_dir / f"weekly_digest_{cfg.issue_number}.pdf"
    build_pdf(content, str(out_path))
    _log(f"wrote {out_path}")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

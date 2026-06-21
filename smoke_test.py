"""Offline smoke test: config + reeder fetch + dedup + assemble + render.
Skips the Gmail and OpenRouter calls (those need secrets). Uses a stub
summarizer so the full content->PDF path is exercised with real Reeder data.
"""
import os
from datetime import date

from weekly_digest import assemble, reeder_source
from weekly_digest.build_pdf import build_pdf
from weekly_digest.config import Config, previous_week
import weekly_digest.extract  # import-only: confirms trafilatura loads

FEED = os.environ.get("REEDER_FEED_URL", "https://reederapp.net/<your-feed-id>.json")


def stub_section(story):
    return {
        "kicker": f"{story.publication} · Read-later",
        "headline": story.title,
        "deck": (story.body_text[:240] or story.title).strip(),
        "subsections": [
            {"subhead": "Summary", "paragraphs": [(story.body_text[:600] or story.title).strip()]}
        ],
    }


def main():
    mon, sun = previous_week()
    print("default previous-week window:", mon, sun)

    cfg = Config(
        openrouter_api_key="x", openrouter_model="x",
        openrouter_base_url="x",
        gmail_client_id="x", gmail_client_secret="x", gmail_refresh_token="x",
        gmail_label="News Letter", reeder_feed_url=FEED,
        output_dir=__import__("pathlib").Path("/tmp"),
        compiled_for="Your Name",
        coverage_start=date(2026, 6, 1), coverage_end=date(2026, 6, 14),
    )
    print("issue number:", cfg.issue_number)

    reeder = reeder_source.fetch(cfg)
    print(f"reeder items in {cfg.coverage_start}..{cfg.coverage_end}: {len(reeder)}")
    for s in reeder[:5]:
        print(f"  - {s.published} | {s.publication} | {s.title[:55]}")

    stories = assemble.dedup_and_order([], reeder)
    sections = [stub_section(s) for s in stories]
    toc = [{"title": s["headline"][:40], "blurb": "sample blurb for smoke test"}
           for s in sections[:5]]
    content = assemble.build_content(cfg, stories, sections, toc)
    print("cover:", content["cover"]["coverage_start"], "->", content["cover"]["coverage_end"])
    print("sections:", len(content["sections"]), "| biblio groups:", len(content["bibliography"]))

    out = f"/tmp/smoke_digest_{cfg.issue_number}.pdf"
    build_pdf(content, out)
    import os
    print(f"PDF written: {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()

"""Summarization via Claude through OpenRouter.

Each story is turned into one structured "section" (kicker, headline, deck,
subsections) matching build_pdf's content schema. A final editor pass selects
the cover TOC. Bylines and bibliography are assembled from metadata elsewhere,
so the model never invents authors, dates, or URLs.
"""
from __future__ import annotations

import json
import re
import time

import requests

from .config import Config
from .models import Story

MAX_BODY_CHARS = 32_000
_TIMEOUT = 120


def _chat(cfg: Config, system: str, user: str, *, max_tokens: int = 2000) -> str:
    headers = {
        "Authorization": f"Bearer {cfg.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-username/weekly-newsletter-digest",
        "X-Title": "Weekly Newsletter Digest",
    }
    payload = {
        "model": cfg.openrouter_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }
    last_err = None
    for attempt in range(4):
        try:
            r = requests.post(
                f"{cfg.openrouter_base_url}/chat/completions",
                headers=headers, json=payload, timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"].get("content") or ""
                if content.strip():
                    return content
                last_err = "empty content in 200 response"  # transient; retry
            else:
                last_err = f"HTTP {r.status_code}: {r.text[:300]}"
        except (requests.RequestException, KeyError, ValueError) as e:
            last_err = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"OpenRouter request failed after retries: {last_err}")


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


_SECTION_SYSTEM = (
    "You are an editor compiling a weekly meta-newsletter. You write concise, "
    "factual prose summaries in your own words. Never paste source text. Keep "
    "any direct quotation under 15 words and at most one per piece; prefer "
    "paraphrase. Preserve concrete facts: numbers, names, versions, dates, "
    "dollar amounts. Respond with a single JSON object only."
)


def summarize_story(cfg: Config, story: Story) -> dict:
    """Return a section dict: kicker, headline, deck, subsections."""
    body = story.body_text.strip()[:MAX_BODY_CHARS]
    schema = (
        '{"kicker": "Topic · Subtopic", "headline": "string, no trailing period", '
        '"deck": "2-3 sentence lead paragraph", "subsections": '
        '[{"subhead": "string", "paragraphs": ["string", "..."], '
        '"quote": {"text": "<15 words", "attribution": "string"}}]}'
    )
    user = (
        f"Publication: {story.publication}\n"
        f"Original title: {story.title}\n"
        f"Date: {story.published.isoformat()}\n\n"
        f"CONTENT:\n{body}\n\n"
        "Write a summary section. Use 2-3 subsections for a short piece, up to "
        "6-8 for a long multi-story newsletter, one subhead per major beat. "
        "The 'quote' field is optional; omit it unless a short verbatim quote "
        "genuinely adds value. Match this JSON shape exactly:\n" + schema
    )
    data = _parse_json(_chat(cfg, _SECTION_SYSTEM, user, max_tokens=2600))
    # Defensive normalization.
    subs = data.get("subsections") or [{"subhead": story.title,
                                         "paragraphs": [data.get("deck", "")]}]
    clean_subs = []
    for s in subs:
        paras = [p for p in (s.get("paragraphs") or []) if p and p.strip()]
        if not paras:
            continue
        sub = {"subhead": (s.get("subhead") or "").strip(), "paragraphs": paras}
        q = s.get("quote")
        if isinstance(q, dict) and q.get("text"):
            sub["quote"] = {"text": q["text"].strip(),
                            "attribution": (q.get("attribution") or "").strip()}
        clean_subs.append(sub)
    return {
        "kicker": (data.get("kicker") or story.publication).strip(),
        "headline": (data.get("headline") or story.title).strip(),
        "deck": (data.get("deck") or "").strip(),
        "subsections": clean_subs or [{"subhead": story.title,
                                       "paragraphs": [story.body_text[:400]]}],
    }


def fallback_section(story: Story) -> dict:
    """Minimal section built without the LLM, for when summarization fails."""
    text = (story.body_text or story.title).strip()
    return {
        "kicker": story.publication,
        "headline": story.title,
        "deck": text[:300] or story.title,
        "subsections": [{"subhead": "Summary", "paragraphs": [text[:800] or story.title]}],
    }


_TOC_SYSTEM = (
    "You select the cover table-of-contents for a weekly digest. Respond with "
    "a single JSON object only."
)


def build_toc(cfg: Config, sections: list[dict]) -> list[dict]:
    """Pick 5 (max 6) varied TOC entries from the section list."""
    catalog = [
        {"i": i, "headline": s["headline"], "deck": s.get("deck", "")[:200]}
        for i, s in enumerate(sections)
    ]
    user = (
        "From these sections, choose the 5 most interesting and varied for the "
        "cover (absolute maximum 6). Favor distinct topics over multiple picks "
        "from one source. For each, write a short title (3-6 words) and a blurb "
        "of 8-14 words. No trailing periods in either field.\n\n"
        f"SECTIONS:\n{json.dumps(catalog, ensure_ascii=False)}\n\n"
        'Respond as JSON: {"toc": [{"title": "string", "blurb": "string"}]}'
    )
    data = _parse_json(_chat(cfg, _TOC_SYSTEM, user, max_tokens=900))
    toc = data.get("toc") or []
    out = []
    for e in toc[:6]:
        title = (e.get("title") or "").strip().rstrip(".")
        blurb = (e.get("blurb") or "").strip().rstrip(".")
        if title and blurb:
            out.append({"title": title, "blurb": blurb})
    return out

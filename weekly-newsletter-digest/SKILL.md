---
name: weekly-newsletter-digest
description: "Generate a polished PDF meta-newsletter from two sources: (1) emails tagged with the \"News Letter\" label in Gmail and (2) articles saved to the Reeder read-later feed, covering a Mon–Sun week. Use this skill whenever the user asks for a weekly newsletter digest, weekly reading roundup, or meta-newsletter PDF, and especially when scheduled to run automatically each Sunday morning. Trigger on phrases like \"build my weekly digest\", \"compile this week's newsletters\", \"run my Sunday newsletter recap\", or any reference to compiling newsletter-tagged emails into a PDF. Always use this skill rather than improvising the layout from scratch — the design, issue-numbering scheme, and bibliography format are part of the deliverable."
---

# Weekly Newsletter Digest

Compile newsletter-tagged Gmail messages **and** Reeder read-later articles from a Mon–Sun week into a designed PDF with a navy/teal/gold magazine-style cover, story-by-story summaries, and a clickable bibliography.

## When the skill runs

This skill is intended to run on a schedule (Sunday morning, 8 AM). When triggered:

1. The default coverage period is the **previous Monday through Sunday** (the just-completed week). Today is Sunday by default, so the range is `[today - 7 days, today - 1 day]` — i.e., last Mon through last Sun.
2. If the user explicitly names a different week, honor that instead.
3. The skill produces one PDF named `weekly_digest_<issue>.pdf` and presents it to the user.

## High-level workflow

The workflow has five phases. Don't skip phases — each one feeds the next.

1. **Fetch** newsletter emails from Gmail for the week.
2. **Fetch** read-later articles from the Reeder shared feed for the week.
3. **Extract** content from both sources; for link-only items, fetch the linked articles and summarize them.
4. **Compose** the digest content as a Python dict matching `references/content_schema.md`.
5. **Render** the PDF using the bundled `scripts/build_pdf.py`.

## Phase 1 — Fetch newsletter emails from Gmail

The Gmail label is **"News Letter"** (with a space). Always look it up fresh via `Gmail:list_labels` and match by display name `"News Letter"`, since the underlying label ID is account-specific.

Use `Gmail:search_threads` with this query template:

```
label:"News Letter" after:YYYY/MM/DD before:YYYY/MM/DD
```

The `before:` date in Gmail is **exclusive**, so to cover Mon–Sun, use `after:<Mon>` and `before:<Mon+7>` (the next Monday).

Set `pageSize: 50`. Paginate if the response includes a next page token.

Then call `Gmail:get_thread` with `messageFormat: FULL_CONTENT` for each thread to retrieve `plaintextBody`.

### Filter out non-editorial emails

Not every email under the "News Letter" label is a story. Exclude:
- Sign-in / verification codes (subjects containing "verification code", "Sign in", "code <digits>")
- Subscription renewal notices and discount offers ("subscription is renewing", "discount offer for you")
- Welcome / confirmation emails for new subscriptions ("Welcome to", "Thank you for subscribing") — list under "Briefer notes" only if completeness is desired; usually skip
- Marketing-only blasts that contain only a CTA and no editorial content (e.g., "Last chance to register")

When in doubt, glance at the body length and structure — editorial newsletters typically have 1,000+ characters of plaintext with multiple links. Skip empty/near-empty bodies that are pure CTA.

## Phase 2 — Fetch read-later articles from Reeder

The Reeder shared feed is a public JSON Feed 1.1 endpoint. Fetch it every run — do not rely on cached or exported data.

**Feed URL (hardcoded):**
```
https://reederapp.net/<your-feed-id>.json
```

### Fetching the feed

**Primary method — bundled fetcher.** Use the bundled `scripts/reeder_read_later.py`, which was purpose-built for this endpoint. It is important to use it rather than fetching the URL naively, because this endpoint:

- responds with an **HTTP 302 redirect** to the actual body, and
- returns a **compressed** body (gzip/deflate).

The script handles both, normalizes each item, and emits one JSON object per line. Run it with `--all` (the skill does its own date filtering in the next step, so do not rely on the script's incremental seen-state here):

```bash
python3 scripts/reeder_read_later.py \
  --url https://reederapp.net/<your-feed-id>.json \
  --all --format jsonl --output /tmp/reeder_week
```

Then read `/tmp/reeder_week.jsonl` (one Article JSON object per line) into the pipeline.

If the script reports a `feed:` scheme error, strip a leading `feed:` from the URL and retry with the plain `https://` form. If it reports a Brotli (`br`) encoding error, that is the one compression case it cannot decode — fall back to `web_fetch` (below).

**Fallback method — `web_fetch`.** If the skill's runtime cannot execute the script with network access, `web_fetch` the feed URL directly and parse the response body as JSON. This is less robust (the endpoint's redirect and compression behavior can cause `web_fetch` to return non-JSON), so prefer the bundled script.

### Item fields

The feed follows the [JSON Feed 1.1](https://www.jsonfeed.org/version/1.1/) spec; the bundled script normalizes each item into an `Article` with these fields:

| Field | Type | Notes |
|---|---|---|
| `id` | str | Unique item identifier |
| `url` | str | Canonical article URL |
| `title` | str | Article title |
| `content_html` | str | HTML content. In practice usually full article text (median ~7k chars), occasionally an excerpt. |
| `content_text` | str | Plain-text content (fallback if no HTML) |
| `date_published` | str | ISO 8601 timestamp, e.g. `2026-06-10T01:00:31Z` |
| `authors` | list[str] | Author/source names. **Often a site or domain name** (e.g. `read.write.as`), not a person — factor this into the byline. |
| `tags` | list | Usually empty on this shared feed; do not rely on it for filtering. |

### Filter to the coverage week

Only include items whose `date_published` falls within the coverage period (Monday 00:00:00 through Sunday 23:59:59 of the target week). Parse the ISO 8601 timestamp, compare the date portion, and discard items outside the window.

The feed contains only the last ~50 items. If no items fall within the coverage week, that is normal — proceed with Gmail content only.

### Filter out non-editorial items

Apply the same editorial filter as Gmail content. Exclude:
- Items with no `title` or no `url`
- Items whose title suggests non-editorial content (sign-in codes, subscription notices, marketing blasts)
- Items with very short `content_text` (under ~200 characters) and no `content_html` — these are likely bookmarks with no extractable content; list under "Briefer notes" only if the title is informative

### Deduplication against Gmail

Before adding Reeder articles to the content pipeline, deduplicate against Gmail newsletter stories. **Gmail takes priority** — if a story appears in both sources, skip the Reeder copy.

Match by URL: normalize both the Gmail article URL and the Reeder item `url` by stripping trailing slashes, query parameters (especially UTM trackers), and fragments, then compare. Also match by title similarity — if a Reeder item's title is a close match (case-insensitive, ignoring leading/trailing whitespace and punctuation) to a Gmail story headline, treat it as a duplicate.

## Phase 3 — Extract content

Process Gmail emails and Reeder articles together. For each item from either source:

### From Gmail emails

1. **Identify the publication, author(s), and date** from the headers and body. The publication is usually inferable from the sender domain (e.g., `weekly@macstories.net` → MacStories; `support@tidbits.com` → TidBITS; `members@sixcolors.com` → Six Colors; `simonw@substack.com` → Simon Willison's Newsletter; `404-media@ghost.io` → 404 Media; `mail@posts.memberful.com` with "MacSparky Labs" in body → MacSparky Labs; `emailteam@emails.hbr.org` → Harvard Business Review).
2. **Note the section/story structure.** Many newsletters bundle multiple stories. Treat each story as its own subsection in the PDF.
3. **Strip tracking redirects when collecting source URLs.** Substack `substack.com/redirect/<id>` URLs and similar redirects should be replaced with the canonical publisher URL whenever it can be identified. If the canonical URL cannot be recovered, omit the link rather than ship a tracker.
4. **For link-only newsletters** (body says "your email software can't display HTML emails" or the email contains only a redirect with no editorial text), always fetch the linked article via `web_fetch` and summarize from that. Six Colors emails frequently arrive in this form. If `web_fetch` is blocked on the redirect URL, use `web_search` with the newsletter title and date to find the canonical article, then fetch that.
5. **For video-led newsletters** (e.g., MacSparky Labs) where the body has only a snippet, use the snippet to write a short note rather than fetching anything else. List those under a "Briefer notes" section near the back.

### From Reeder articles

1. **Identify the publication and author(s)** from the `authors` field and the `url` domain. Infer the publication name from the domain (e.g., `arstechnica.com` → Ars Technica, `theverge.com` → The Verge). If the domain is a personal blog or unrecognizable, use the domain name as-is.
2. **Extract the date** from `date_published`.
3. **Assess content completeness.** If `content_html` or `content_text` contains enough text for a meaningful summary (roughly 500+ characters of prose), summarize from that. If the feed item contains only a title and URL (or very short content), fetch the full article via `web_fetch` using the item's `url`, then summarize from the fetched content.
4. **Strip tracking redirects** from the `url` field, same rules as Gmail.
5. **For items where `web_fetch` fails**, use `web_search` with the article title to find an accessible copy, then fetch that. If all attempts fail, list the item under "Briefer notes" with whatever is known (title, author, one-line description from the feed).

### Summarization style

Write prose summaries in original words, not pasted email text or feed content. Each story gets:

- A short lead paragraph (2–3 sentences) that frames what the piece is about.
- One or more sub-headed paragraphs covering the story's key points (one sub-head per major beat).
- Concrete facts: numbers, names, product versions, dates, and dollar amounts should appear in the summary because they're what makes the digest useful as a reference.
- Keep direct quotations rare and short (well under 15 words each, at most one per source). Default to paraphrase.

Match the depth of summary to the source. A long Simon Willison or 404 Media issue with multiple distinct stories warrants 4–8 sub-sections; a short HBR Insider column may need only 2. A typical Reeder article (single piece, not a bundled newsletter) usually warrants 2–4 sub-sections.

## Phase 4 — Compose the content payload

**Read `references/content_schema.md` first.** It contains the authoritative field-by-field spec, types, and a worked minimal example.

The top-level shape:

```python
content = {
    "cover": {
        "subtitle": "A curated meta-newsletter of the week's reading",
        "issue_number": "26132",
        "coverage_start": "Monday, May 11",
        "coverage_end": "Sunday, May 17, 2026",
        "compiled_date": "May 18, 2026",
        "compiled_for": "Your Name",
    },
    "toc": [
        {"title": "...", "blurb": "..."},
        # 5 target, 6 cap
    ],
    "sections": [
        {
            "kicker": "Apple · How-To",
            "headline": "...",
            "byline": "By Author · Publication · Date",
            "deck": "...",                          # lead paragraph
            "subsections": [
                {"subhead": "...",
                 "paragraphs": ["...", "..."],
                 "quote": {"text": "...", "attribution": "..."}},  # quote optional
            ],
        },
    ],
    "briefer_notes": [
        {"headline": "...", "body": "..."},        # optional; omit to skip the page
    ],
    "bibliography": [
        {"heading": "Publication Name — Date",
         "entries": [
             {"citation": "Author. Title. Date.",
              "url": "https://..."},
         ]},
    ],
    "closing_line": "End of Issue 26132. Compiled May 18, 2026 from newsletter-tagged emails and read-later articles received between Monday, May 11 and Sunday, May 17, 2026.",
}
```

### Ordering sections

Gmail newsletter stories and Reeder articles are **mixed together** in the `sections` list. Order them by **date published** (earliest first), regardless of source. If two items share the same date, order by thematic grouping (cluster related topics together) or alphabetically by publication name.

There is no visual distinction between Gmail-sourced and Reeder-sourced sections in the PDF. Both use the same kicker/headline/byline/subsection structure.

### Issue number

The issue number uses a **Julian-style** scheme: two-digit year + day-of-year for the **first day** of the coverage period, with a +1 offset. Use this exact formula:

```python
from datetime import date
d = coverage_start_date  # the Monday
issue_number = f"{d.year % 100:02d}{d.timetuple().tm_yday + 1:03d}"
```

Verification: May 11, 2026 → year_suffix=26, DOY=131, +1 = 132 → `"26132"`.

### TOC entries

The "In This Issue" list on the cover has a **hard cap of 6 entries** and a **preferred target of 5**. The cover layout is fixed; more than 6 entries — or 6 entries with long blurbs — overflows the lower frame and looks unbalanced.

**Rules:**

1. **Cap: 6 entries maximum. Target: 5.** Start by drafting 5; only add a sixth if a clearly distinct theme is not covered by the first five.
2. **Blurb length budget.** Each blurb should be **one short clause, roughly 8–14 words**, never a full sentence with subordinate phrasing. Treat ~14 words as the soft ceiling for any single blurb when the list has 6 items.
3. **Monitor combined length before rendering.** At 6 entries, the average blurb must stay near the lower end of the range. If any blurb in a 6-entry list runs long (15+ words, or wraps to a third line at typical rendering), either:
   - **Tighten the offending blurb** to fit, or
   - **Drop to 5 entries**, removing the weakest pick.
4. **Pick for variety and thematic interest.** Choose entries that span the week's range of topics rather than stacking multiple sub-stories from the same source. Favor:
   - Pieces unique to the week (a one-off investigation, an anniversary feature, an unusual research finding) over routine roundups.
   - Items reflecting the reader's stated interests when relevant.
   - One representative pick per major source rather than three picks from MacStories.
   - **Reeder articles are eligible for the TOC** on equal footing with Gmail stories. A standout Reeder article can and should displace a weaker Gmail story in the TOC.
5. **Format.** The renderer outputs each entry as `<b>Title.</b> Blurb.` — do **not** include trailing periods in either field; the template adds them.

### Bibliography

Reeder articles appear in the bibliography alongside Gmail newsletter entries, grouped by publication and date in the same format. There is no separate bibliography section for Reeder content.

### Closing line

Update the closing line to reflect both sources:

```python
f"End of Issue {issue_number}. Compiled {compiled_date} from newsletter-tagged emails and read-later articles received between {coverage_start} and {coverage_end}."
```

## Phase 5 — Render the PDF

**The design is locked.** Do not modify `scripts/build_pdf.py` — neither the color palette, the cover layout coordinates, the typography, nor the chrome. The cover specifically uses:

- Full-bleed navy-teal background `#0e2a36`
- Teal `#2da1ba` bands at top (y=774, h=18) and bottom (y=0, h=14)
- Gold `#e8b34b` vertical hairline at x=43.2, gold dot at top, gold issue number (72pt) and "IN THIS ISSUE" header
- Cream `#f4ede2` title, tagline, and metadata text
- Light gray `#cccccc` TOC blurbs with cream-bold titles
- Helvetica family throughout
- Upper block (title through metadata) drawn at absolute Y coordinates on the canvas
- TOC anchored in a lower frame (y=30 to y=350) for magazine balance

Inner pages use:
- Slate `#6b6b6b` chrome ("THE WEEKLY DIGEST · ISSUE NNNNN" header, page numbers, footer)
- Light gray `#d8d8d8` hairline rules above and below content
- Teal `#2da1ba` kickers and hyperlinks
- Helvetica-Bold 22pt headlines, Helvetica-Oblique 10pt bylines, Helvetica 10.5pt body

If a design change is genuinely needed, ask the user first. Otherwise just call the renderer:

```python
import sys
sys.path.insert(0, "scripts")  # or wherever the skill lives
from build_pdf import build_pdf

build_pdf(content, f"/mnt/user-data/outputs/weekly_digest_{issue_number}.pdf")
```

After rendering, verify with `pypdf.PdfReader` that the page count is non-trivial (typically 10–20 pages for a normal week), then `present_files` the result.

## Output location & naming

- Path: `/mnt/user-data/outputs/weekly_digest_<issue_number>.pdf`
- Always use `present_files` to surface the PDF to the user at the end.

## Edge cases

- **No content from either source that week.** Don't produce an empty PDF. Tell the user the week had no qualifying emails or read-later articles and stop.
- **Gmail only, no Reeder items.** Proceed normally — the digest works fine with Gmail content alone (identical to v1 behavior).
- **Reeder only, no Gmail emails.** Still produce a PDF using only the Reeder articles. The layout is the same.
- **One or two items total.** Still produce a PDF; just keep TOC entries proportional to what's there.
- **An email's body fails to retrieve plaintext.** Fall back to the snippet plus a `web_search` for the article title; if both fail, list the item under "Briefer notes" with whatever is known.
- **Web fetch blocked on a tracker URL.** Don't repeatedly retry the redirect. Search by title and date to find the canonical URL, then fetch that.
- **Same story covered by two newsletters.** That's fine — each gets its own section. Don't try to merge.
- **Same story in Gmail and Reeder.** Skip the Reeder copy. Gmail takes priority.
- **Reeder feed is unreachable.** Log a warning and proceed with Gmail content only. Do not fail the entire run because the Reeder feed is down.

## Reference files

- `references/content_schema.md` — full content-dict schema with field-level notes, types, and a worked minimal example. **Read this before composing the content payload.**

## Bundled scripts

- `scripts/build_pdf.py` — the rendering engine. **Design is locked — do not modify** unless the user explicitly requests a design change.
- `scripts/reeder_read_later.py` — zero-dependency (stdlib only) fetcher for the Reeder shared JSON Feed. Handles the endpoint's 302 redirect and gzip/deflate compression. Used in Phase 2. See `--help` for flags.

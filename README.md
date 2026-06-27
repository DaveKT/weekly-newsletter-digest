# Weekly Newsletter Digest

A standalone Python pipeline that compiles a week of reading into a single,
designed PDF "meta-newsletter" — a navy/teal/gold magazine-style cover,
story-by-story summaries, and a clickable bibliography.

It runs entirely on your own machine (cron-friendly, no cloud sandbox), pulling
from two sources for a given Monday–Sunday week:

1. **Gmail** — emails tagged with a `News Letter` label (read-only Gmail API).
2. **Reeder** — articles saved to a [Reeder](https://reederapp.com/) read-later shared feed.

Stories from both sources are summarized by **Claude via [OpenRouter](https://openrouter.ai/)**,
de-duplicated (Gmail wins), mixed together by date, and rendered to a PDF.

> Published as a **reference example**. Secrets, the feed URL, and the recipient
> name are placeholders — see [SETUP.md](SETUP.md).

## Sample output

Rendered from synthetic placeholder content — no real names, articles, or subscriptions.

| Cover | Inner page |
|---|---|
| ![Sample digest cover](docs/sample-cover.png) | ![Sample digest inner page](docs/sample-page.png) |

## How it works

```
run.sh (cron entry)
  └─ source mysecrets  →  uv run python -m weekly_digest
        1. fetch_gmail    — News Letter-labeled emails in the Mon–Sun window
        2. fetch_reeder   — read-later items, date-filtered to the same window
        3. dedup          — Gmail wins on overlap
        4. extract        — trafilatura pulls full text for link-only/thin items
        5. summarize      — Claude (OpenRouter) → structured JSON sections + TOC
        6. assemble       — content dict + bibliography + issue number
        7. render         — build_pdf.py → ~/Desktop/weekly_digest_<issue>.pdf
```

Dependencies are managed by **[uv](https://docs.astral.sh/uv/)** from
`pyproject.toml`, so cron never touches a hand-built virtualenv. The PDF layout
is intentionally **locked** (palette, cover coordinates, typography) — it's part
of the deliverable, not improvised per run.

Reeder items are filtered by **save date** (when you added them to the read-later
tag), not the article's publish date. Run `./run.sh --since-last-run` for an
on-demand interim report of everything new since the last interim run; it keeps
its own state and never affects the scheduled weekly window.

## Layout

```
weekly-newsletter-digest/
├── run.sh                 # cron entry: sources mysecrets, runs the pipeline via uv
├── gmail_auth.py          # one-time: mints the Gmail read-only refresh token
├── mysecrets.example      # secrets template (copy → mysecrets, gitignored)
├── smoke_test.py          # offline self-test: Reeder + render, no secrets
├── pyproject.toml         # dependencies (managed by uv)
├── SETUP.md               # full setup + cron instructions
└── weekly_digest/
    ├── config.py          # env, Mon–Sun window, issue number
    ├── gmail_source.py    # Gmail API (read-only OAuth)
    ├── reeder_source.py   # date-filtered Reeder feed
    ├── reeder_read_later.py  # zero-dependency Reeder JSON-feed fetcher
    ├── extract.py         # trafilatura full-text extraction
    ├── summarize.py       # Claude via OpenRouter → structured JSON
    ├── assemble.py        # dedup, ordering, bibliography, content dict
    └── build_pdf.py       # the locked ReportLab renderer
```

## Quick start

```bash
git clone https://github.com/<you>/weekly-newsletter-digest
cd weekly-newsletter-digest
cp mysecrets.example mysecrets && chmod 600 mysecrets   # then fill it in
./run.sh
```

Full instructions — Gmail OAuth, OpenRouter, and cron — are in **[SETUP.md](SETUP.md)**.

## Configuration

All settings come from environment variables, sourced from `mysecrets`:

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter key for summarization |
| `OPENROUTER_MODEL` | e.g. `anthropic/claude-sonnet-4.6` or `~anthropic/claude-sonnet-latest` |
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` | Read-only Gmail API auth (see `gmail_auth.py`) |
| `GMAIL_LABEL` | Gmail label to compile (default `News Letter`) |
| `REEDER_FEED_URL` | Your Reeder shared feed (the `.json` suffix is required) |
| `DIGEST_OUTPUT_DIR` | Where the PDF lands (default `~/Desktop`) |
| `DIGEST_COMPILED_FOR` | Recipient name on the cover |
| `DIGEST_WEEK_START` / `DIGEST_WEEK_END` | Optional `YYYY-MM-DD` override of the default previous-week window |

## The Reeder fetcher

`weekly_digest/reeder_read_later.py` is a standalone, standard-library-only
fetcher for a Reeder shared JSON Feed (JSON Feed 1.1). It handles the endpoint's
302 redirect to compressed object storage and the JSON Feed 1.0/1.1 author-field
differences. The shared feed only holds the last ~50 items, so run often enough
that items don't roll off before capture. Note the `.json` suffix is required on
the feed URL.

## Cost

The Google/Gmail side is free (well within the Gmail API's free quota; no billing
account needed). The only cost is OpenRouter summarization — roughly a few dollars
a month, prepaid so you set the ceiling. Pick a cheaper model slug to reduce it.

## License

[MIT](LICENSE). This project began as a Claude Code skill and was rewritten as a
standalone pipeline so it can run unattended via cron.

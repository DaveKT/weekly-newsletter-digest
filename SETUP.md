# Weekly Newsletter Digest — setup

A self-contained Python pipeline that builds the weekly digest PDF entirely
on your machine, with no Claude Code / app sandbox involved:

1. **Gmail** — reads `News Letter`-labeled mail via the Gmail API (read-only).
2. **Reeder** — pulls read-later items from the shared JSON feed.
3. **Summarize** — sends each story to Claude via **OpenRouter**.
4. **Render** — `build_pdf.py` writes `weekly_digest_<issue>.pdf`.

Dependencies are managed by **uv** — you never create a venv by hand.

> Clone the repo, then run all commands from its root (`cd weekly-newsletter-digest`).

## One-time setup

### 1. Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS/Linux
uv --version                                       # confirm it's on PATH
```

### 2. OpenRouter API key
Create a key at https://openrouter.ai/keys and add a few dollars of credit at
https://openrouter.ai/credits (prepaid; it can't overspend). You'll paste the
key into `mysecrets`. For the model, either pin a version
(`anthropic/claude-sonnet-4.6`) or use the auto-latest alias
(`~anthropic/claude-sonnet-latest`, note the leading `~`). Browse slugs at
https://openrouter.ai/models.

### 3. Gmail API (read-only OAuth)
1. In https://console.cloud.google.com, create a project.
2. **APIs & Services → Library → Gmail API → Enable.**
3. **OAuth consent screen:** choose **External** and add your own address as a
   **Test user** (or **Internal** if this is a Google Workspace account).
4. **Credentials → Create credentials → OAuth client ID → Desktop app.**
   Download the JSON (e.g. `~/Downloads/client_secret.json`).
5. Mint a refresh token (opens a browser for consent — approve with the account
   that holds your newsletters):
   ```bash
   uv run python gmail_auth.py ~/Downloads/client_secret.json
   ```
   It prints `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`.

> Workspace note: if your domain blocks third-party app access, an admin must
> allow this app in **Admin console → Security → API controls**.

### 4. Fill in secrets
```bash
cp mysecrets.example mysecrets
chmod 600 mysecrets
# edit mysecrets: OpenRouter key + model, the three Gmail values,
# your REEDER_FEED_URL, and DIGEST_COMPILED_FOR.
```
`mysecrets` is gitignored — never commit it.

## Test run
```bash
./run.sh
```
On success it prints the PDF path (default `~/Desktop/weekly_digest_<issue>.pdf`).
To test a specific past week, set `DIGEST_WEEK_START` / `DIGEST_WEEK_END`
(`YYYY-MM-DD`) in `mysecrets`.

### Interim report (on demand)
```bash
./run.sh --since-last-run
```
Covers everything new since the last interim run — Gmail received and Reeder
items **saved** since then (first run seeds to 7 days ago). It uses its own
state file (`.reeder_interim_state.json`) and does **not** affect the scheduled
weekly window: the next cron run still produces the full previous-week digest.
Reeder filtering is by save date, so a recently-saved older article is included.

An offline self-test (Reeder + render only — no Gmail/OpenRouter, no secrets)
is available. Point it at any public Reeder feed:
```bash
REEDER_FEED_URL="https://reederapp.net/<your-feed-id>.json" uv run python smoke_test.py
```

## Schedule with cron
Run every Sunday at 08:00:
```bash
crontab -e
```
Add (use the absolute path to your checkout):
```
0 8 * * 0  /path/to/weekly-newsletter-digest/run.sh >> "$HOME/weekly_digest.log" 2>&1
```
`run.sh` sets `PATH` so cron can find `uv`, sources `mysecrets`, and runs the
pipeline. Check `~/weekly_digest.log` after the first scheduled run.

## Notes
- The PDF design in `weekly_digest/build_pdf.py` is locked — don't edit it
  unless you want a design change.
- If Gmail or Reeder fails on a given week, the run logs the error and proceeds
  with whatever source succeeded rather than aborting.
- Exit code `2` means there was no qualifying content that week (no PDF written).

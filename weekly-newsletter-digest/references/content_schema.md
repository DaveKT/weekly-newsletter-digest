# Content schema for `build_pdf.py`

The renderer `scripts/build_pdf.py` consumes a single Python dict named `content`. The shape below is **authoritative**. Adding extra keys is harmless; missing required keys will raise a KeyError at render time.

## Top-level structure

```python
content = {
    "cover": { ... },              # required, dict
    "toc": [ ... ],                # required, list of TOC items (5 target, 6 cap)
    "sections": [ ... ],           # required, list of story sections
    "briefer_notes": [ ... ],      # optional, list of brief items
    "bibliography": [ ... ],       # required, list of source groups
    "closing_line": "...",         # required, string shown at end of biblio
}
```

## `cover` — masthead and metadata

```python
"cover": {
    "subtitle": "A curated meta-newsletter of the week's reading",
    "issue_number": "26132",                       # see issue-number rule below
    "coverage_start": "Monday, May 11",            # no comma after the weekday
    "coverage_end": "Sunday, May 17, 2026",        # include year on end-date only
    "compiled_date": "May 18, 2026",
    "compiled_for": "Your Name",
}
```

| Field | Type | Notes |
|---|---|---|
| `subtitle` | str | Cover tagline. Keep around 7–10 words. The default above is canonical. |
| `issue_number` | str | Julian-style: 2-digit year + day-of-year of coverage_start Monday, +1 offset. See formula below. |
| `coverage_start` | str | Human-readable Monday. Format: `"Monday, May 11"` (no year). |
| `coverage_end` | str | Human-readable Sunday with year. Format: `"Sunday, May 17, 2026"`. |
| `compiled_date` | str | When the digest was rendered. Format: `"May 18, 2026"`. |
| `compiled_for` | str | Recipient name. Default: `"Your Name"`. |

### Issue number formula

```python
from datetime import date
d = coverage_start_date          # the Monday, as a date
issue_number = f"{d.year % 100:02d}{d.timetuple().tm_yday + 1:03d}"
```

Verification: May 11, 2026 → year_suffix=26, DOY=131, +1=132 → `"26132"`.

## `toc` — In This Issue list on the cover

A list of dicts. **5 target, 6 cap.** More than 6 entries breaks the cover layout.

```python
"toc": [
    {"title": "The Mac sleep mystery",
     "blurb": "Glenn Fleishman traces a stubborn macOS sleep bug to a hidden menu-bar utility"},
    {"title": "Strange new crystal from Trinity",
     "blurb": "Researchers identify the first crystallographic clathrate formed in a nuclear blast"},
    # ... up to 6
]
```

| Field | Type | Notes |
|---|---|---|
| `title` | str | Short headline, ~3–6 words. No trailing period. |
| `blurb` | str | ~8–18 words. No trailing period. Renderer appends periods to both. |

The renderer emits each entry as `<b>Title.</b> Blurb.` with the title in cream and the blurb in light gray.

## `sections` — full story write-ups

A list of dicts, one per major story or newsletter. Each gets its own page (or multiple pages if the content is long).

```python
"sections": [
    {
        "kicker": "Apple · How-To",                              # rendered in UPPERCASE teal
        "headline": "Help me, Glenn!: Keeping (and losing) track of Mac sleep settings",
        "byline": "By Glenn Fleishman with Dan Moren · Six Colors · May 11, 2026",
        "deck": "A reader asked why a brand-new M3 Mac mini...", # 2–3 sentence lead paragraph
        "subsections": [
            {
                "subhead": "Where sleep settings live today",
                "paragraphs": [
                    "Sleep-related controls are scattered...",
                    "Fleishman notes that the spread reflects..."
                ],
                "quote": {                                       # optional
                    "text": "atrophy of the thing you would have figured out yourself",
                    "attribution": "one engineer quoted by Maiberg"
                }
            },
            # ... more subsections
        ],
    },
    # ... more sections
]
```

| Field | Type | Notes |
|---|---|---|
| `kicker` | str | Category label. Renderer uppercases it. Format: `"Topic · Subtopic"` with middle dot `·`. |
| `headline` | str | Main story title. No trailing period. |
| `byline` | str | `"By Author · Publication · Date"`. Use `·` as separator. |
| `deck` | str | Lead paragraph. 2–4 sentences. Renderer justifies it. |
| `subsections` | list | At least one subsection required. |

### Subsection fields

| Field | Type | Notes |
|---|---|---|
| `subhead` | str | Section heading, 14pt bold. No trailing period. |
| `paragraphs` | list[str] | One or more body paragraphs. ReportLab inline tags allowed: `<b>`, `<i>`, `<font face="Courier">code</font>`, HTML entities like `&ldquo;` / `&rdquo;` / `&mdash;`. |
| `quote` | dict or absent | Optional pull-quote. Keep `text` under 15 words. |

### Inline formatting

Use ReportLab's mini-HTML. Common patterns:

- `<font face="Courier">pmset -g assertions</font>` for inline shell commands
- `<i>italics</i>` and `<b>bold</b>` as needed
- `&ldquo;quoted&rdquo;` for curly quotes, `&mdash;` for em-dash, `&amp;` for ampersand
- Avoid raw `&` in body text — use `&amp;`

## `briefer_notes` — Additional items this week

Optional. A list of short items that don't warrant a full section (e.g., video-only newsletters, weekly recap labs).

```python
"briefer_notes": [
    {"headline": "MacSparky Labs — videos and community posts",
     "body": "Five briefer items from MacSparky Labs this week: the May 15 Lab Report..."},
    # ... more notes
]
```

| Field | Type | Notes |
|---|---|---|
| `headline` | str | Small bold heading. |
| `body` | str | One paragraph. Inline formatting allowed. |

If `briefer_notes` is empty or absent, the entire "Additional items this week" page is skipped.

## `bibliography` — clickable source list

Required. A list of source groups, each containing entries with citation text and a canonical URL. Group by newsletter-issue-date.

```python
"bibliography": [
    {
        "heading": "Six Colors — May 11, 2026",
        "entries": [
            {"citation": "Fleishman, Glenn. Help me, Glenn!: Keeping (and losing) track of Mac sleep settings. May 11, 2026.",
             "url": "https://sixcolors.com/"},
            {"citation": "Moren, Dan. Apple rolls out encrypted RCS messaging in iOS 26.5 beta. May 11, 2026.",
             "url": "https://sixcolors.com/"},
        ],
    },
    # ... more groups
]
```

| Field | Type | Notes |
|---|---|---|
| `heading` | str | Group label. Format: `"Publication Name — Date"`. Rendered in navy-teal bold. |
| `entries` | list | One per cited piece. |
| `entries[].citation` | str | Author-Title-Date in plain text. `<i>...</i>` allowed for book/magazine titles. |
| `entries[].url` | str | Canonical publisher URL. Strip Substack/Mailchimp/etc. tracker redirects. |

URLs render as clickable teal underlined hyperlinks beneath each citation.

## `closing_line` — final line of the document

A single string rendered in italic slate gray at the end of the bibliography page.

```python
"closing_line": "End of Issue 26132. Compiled May 18, 2026 from newsletter-tagged emails received between Monday, May 11 and Sunday, May 17, 2026."
```

## Worked minimal example

```python
from datetime import date
from scripts.build_pdf import build_pdf

coverage_start = date(2026, 5, 11)
coverage_end = date(2026, 5, 17)
compiled = date(2026, 5, 18)
issue_num = f"{coverage_start.year % 100:02d}{coverage_start.timetuple().tm_yday + 1:03d}"

content = {
    "cover": {
        "subtitle": "A curated meta-newsletter of the week's reading",
        "issue_number": issue_num,
        "coverage_start": "Monday, May 11",
        "coverage_end": "Sunday, May 17, 2026",
        "compiled_date": "May 18, 2026",
        "compiled_for": "Your Name",
    },
    "toc": [
        {"title": "Example story", "blurb": "Short blurb describing the story"},
        # ... 4 more
    ],
    "sections": [
        {
            "kicker": "Apple · How-To",
            "headline": "Example headline",
            "byline": "By Author · Publication · May 11, 2026",
            "deck": "Lead paragraph summarizing the piece in 2–3 sentences.",
            "subsections": [
                {"subhead": "First beat",
                 "paragraphs": ["Body paragraph one.", "Body paragraph two."]},
            ],
        },
    ],
    "briefer_notes": [],
    "bibliography": [
        {"heading": "Publication — May 11, 2026",
         "entries": [
             {"citation": "Author. Title. May 11, 2026.",
              "url": "https://example.com/"},
         ]},
    ],
    "closing_line": f"End of Issue {issue_num}. Compiled May 18, 2026.",
}

build_pdf(content, f"/mnt/user-data/outputs/weekly_digest_{issue_num}.pdf")
```

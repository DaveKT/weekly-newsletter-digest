"""Fetch newsletter-labeled emails via the Gmail API (read-only).

Credentials are assembled from environment variables (client id/secret +
a long-lived refresh token), so the job runs unattended under cron. Use
gmail_auth.py once to mint the refresh token.
"""
from __future__ import annotations

import base64
import re
from datetime import date, datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .config import Config
from .models import Story, canonicalize_url, publication_from_domain

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_URI = "https://oauth2.googleapis.com/token"

# Subjects that are not editorial content; skip these.
_SKIP_SUBJECT = re.compile(
    r"(verification code|sign[\s-]?in|welcome to|thank you for subscribing"
    r"|subscription is renewing|discount offer|last chance|confirm your)",
    re.I,
)
_URL_RE = re.compile(r"https?://[^\s\)\]\>\"']+")

# Email platforms where the sender's display name is the real publication,
# not the platform itself — trust the display name for these domains.
_GENERIC_PLATFORMS = ("substack.com", "circle.so", "beehiiv.com",
                      "mailchimp", "list-manage.com", "memberful.com")


def _clean_platform_name(name: str) -> str:
    """Substack display names are 'Author from Publication' — keep Publication."""
    if " from " in name:
        return name.split(" from ", 1)[1].strip()
    return name.strip()


def _platform_author(name: str) -> str:
    """For 'Author from Publication', return the author; else '' (name is the pub)."""
    if " from " in name:
        return name.split(" from ", 1)[0].strip()
    return ""


def _credentials(cfg: Config) -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=cfg.gmail_refresh_token,
        client_id=cfg.gmail_client_id,
        client_secret=cfg.gmail_client_secret,
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def _find_label_id(service, display_name: str) -> str | None:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lab in labels:
        if lab.get("name") == display_name:
            return lab.get("id")
    return None


def _walk_parts(payload) -> str:
    """Depth-first collect text/plain (preferred) from a Gmail message payload."""
    plain, html = [], []

    def rec(part):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data:
            decoded = base64.urlsafe_b64decode(data.encode("utf-8")).decode(
                "utf-8", errors="replace"
            )
            if mime == "text/plain":
                plain.append(decoded)
            elif mime == "text/html":
                html.append(decoded)
        for sub in part.get("parts", []) or []:
            rec(sub)

    rec(payload)
    if plain:
        return "\n".join(plain)
    if html:
        return _strip_html(" ".join(html))
    return ""


def _strip_html(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _parse_sender(from_header: str) -> tuple[str, str]:
    """Return (display_name, email) from a From: header."""
    m = re.match(r"\s*(.*?)\s*<([^>]+)>", from_header)
    if m:
        return m.group(1).strip().strip('"'), m.group(2).strip()
    return "", from_header.strip()


def fetch(cfg: Config, since: datetime | None = None) -> list[Story]:
    """Return editorial newsletter Stories.

    Default: messages within cfg's coverage window. If `since` (aware datetime)
    is given, messages received strictly after it instead (interim reports).
    """
    service = build("gmail", "v1", credentials=_credentials(cfg), cache_discovery=False)

    label_id = _find_label_id(service, cfg.gmail_label)
    if since is None:
        # Gmail `before:` is exclusive; add a day so Sunday is included.
        after = cfg.coverage_start.strftime("%Y/%m/%d")
        before = (cfg.coverage_end + timedelta(days=1)).strftime("%Y/%m/%d")
        query = f'label:"{cfg.gmail_label}" after:{after} before:{before}'
    else:
        # Gmail accepts a Unix timestamp for after:
        query = f'label:"{cfg.gmail_label}" after:{int(since.timestamp())}'

    list_kwargs = {"userId": "me", "q": query, "maxResults": 50}
    if label_id:
        list_kwargs["labelIds"] = [label_id]

    message_ids: list[str] = []
    resp = service.users().messages().list(**list_kwargs).execute()
    message_ids += [m["id"] for m in resp.get("messages", [])]
    while resp.get("nextPageToken"):
        resp = service.users().messages().list(
            **list_kwargs, pageToken=resp["nextPageToken"]
        ).execute()
        message_ids += [m["id"] for m in resp.get("messages", [])]

    stories: list[Story] = []
    for mid in message_ids:
        msg = service.users().messages().get(
            userId="me", id=mid, format="full"
        ).execute()
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        subject = _header(headers, "Subject").strip()
        if _SKIP_SUBJECT.search(subject):
            continue

        body = _walk_parts(payload)
        if len(body.strip()) < 400:  # near-empty / pure-CTA
            continue

        sender_name, sender_email = _parse_sender(_header(headers, "From"))
        domain = sender_email.split("@")[-1].lower() if "@" in sender_email else ""
        if sender_name and any(p in domain for p in _GENERIC_PLATFORMS):
            publication = _clean_platform_name(sender_name)
            author = _platform_author(sender_name)
            authors = [author] if author else []
        else:
            mapped = publication_from_domain(sender_email) if "@" in sender_email else "Unknown"
            publication = mapped if mapped != "Unknown" else (sender_name or "Unknown")
            authors = [sender_name] if sender_name else []

        # Date from internal timestamp (ms since epoch).
        ts = int(msg.get("internalDate", "0")) / 1000
        if since is not None and ts and ts <= since.timestamp():
            continue  # precise cutoff (Gmail after: is day-granular)
        published = datetime.fromtimestamp(ts).date() if ts else cfg.coverage_start

        urls = []
        seen = set()
        for u in _URL_RE.findall(body):
            c = canonicalize_url(u)
            if c and c not in seen:
                seen.add(c)
                urls.append(c)

        stories.append(
            Story(
                source="gmail",
                publication=publication,
                authors=authors,
                published=published,
                title=subject,
                body_text=body,
                primary_url=urls[0] if urls else "",
                urls=urls[:20],
            )
        )
    return stories

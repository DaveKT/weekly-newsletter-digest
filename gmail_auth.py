#!/usr/bin/env python3
"""One-time helper to mint a long-lived Gmail refresh token for cron use.

Prereqs:
  1. In Google Cloud Console, create a project and enable the Gmail API.
  2. Configure an OAuth consent screen (External, add yourself as a test user).
  3. Create an OAuth client of type "Desktop app" and download its JSON.

Then run:
    python gmail_auth.py /path/to/client_secret.json

A browser window opens for consent. On success this prints the three values
to paste into your `mysecrets` file. The token is read-only (gmail.readonly).
"""
from __future__ import annotations

import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1
    client_secret_path = argv[1]

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    with open(client_secret_path) as f:
        cfg = json.load(f)
    block = cfg.get("installed") or cfg.get("web") or {}
    client_id = block.get("client_id", "")
    client_secret = block.get("client_secret", "")

    if not creds.refresh_token:
        print("\nNo refresh token returned. Re-run; the consent prompt with "
              "access_type=offline must be accepted.", file=sys.stderr)
        return 2

    print("\n# --- paste these into your mysecrets file ---")
    print(f'export GMAIL_CLIENT_ID="{client_id}"')
    print(f'export GMAIL_CLIENT_SECRET="{client_secret}"')
    print(f'export GMAIL_REFRESH_TOKEN="{creds.refresh_token}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

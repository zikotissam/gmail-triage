from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

PENDING_FILE = "pending-auth.json"


def credentials_path(state_dir: Path) -> Path:
    in_state = state_dir / "credentials.json"
    in_cwd = Path.cwd() / "credentials.json"
    if in_cwd.exists():
        return in_cwd
    return in_state


def token_path(state_dir: Path, account: str = "default") -> Path:
    return state_dir / account / "token.json"


def pending_path(state_dir: Path) -> Path:
    return state_dir / PENDING_FILE


def auth_url(state_dir: Path, client_file: str | None = None, account: str = "default") -> tuple[str, Path]:
    """Generate the authorization URL and save the pending-flow state. Returns (url, state_path)."""
    state_dir.mkdir(parents=True, exist_ok=True)
    creds_path = credentials_path(state_dir)
    if client_file:
        creds_path = Path(client_file)
    if not creds_path.exists():
        raise SystemExit(
            f"No OAuth client found at {creds_path}.\n"
            "Create a Google Cloud project, enable the Gmail API, download the "
            "Desktop app OAuth client JSON and save it as credentials.json (see README)."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    state_path = pending_path(state_dir)
    state_path.write_text(
        json.dumps({"url": url, "code_verifier": flow.code_verifier, "account": account}),
        encoding="utf-8",
    )
    return url, state_path


def finish_auth(state_dir: Path, code: str, account: str = "default") -> Any:
    """Exchange the pasted authorization code for tokens using the saved pending state."""
    state_path = pending_path(state_dir)
    if not state_path.exists():
        raise SystemExit(
            f"No pending auth found at {state_path}. Run 'gmail-triage auth-run --no-browser' first."
        )
    pending = json.loads(state_path.read_text(encoding="utf-8"))
    if pending.get("account") != account:
        raise SystemExit(
            f"Pending auth is for account '{pending.get('account')}', not '{account}'. "
            "Run 'gmail-triage auth-run --no-browser' again."
        )
    creds_path = credentials_path(state_dir)
    if not creds_path.exists():
        raise SystemExit(f"No OAuth client found at {creds_path}. See README.")
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    flow.code_verifier = pending["code_verifier"]
    flow.fetch_token(code=code)
    tok_path = token_path(state_dir, account)
    tok_path.parent.mkdir(parents=True, exist_ok=True)
    tok_path.write_text(flow.credentials.to_json(), encoding="utf-8")
    os.chmod(tok_path, 0o600)
    state_path.unlink(missing_ok=True)
    return flow.credentials


def get_credentials(state_dir: Path, client_file: str | None = None, account: str = "default", no_browser: bool = False) -> Any:
    state_dir.mkdir(parents=True, exist_ok=True)
    creds_path = credentials_path(state_dir)
    tok_path = token_path(state_dir, account)
    tok_path.parent.mkdir(parents=True, exist_ok=True)

    if client_file:
        creds_path = Path(client_file)

    creds = None
    if tok_path.exists():
        creds = Credentials.from_authorized_user_file(str(tok_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not creds_path.exists():
            raise SystemExit(
                f"No OAuth client found at {creds_path}.\n"
                "Create a Google Cloud project, enable the Gmail API, download the "
                "Desktop app OAuth client JSON and save it as credentials.json (see README)."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
        if no_browser:
            raise SystemExit(
                "Use 'gmail-triage auth-run --no-browser' to get a URL, then "
                "'gmail-triage auth-complete <code>' once you've authorized."
            )
        creds = flow.run_local_server(port=0, prompt="consent")
        tok_path.write_text(creds.to_json(), encoding="utf-8")
        os.chmod(tok_path, 0o600)

    return creds

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def credentials_path(state_dir: Path) -> Path:
    in_state = state_dir / "credentials.json"
    in_cwd = Path.cwd() / "credentials.json"
    if in_cwd.exists():
        return in_cwd
    return in_state


def token_path(state_dir: Path, account: str = "default") -> Path:
    return state_dir / account / "token.json"


def get_credentials(state_dir: Path, client_file: str | None = None, account: str = "default") -> Any:
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
        creds = flow.run_local_server(port=0, prompt="consent")
        tok_path.write_text(creds.to_json(), encoding="utf-8")
        os.chmod(tok_path, 0o600)

    return creds

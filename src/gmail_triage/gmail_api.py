from __future__ import annotations

import base64
import html as html_lib
import re
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import Attachment, Message

DEFAULT_LABEL = "in:inbox"
META_HEADERS = ["From", "To", "Subject", "Date", "List-Unsubscribe", "Precedence", "X-Auto-Response-Suppress", "X-Feedback-ID", "X-Mailer", "Auto-Submitted"]


def _resolve_window(since: datetime | None, until: datetime | None, hours: int | None) -> tuple[datetime | None, datetime | None]:
    if hours is not None:
        if since is not None or until is not None:
            raise ValueError("--hours cannot be combined with --since/--until")
        since = datetime.now() - timedelta(hours=hours)
    return since, until


def _date_query(date: datetime, label: str) -> str:
    return f"{label}:{date.year}/{date.month:02d}/{date.day:02d}"


def _label_scope(label: str | None) -> str:
    if not label:
        return DEFAULT_LABEL
    label = label.strip().lower()
    if label in ("inbox", "spam", "sent", "draft", "trash", "archive", "all", "unread", "starred"):
        return f"in:{label}" if label != "all" else "in:anywhere"
    return f"label:{label}"


def build_query(since: datetime | None, until: datetime | None, hours: int | None, label: str | None = None, unread_only: bool = False, extra: str | None = None) -> tuple[str, datetime | None, datetime | None]:
    since, until = _resolve_window(since, until, hours)
    parts = [_label_scope(label)]
    if unread_only:
        parts.append("is:unread")
    if since:
        parts.append(_date_query(since, "after"))
    if until:
        parts.append(_date_query(until, "before"))
    if extra and extra.strip():
        parts.append(extra.strip())
    return " ".join(parts), since, until


class GmailClient:
    def __init__(self, creds: Credentials):
        self.service = build("gmail", "v1", credentials=creds)

    def fetch(self, since: datetime | None = None, until: datetime | None = None, hours: int | None = None, max_results: int = 100, include_body: bool = False, label: str | None = None, unread_only: bool = False, extra: str | None = None) -> list[Message]:
        query, since, until = build_query(since, until, hours, label=label, unread_only=unread_only, extra=extra)
        messages = self.service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute(num_retries=4).get("messages", [])

        fmt = "full" if include_body else "metadata"

        out: list[Message] = []
        for entry in messages:
            kwargs = {"userId": "me", "id": entry["id"], "format": fmt}
            if not include_body:
                kwargs["metadataHeaders"] = META_HEADERS
            detail = self.service.users().messages().get(**kwargs).execute(num_retries=4)
            msg = _parse_message(detail)
            if include_body:
                msg.body = _extract_body(detail.get("payload", {}))
            out.append(msg)
        return out


def _decode(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _html_to_text(raw: str) -> str:
    text = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|tr|li|h[1-6])>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html_lib.unescape(re.sub(r"\s+", " ", text)).strip()


def _extract_body(payload: dict) -> str:
    direct = payload.get("body", {}).get("data")
    if direct:
        return _decode(direct)

    texts: list[str] = []
    for part in payload.get("parts", []) or []:
        mt = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if mt == "text/plain" and data:
            texts.append(_decode(data))
        elif mt == "text/html" and data:
            texts.append(_html_to_text(_decode(data)))
        elif mt.startswith("multipart/"):
            nested = _extract_body(part)
            if nested:
                texts.append(nested)
    return "\n".join(texts)


def _walk_attachments(payload: dict) -> list[Attachment]:
    out: list[Attachment] = []
    filename = payload.get("filename")
    if filename:
        body = payload.get("body", {})
        out.append(Attachment(name=filename, mime_type=payload.get("mimeType", ""), size=body.get("size")))
    for part in payload.get("parts", []) or []:
        out.extend(_walk_attachments(part))
    return out


def _parse_unsubscribe(header: str | None) -> str | None:
    if not header:
        return None
    for match in re.finditer(r"<(https?://[^>]+)>", header):
        return match.group(1)
    for match in re.finditer(r"<mailto:[^>]+>", header):
        return match.group(0)
    return None


def _parse_message(detail: dict) -> Message:
    headers: dict[str, str] = {}
    for h in detail.get("payload", {}).get("headers", []):
        headers[h["name"].lower()] = h.get("value", "")

    def head(name: str) -> str:
        return headers.get(name, "")

    parsed_date = _parse_date(head("date"))
    return Message(
        id=detail["id"],
        thread_id=detail.get("threadId", ""),
        from_=head("from"),
        from_name=_name_part(head("from")),
        to=head("to"),
        subject=head("subject"),
        snippet=detail.get("snippet", ""),
        date=parsed_date,
        gmail_labels=detail.get("labelIds", []),
        headers=headers,
        attachments=_walk_attachments(detail.get("payload", {})),
        unsubscribe_url=_parse_unsubscribe(headers.get("list-unsubscribe")),
    )


def _name_part(from_header: str) -> str:
    if "<" in from_header:
        name = from_header.split("<")[0].strip().strip('"')
        if name:
            return name
    return from_header.strip()


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(value)
    except Exception:
        return None

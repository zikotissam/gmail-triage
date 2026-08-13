from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Attachment:
    name: str
    mime_type: str
    size: int | None = None


@dataclass
class Message:
    id: str
    thread_id: str
    from_: str
    from_name: str
    to: str
    subject: str
    snippet: str
    date: datetime | None
    gmail_labels: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    unsubscribe_url: str | None = None

    def header(self, name: str) -> str | None:
        return self.headers.get(name)

    @property
    def is_unread(self) -> bool:
        return "UNREAD" in self.gmail_labels

    def to_features(self, include_body: bool = False) -> dict:
        out = {
            "id": self.id,
            "thread_id": self.thread_id,
            "from": self.from_,
            "from_name": self.from_name,
            "to": self.to,
            "subject": self.subject,
            "snippet": self.snippet,
            "date": self.date.isoformat() if self.date else None,
            "is_unread": self.is_unread,
            "gmail_labels": self.gmail_labels,
            "has_attachment": bool(self.attachments),
            "attachments": [
                {
                    "name": a.name,
                    "mime_type": a.mime_type,
                    "size": a.size,
                }
                for a in self.attachments
            ],
            "unsubscribe_url": self.unsubscribe_url,
            "headers": {
                k: v
                for k, v in self.headers.items()
                if k
                in (
                    "list-unsubscribe",
                    "precedence",
                    "x-auto-response-suppress",
                    "x-feedback-id",
                    "x-mailer",
                    "auto-submitted",
                )
            },
        }
        if include_body:
            out["body"] = self.body
        return out

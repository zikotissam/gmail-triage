from __future__ import annotations

from email.utils import parseaddr
from typing import Any

from ..models import Message
from .categories import gmail_label_category


def sender_domain(from_header: str) -> str:
    addr = parseaddr(from_header)[1].strip().lower()
    if not addr:
        return ""
    return addr.rsplit("@", 1)[-1]


def sender_email(from_header: str) -> str:
    return parseaddr(from_header)[1].strip().lower()


def classify_by_rules(message: Message, config: dict[str, Any]) -> tuple[str | None, list[str]]:
    """Deterministic pass. Returns (category, matched_reasons). None means indeterminate."""
    rules = config["rules"]
    reasons: list[str] = []

    subject = message.subject.lower()
    snippet = message.snippet.lower()
    domain = sender_domain(message.from_)
    email = sender_email(message.from_)

    block = rules.get("block_senders", {})
    if email in block:
        return "ads", [f"block_senders:{block[email]}"]
    for pattern, label in block.items():
        if pattern in subject:
            return label, [f"block_senders:{pattern}->{label}"]

    allow = rules.get("allow_senders", {})
    if email in allow:
        return allow[email], [f"allow_senders:{email}->{allow[email]}"]

    block_domains = rules.get("block_domains", [])
    if domain in block_domains:
        return "ads", [f"block_domains:{domain}"]

    allow_domains = rules.get("allow_domains", [])
    if domain in allow_domains:
        return "personal", [f"allow_domains:{domain}"]

    list_unsubscribe = message.header("list-unsubscribe")
    precedence = message.header("precedence")
    feedback = message.header("x-feedback-id")

    is_bulk = bool(
        list_unsubscribe
        or precedence in ("bulk", "junk", "list")
        or feedback
        or message.header("x-auto-response-suppress")
        or message.header("auto-submitted")
    )
    if is_bulk:
        reasons.append("bulk_headers")

    text = f"{subject} {snippet}"
    if any(k in text for k in rules["security_keywords"]):
        return "security", ["security_keywords"]

    gmail_cat = gmail_label_category(message.gmail_labels)
    if gmail_cat == "ads":
        return "ads", [*reasons, f"gmail_label:{gmail_cat}"]

    if any(k in text for k in rules["urgent_keywords"]):
        return "urgent", ["urgent_keywords"]

    if is_bulk:
        return "updates", [*reasons, "bulk_headers"]

    if gmail_cat == "updates":
        return "updates", [f"gmail_label:{gmail_cat}"]

    return None, reasons

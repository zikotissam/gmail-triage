from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = """
categories:
  important: "High-priority messages that genuinely need attention"
  ads: "Marketing, promotions, offers, deals"
  security: "Password resets, login alerts, 2FA codes, security notifications"
  urgent: "Time-sensitive messages with deadlines or immediate action"
  personal: "Messages from people you know, personal correspondence"
  updates: "Newsletters, product updates, notifications, receipts"
  other: "Everything that doesn't fit above"

rules:
  security_keywords:
    - "verify your identity"
    - "sign-in attempt"
    - "new device"
    - "security alert"
    - "password"
    - "verification code"
    - "authentication"
    - "unusual activity"
    - "account locked"
    - "reset your password"
  urgent_keywords:
    - "urgent"
    - "asap"
    - "deadline"
    - "today"
    - "by eod"
    - "action required"
    - "immediately"
    - "expires"
  allow_senders: {}
  block_senders: {}
  allow_domains: []
  block_domains: []

labels:
  ads:
    - "CATEGORY_PROMOTIONS"
  updates:
    - "CATEGORY_UPDATES"
"""


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: str | os.PathLike | None = None) -> dict[str, Any]:
    base = yaml.safe_load(DEFAULT_CONFIG)
    if path and Path(path).exists():
        override = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        _merge(base, override)
    return base

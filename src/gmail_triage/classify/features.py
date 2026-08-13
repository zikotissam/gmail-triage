from __future__ import annotations

from ..models import Message
from .rules import classify_by_rules


def classify(message: Message, config: dict, include_body: bool = False) -> dict:
    category, reasons = classify_by_rules(message, config)
    features = message.to_features(include_body=include_body)
    features["rule_category"] = category
    features["rule_reasons"] = reasons
    features["rule_indeterminate"] = category is None
    return features

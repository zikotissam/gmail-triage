CANONICAL = [
    "important",
    "ads",
    "security",
    "urgent",
    "personal",
    "updates",
    "other",
]


def gmail_label_category(labels: list[str]) -> str | None:
    if "CATEGORY_PROMOTIONS" in labels:
        return "ads"
    if "CATEGORY_UPDATES" in labels:
        return "updates"
    return None

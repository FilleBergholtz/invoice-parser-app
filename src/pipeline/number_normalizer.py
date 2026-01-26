"""Utilities for normalizing Swedish numeric formats."""

from decimal import Decimal, InvalidOperation
import re


_CURRENCY_PATTERN = re.compile(r"(?i)\bsek\b|\bkr\b|:-|€|\$")


def normalize_swedish_decimal(text: str) -> Decimal:
    """Normalize Swedish numeric strings to Decimal.

    Rules:
    - Trim whitespace
    - Remove spaces as thousand separators
    - Remove dots as thousand separators only when followed by three digits
    - Convert commas to dot before Decimal parsing
    - Support negative amounts with leading or trailing '-'
    - Raise ValueError for invalid formats
    """
    if text is None:
        raise ValueError("Input text is None")

    raw = text.strip()
    if not raw:
        raise ValueError("Input text is empty")

    negative = False
    if raw.startswith("-"):
        negative = True
        raw = raw[1:].strip()
    if raw.endswith("-"):
        negative = True
        raw = raw[:-1].strip()

    cleaned = _CURRENCY_PATTERN.sub("", raw)
    cleaned = re.sub(r"\s+", "", cleaned).strip()
    if not cleaned:
        raise ValueError("Input text has no numeric content")

    # Remove dot thousand separators only when followed by three digits
    cleaned = re.sub(r"(?<=\d)\.(?=\d{3}(\D|$))", "", cleaned)
    cleaned = cleaned.replace(",", ".")

    if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
        raise ValueError(f"Invalid numeric format: {text!r}")

    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric format: {text!r}") from exc

    return -value if negative else value

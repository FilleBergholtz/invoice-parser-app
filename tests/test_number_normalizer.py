"""Unit tests for Swedish number normalization."""

from decimal import Decimal

import pytest

from src.pipeline.number_normalizer import normalize_swedish_decimal


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1 234 567,89", Decimal("1234567.89")),
        ("12.345,67", Decimal("12345.67")),
        ("12.50", Decimal("12.50")),
        ("12.5", Decimal("12.5")),
        ("1.234", Decimal("1234")),
        ("1,234", Decimal("1.234")),
        ("SEK 1 234,50", Decimal("1234.50")),
        ("1 234,00 kr", Decimal("1234.00")),
        ("-1 234,00", Decimal("-1234.00")),
        ("1 234,00-", Decimal("-1234.00")),
    ],
)
def test_normalize_swedish_decimal(text, expected):
    assert normalize_swedish_decimal(text) == expected


@pytest.mark.parametrize("text", ["", " ", "12..3", "abc", "12,34,56"])
def test_normalize_swedish_decimal_rejects_invalid(text):
    with pytest.raises(ValueError):
        normalize_swedish_decimal(text)

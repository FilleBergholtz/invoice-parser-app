"""Deterministic text quality scoring [0..1] per page for routing (pdfplumber vs OCR vs AI).

Used by orchestration to decide AI text-only vs vision: when text_quality >= threshold
(e.g. 0.5), text-only AI is sufficient; below that, vision may be used.

Factors: nonempty_ratio, weird_char_ratio, alpha_num_ratio, token length sanity,
optional invoice keyword hits (Total, Moms, Faktura, Bankgiro).
"""

from __future__ import annotations

import statistics
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.token import Token

# Optional invoice keywords; presence suggests usable invoice text
_INVOICE_KEYWORDS = ("total", "moms", "faktura", "bankgiro", "att betala", "summa")


def _content_score(text: str, tokens: List["Token"]) -> float:
    """Compute content-based quality sub-scores and return aggregate in [0, 1]."""
    if not text and not tokens:
        return 0.0
    full = text if text else " ".join(t.text for t in tokens)
    full = full or ""
    chars = list(full)
    if not chars:
        return 0.0
    # nonempty: enough content
    total_chars = len(chars)
    num_tokens = len(tokens) if tokens else (len(full.split()) if full else 0)
    nonempty = min(1.0, (total_chars / 30.0) * 0.5 + (num_tokens / 5.0) * 0.5)

    # weird_char_ratio: control, replacement (U+FFFD), heavy punctuation
    letters_digits = sum(1 for c in chars if c.isalnum() or c.isspace())
    weird = total_chars - letters_digits
    # allow normal punctuation (. , - / :)
    normal_punct = sum(1 for c in chars if c in ".,-/ :;")
    weird = max(0, weird - normal_punct)
    weird_ratio = weird / max(1, total_chars)
    clean_ratio = 1.0 - min(1.0, weird_ratio * 2.0)  # dampen

    # alpha_num_ratio
    alnum = sum(1 for c in chars if c.isalnum())
    alpha_num_ratio = alnum / max(1, total_chars)

    # token length sanity (median length in reasonable range)
    if tokens:
        lens = [len(t.text) for t in tokens if t.text]
        med = statistics.median(lens) if lens else 0
        if med < 1:
            len_sanity = 0.0
        elif 2 <= med <= 20:
            len_sanity = 1.0
        else:
            len_sanity = max(0, 1.0 - abs(med - 10) / 30.0)
    else:
        words = full.split()
        lens = [len(w) for w in words] if words else [0]
        med = statistics.median(lens) if lens else 0
        len_sanity = 1.0 if 2 <= med <= 20 else max(0, 1.0 - abs(med - 10) / 30.0)

    # keyword bonus (small)
    lower = full.lower()
    hits = sum(1 for kw in _INVOICE_KEYWORDS if kw in lower)
    keyword_bonus = min(0.2, hits * 0.05)

    # weighted blend
    raw = 0.25 * nonempty + 0.3 * clean_ratio + 0.25 * alpha_num_ratio + 0.2 * len_sanity + keyword_bonus
    return max(0.0, min(1.0, raw))


def score_text_quality(text: str, tokens: List["Token"]) -> float:
    """Score quality of pdfplumber-derived text for a page (for routing).

    Args:
        text: Concatenated or full-page text from pdfplumber.
        tokens: Tokens from pdfplumber for this page (optional but preferred for length stats).

    Returns:
        Float in [0.0, 1.0]. Higher = more reliable for AI text-only.
    """
    return _content_score(text, tokens)


def score_ocr_quality(tokens: List["Token"]) -> float:
    """Score quality of OCR-derived tokens for a page (for routing).

    Uses token.confidence (0–100) when present, plus content-based signals.
    OCR tokens typically have confidence set; pdfplumber tokens do not.

    Args:
        tokens: Tokens from OCR for this page (token.confidence in 0–100).

    Returns:
        Float in [0.0, 1.0]. Higher = more reliable for downstream use.
    """
    if not tokens:
        return 0.0
    confs = [t.confidence for t in tokens if t.confidence is not None and t.confidence >= 0]
    text = " ".join(t.text for t in tokens)
    content = _content_score(text, tokens)
    if not confs:
        return content
    # Blend content score with confidence (0–100 -> 0–1)
    conf_score = statistics.median(confs) / 100.0
    return max(0.0, min(1.0, 0.5 * content + 0.5 * conf_score))

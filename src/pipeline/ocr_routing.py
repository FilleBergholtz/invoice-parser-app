"""OCR routing helpers for per-page text-layer decisions."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

from ..config.profile_manager import get_profile
from .text_quality import score_text_quality

if TYPE_CHECKING:
    from ..models.token import Token


_DEFAULT_OCR_ROUTING: Dict[str, Any] = {
    "min_text_chars": 500,
    "required_anchors": [r"Faktura\s"],
    "extra_anchors": [r"Sida\s*\d+\s*/\s*\d+", r"Ramirent"],
    "min_word_tokens": 40,
    "min_text_quality": 0.5,
    "allow_quality_override": True,
    "cache_pdfplumber_text": True,
}


def get_ocr_routing_config(profile: Optional[Any] = None) -> Dict[str, Any]:
    """Return OCR routing config with defaults applied."""
    active = profile or get_profile()
    config = getattr(active, "ocr_routing", None)
    if not isinstance(config, dict):
        config = {}
    merged = dict(_DEFAULT_OCR_ROUTING)
    merged.update(config)
    merged["required_anchors"] = list(merged.get("required_anchors") or [])
    merged["extra_anchors"] = list(merged.get("extra_anchors") or [])
    return merged


def _compile_anchors(anchors: Iterable[str]) -> List[re.Pattern]:
    patterns = []
    for anchor in anchors:
        if not anchor:
            continue
        try:
            patterns.append(re.compile(anchor, re.IGNORECASE))
        except re.error:
            patterns.append(re.compile(re.escape(anchor), re.IGNORECASE))
    return patterns


def _match_patterns(text: str, patterns: Iterable[str]) -> List[str]:
    compiled = _compile_anchors(patterns)
    if not compiled:
        return []
    text = text or ""
    return [p.pattern for p in compiled if p.search(text)]


def evaluate_text_layer(
    text: str,
    tokens: Optional[List["Token"]],
    routing_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Evaluate if pdfplumber text layer is sufficient for a page.

    Returns a dict with decision and reasoning for debug.
    """
    cfg = routing_config or get_ocr_routing_config()
    text = (text or "").strip()
    text_chars = len(text)
    word_tokens = len(text.split())
    tokens = tokens or []

    required_patterns = _compile_anchors(cfg.get("required_anchors", []))
    extra_patterns = _compile_anchors(cfg.get("extra_anchors", []))

    required_hits = [p.pattern for p in required_patterns if p.search(text)]
    extra_hits = [p.pattern for p in extra_patterns if p.search(text)]

    required_ok = True if not required_patterns else bool(required_hits)
    extra_ok = True if not extra_patterns else bool(extra_hits)
    chars_ok = text_chars >= int(cfg.get("min_text_chars", 0) or 0)
    min_word_tokens = int(cfg.get("min_word_tokens", 0) or 0)
    text_quality = score_text_quality(text, tokens)
    quality_ok = text_quality >= float(cfg.get("min_text_quality", 0.0) or 0.0)

    base_ok = chars_ok and required_ok and extra_ok
    allow_override = bool(cfg.get("allow_quality_override", False))
    override_ok = allow_override and quality_ok and word_tokens >= min_word_tokens

    use_text_layer = base_ok or override_ok
    reason_flags: List[str] = []
    if not chars_ok:
        reason_flags.append("min_text_chars")
    if not required_ok:
        reason_flags.append("required_anchor_missing")
    if not extra_ok:
        reason_flags.append("extra_anchor_missing")
    if override_ok and not base_ok:
        reason_flags.append("quality_override")

    return {
        "use_text_layer": use_text_layer,
        "text_chars": text_chars,
        "word_tokens": word_tokens,
        "text_quality": text_quality,
        "required_anchor_hits": required_hits,
        "extra_anchor_hits": extra_hits,
        "reason_flags": reason_flags,
    }


def evaluate_edi_signals(
    text: str,
    text_layer_used: bool,
    text_quality: Optional[float],
    anchor_rules: Optional[Dict[str, Iterable[str]]],
    table_patterns: Optional[Iterable[str]],
    min_signals: int = 2,
    min_text_quality: float = 0.5,
) -> Dict[str, Any]:
    """Evaluate EDI-like signals for AI policy decisions."""
    rules = anchor_rules or {}
    required = list(rules.get("required") or [])
    extra = list(rules.get("extra") or [])
    required_hits = _match_patterns(text, required)
    extra_hits = _match_patterns(text, extra)
    table_hits = _match_patterns(text, table_patterns or [])

    signals = []
    if text_layer_used:
        signals.append("text_layer")
    if text_quality is not None and text_quality >= min_text_quality:
        signals.append("text_quality")
    if required_hits:
        signals.append("anchor_required")
    if extra_hits:
        signals.append("anchor_extra")
    if table_hits:
        signals.append("table_pattern")

    signal_count = len(signals)
    required_ok = True if not required else bool(required_hits)
    edi_like = bool(text_layer_used and required_ok and signal_count >= max(1, min_signals))

    reason_flags = []
    if text_layer_used:
        reason_flags.append("edi_text_layer")
    if text_quality is not None and text_quality >= min_text_quality:
        reason_flags.append("edi_text_quality")
    if required_hits:
        reason_flags.append("edi_anchor_required")
    if extra_hits:
        reason_flags.append("edi_anchor_extra")
    if table_hits:
        reason_flags.append("edi_table_pattern")
    if edi_like:
        reason_flags.append("edi_like")

    return {
        "edi_like": edi_like,
        "signal_count": signal_count,
        "signals": signals,
        "required_anchor_hits": required_hits,
        "extra_anchor_hits": extra_hits,
        "table_pattern_hits": table_hits,
        "reason_flags": reason_flags,
    }

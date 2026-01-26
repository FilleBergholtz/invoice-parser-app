"""AI fallback for total amount extraction when confidence is low.

R4: Max 1 retry on invalid JSON/schema with stricter instruction (AI_JSON_RETRY_COUNT=1).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .providers import AIProvider, AI_JSON_RETRY_COUNT, ClaudeProvider, OpenAIProvider
from ..config import get_ai_key, get_ai_model, get_ai_provider
from ..config.profile_manager import get_profile
from ..models.validation_result import ValidationResult
from ..pipeline.ocr_routing import evaluate_edi_signals

logger = logging.getLogger(__name__)

AI_POLICY_VERSION = "17-01"

_DEFAULT_AI_POLICY: Dict[str, Any] = {
    "allow_ai_for_edi": False,
    "force_review_on_edi_fail": True,
    "min_edi_signals": 2,
    "min_text_quality": 0.5,
    "edi_anchor_rules": {
        "required": [r"Faktura\s"],
        "extra": [r"Sida\s*\d+\s*/\s*\d+", r"Bankgiro"],
    },
    "edi_table_patterns": [
        r"\bArtikel\b",
        r"\bArt\.nr\b",
        r"\bAntal\b",
        r"\bQty\b",
        r"\bPris\b",
        r"\bBelopp\b",
        r"\bAmount\b",
    ],
}


def get_ai_policy_config(profile: Optional[Any] = None) -> Dict[str, Any]:
    """Return AI policy config with defaults applied."""
    active = profile or get_profile()
    raw = getattr(active, "ai_policy", None)
    if not isinstance(raw, dict):
        raw = {}
    merged = dict(_DEFAULT_AI_POLICY)
    merged.update(raw)
    anchor_rules = dict(_DEFAULT_AI_POLICY["edi_anchor_rules"])
    anchor_rules.update(merged.get("edi_anchor_rules") or {})
    anchor_rules["required"] = list(anchor_rules.get("required") or [])
    anchor_rules["extra"] = list(anchor_rules.get("extra") or [])
    merged["edi_anchor_rules"] = anchor_rules
    merged["edi_table_patterns"] = list(merged.get("edi_table_patterns") or [])
    return merged


def evaluate_ai_policy(
    extraction_source: Optional[str],
    text_quality: Optional[float],
    validation_result: Optional[ValidationResult],
    edi_signals: Optional[Dict[str, Any]] = None,
    policy_config: Optional[Dict[str, Any]] = None,
    fallback_attempted: bool = False,
    fallback_passed: Optional[bool] = None,
) -> Dict[str, Any]:
    """Evaluate AI policy gating decision for fallback usage."""
    policy = policy_config or get_ai_policy_config()
    allow_ai_for_edi = bool(policy.get("allow_ai_for_edi", False))
    force_review_on_edi_fail = bool(policy.get("force_review_on_edi_fail", True))

    signals = edi_signals or evaluate_edi_signals(
        text="",
        text_layer_used=extraction_source == "pdfplumber",
        text_quality=text_quality,
        anchor_rules=policy.get("edi_anchor_rules"),
        table_patterns=policy.get("edi_table_patterns"),
        min_signals=int(policy.get("min_edi_signals", 2) or 2),
        min_text_quality=float(policy.get("min_text_quality", 0.5) or 0.5),
    )
    reason_flags = list(dict.fromkeys(signals.get("reason_flags") or []))
    edi_like = bool(signals.get("edi_like"))

    if validation_result is None:
        reason_flags.append("validation_missing")
        validation_ok = False
    else:
        validation_ok = validation_result.status in ("OK", "PARTIAL")
        reason_flags.append("validation_passed" if validation_ok else "validation_failed")

    if fallback_attempted:
        reason_flags.append("fallback_attempted")
        if fallback_passed is True:
            reason_flags.append("fallback_passed")
        elif fallback_passed is False:
            reason_flags.append("fallback_failed")
    else:
        reason_flags.append("fallback_not_attempted")

    if edi_like and validation_ok:
        allow_ai = allow_ai_for_edi
        if not allow_ai:
            reason_flags.append("edi_blocked_validation_ok")
    elif edi_like and not validation_ok:
        if force_review_on_edi_fail:
            allow_ai = False
            reason_flags.append("edi_force_review")
        else:
            allow_ai = allow_ai_for_edi
            if not allow_ai:
                reason_flags.append("edi_blocked_validation_fail")
    else:
        allow_ai = True

    if extraction_source:
        reason_flags.append(f"source:{extraction_source}")

    return {
        "allow_ai": allow_ai,
        "reason_flags": reason_flags,
        "policy_version": AI_POLICY_VERSION,
        "edi_like": edi_like,
        "edi_signals": signals,
    }


class AIFallback:
    """AI fallback for total amount extraction."""

    def __init__(self, provider: Optional[AIProvider] = None):
        """Initialize AI fallback.

        Args:
            provider: Optional AIProvider instance. If None, creates provider from config.
        """
        self.provider = provider or self._create_provider()

    def _create_provider(self) -> Optional[AIProvider]:
        """Create AI provider from configuration."""
        api_key = get_ai_key()
        if not api_key:
            logger.debug("AI API key not configured, AI fallback disabled")
            return None
        provider_name = get_ai_provider()
        model = get_ai_model()
        try:
            if provider_name == "openai":
                return OpenAIProvider(api_key=api_key, model=model)
            elif provider_name == "claude":
                return ClaudeProvider(api_key=api_key, model=model)
            logger.warning("Unknown AI provider: %s", provider_name)
            return None
        except ImportError as e:
            logger.warning("AI provider library not installed: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to create AI provider: %s", e)
            return None

    def extract(
        self,
        footer_text: str,
        line_items_sum: Optional[float] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        page_context: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extract total amount using AI; optional vision via image_path. Up to 1 retry on invalid JSON."""
        if not self.provider:
            return None
        last_error: Optional[Exception] = None
        for attempt in range(AI_JSON_RETRY_COUNT + 1):
            strict = attempt > 0
            if strict:
                logger.warning("AI response invalid, retrying once with strict JSON instruction")
            try:
                result = self.provider.extract_total_amount(
                    footer_text,
                    line_items_sum,
                    candidates=candidates,
                    page_context=page_context,
                    image_path=image_path,
                    strict_json_instruction=strict,
                )
            except Exception as e:
                last_error = e
                if not strict:
                    logger.warning("AI extraction failed: %s", e)
                continue
            if result and self.provider.validate_response(result):
                return self._apply_validation_boosting(result, line_items_sum)
            last_error = ValueError("AI response validation failed")
        if last_error:
            logger.warning("AI extraction failed after retry: %s", last_error)
        return None

    def _apply_validation_boosting(
        self, result: Dict[str, Any], line_items_sum: Optional[float]
    ) -> Dict[str, Any]:
        """Apply validation vs line_items_sum and optional confidence boost."""
        ai_total = result.get("total_amount")
        if line_items_sum is not None and ai_total is not None:
            diff = abs(ai_total - line_items_sum)
            implausible = (
                diff > max(500.0, 0.15 * ai_total)
                or (line_items_sum < 100.0 and ai_total > 1000.0)
            )
            if implausible:
                result["validation_passed"] = True
                logger.info(
                    "Line items sum %s SEK implausible vs AI total %s SEK; trusting AI",
                    line_items_sum, ai_total,
                )
            else:
                result["validation_passed"] = diff <= 1.0
                if result["validation_passed"]:
                    base_conf = result.get("confidence", 0.0)
                    boost = 0.2 if abs(ai_total - line_items_sum) < 0.01 else 0.1
                    result["confidence"] = min(1.0, base_conf + boost)
        else:
            result["validation_passed"] = ai_total is not None
        return result


def extract_total_with_ai(
    footer_text: str,
    line_items_sum: Optional[float] = None,
    provider: Optional[AIProvider] = None,
    candidates: Optional[List[Dict[str, Any]]] = None,
    page_context: Optional[str] = None,
    image_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Extract total amount using AI fallback. Supports vision via image_path (R3 limits)."""
    fallback = AIFallback(provider=provider)
    return fallback.extract(
        footer_text,
        line_items_sum,
        candidates=candidates,
        page_context=page_context,
        image_path=image_path,
    )

"""AI fallback for total amount extraction when confidence is low.

R4: Max 1 retry on invalid JSON/schema with stricter instruction (AI_JSON_RETRY_COUNT=1).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .providers import AIProvider, AI_JSON_RETRY_COUNT, ClaudeProvider, OpenAIProvider
from ..config import get_ai_key, get_ai_model, get_ai_provider

logger = logging.getLogger(__name__)


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

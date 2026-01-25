"""AI fallback for total amount extraction when confidence is low."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .providers import AIProvider, OpenAIProvider, ClaudeProvider
from ..config import get_ai_key, get_ai_provider, get_ai_model

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
        """Create AI provider from configuration.
        
        Returns:
            AIProvider instance, or None if not configured
        """
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
            else:
                logger.warning(f"Unknown AI provider: {provider_name}")
                return None
        except ImportError as e:
            logger.warning(f"AI provider library not installed: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create AI provider: {e}")
            return None
    
    def extract(
        self,
        footer_text: str,
        line_items_sum: Optional[float] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        page_context: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extract total amount using AI with validation and confidence boosting.
        
        Args:
            footer_text: Footer text from invoice
            line_items_sum: Optional sum of line items for validation
            candidates: Optional heuristic candidates [{amount, keyword_type}] for better AI context
            page_context: Full page text (header/items/footer) so AI sees PDF hela data
            
        Returns:
            Dict with total_amount, confidence (boosted), reasoning, validation_passed, or None if fails
        """
        if not self.provider:
            return None
        
        try:
            result = self.provider.extract_total_amount(
                footer_text, line_items_sum, candidates=candidates, page_context=page_context
            )
            
            # Validate response structure
            if not self.provider.validate_response(result):
                logger.warning("AI response structure validation failed")
                return None
            
            # Validate against line items sum (when it's plausible)
            ai_total = result.get('total_amount')
            validation_passed = False
            
            if line_items_sum is not None and ai_total is not None:
                diff = abs(ai_total - line_items_sum)
                # Line items sum can be wrong (OCR, garbled rows). If it's implausible vs AI total,
                # don't fail validation – trust AI extraction (e.g. "Att betala: SEK X").
                implausible = (
                    diff > max(500.0, 0.15 * ai_total)
                    or (line_items_sum < 100.0 and ai_total > 1000.0)
                )
                if implausible:
                    result['validation_passed'] = True
                    logger.info(
                        f"Line items sum {line_items_sum:.2f} SEK implausible vs AI total {ai_total:.2f} SEK "
                        f"(diff={diff:.2f}); trusting AI, validation_passed=True"
                    )
                else:
                    validation_passed = diff <= 1.0
                    result['validation_passed'] = validation_passed
                    if validation_passed:
                        base_confidence = result.get('confidence', 0.0)
                        boost = 0.1
                        if abs(ai_total - line_items_sum) < 0.01:
                            boost += 0.1
                        boosted_confidence = min(1.0, base_confidence + boost)
                        result['confidence'] = boosted_confidence
                        logger.debug(
                            f"AI validation passed: boosted confidence from {base_confidence:.2f} "
                            f"to {boosted_confidence:.2f} (boost: {boost:.2f})"
                        )
            else:
                result['validation_passed'] = True if ai_total is not None else False
            
            return result
            
        except Exception as e:
            logger.warning(f"AI extraction failed: {e}")
            return None


def extract_total_with_ai(
    footer_text: str,
    line_items_sum: Optional[float] = None,
    provider: Optional[AIProvider] = None,
    candidates: Optional[List[Dict[str, Any]]] = None,
    page_context: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Extract total amount using AI fallback.
    
    Args:
        footer_text: Footer text from invoice
        line_items_sum: Optional sum of line items for validation
        provider: Optional AIProvider instance (creates from config if None)
        candidates: Optional heuristic candidates [{amount, keyword_type}] for better results
        page_context: Full page text (header/items/footer) so AI sees PDF hela data
        
    Returns:
        Dict with total_amount, confidence, reasoning, validation_passed, or None if fails
    """
    fallback = AIFallback(provider=provider)
    return fallback.extract(
        footer_text, line_items_sum, candidates=candidates, page_context=page_context
    )

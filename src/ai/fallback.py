"""AI fallback for total amount extraction when confidence is low."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
        line_items_sum: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Extract total amount using AI.
        
        Args:
            footer_text: Footer text from invoice
            line_items_sum: Optional sum of line items for validation
            
        Returns:
            Dict with total_amount, confidence, reasoning, validation_passed, or None if fails
        """
        if not self.provider:
            return None
        
        try:
            result = self.provider.extract_total_amount(footer_text, line_items_sum)
            
            # Validate response
            if not self.provider.validate_response(result):
                logger.warning("AI response validation failed")
                return None
            
            return result
            
        except Exception as e:
            logger.warning(f"AI extraction failed: {e}")
            return None


def extract_total_with_ai(
    footer_text: str,
    line_items_sum: Optional[float] = None,
    provider: Optional[AIProvider] = None
) -> Optional[Dict[str, Any]]:
    """Extract total amount using AI fallback.
    
    Args:
        footer_text: Footer text from invoice
        line_items_sum: Optional sum of line items for validation
        provider: Optional AIProvider instance (creates from config if None)
        
    Returns:
        Dict with total_amount, confidence, reasoning, validation_passed, or None if fails
    """
    fallback = AIFallback(provider=provider)
    return fallback.extract(footer_text, line_items_sum)

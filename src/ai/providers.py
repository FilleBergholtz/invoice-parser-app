"""AI provider abstraction for OpenAI and Claude."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AITotalResponse(BaseModel):
    """Structured response from AI for total amount extraction."""
    total_amount: float
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    reasoning: Optional[str] = Field(None, description="AI reasoning for extraction")
    validation_passed: bool = Field(False, description="Whether total matches line items sum")


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def extract_total_amount(
        self,
        footer_text: str,
        line_items_sum: Optional[float] = None
    ) -> Dict[str, Any]:
        """Extract total amount from footer text using AI.
        
        Args:
            footer_text: Footer text from invoice
            line_items_sum: Optional sum of line items for validation
            
        Returns:
            Dict with total_amount, confidence, reasoning, validation_passed
            
        Raises:
            Exception: If AI call fails
        """
        pass
    
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate AI response structure.
        
        Args:
            response: AI response dict
            
        Returns:
            True if response is valid
        """
        required_fields = ['total_amount', 'confidence', 'validation_passed']
        for field in required_fields:
            if field not in response:
                return False
        
        # Validate types
        if not isinstance(response['total_amount'], (int, float)):
            return False
        if not isinstance(response['confidence'], (int, float)):
            return False
        if not isinstance(response['validation_passed'], bool):
            return False
        
        # Validate confidence range
        confidence = float(response['confidence'])
        if not 0.0 <= confidence <= 1.0:
            return False
        
        return True


class OpenAIProvider(AIProvider):
    """OpenAI provider using GPT-4 with structured outputs."""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        """Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4-turbo-preview)
        """
        if OpenAI is None:
            raise ImportError(
                "openai library is required. Install with: pip install openai"
            )
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def extract_total_amount(
        self,
        footer_text: str,
        line_items_sum: Optional[float] = None
    ) -> Dict[str, Any]:
        """Extract total amount using OpenAI API.
        
        Args:
            footer_text: Footer text from invoice
            line_items_sum: Optional sum of line items for validation
            
        Returns:
            Dict with total_amount, confidence, reasoning, validation_passed
            
        Raises:
            Exception: If API call fails
        """
        # Build prompt
        prompt = self._build_prompt(footer_text, line_items_sum)
        
        # Call OpenAI API with structured output
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting total amounts from Swedish invoice footers. Return structured data with confidence score."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format=AITotalResponse
            )
            
            # Parse response
            parsed = response.choices[0].message.parsed
            if parsed:
                return {
                    'total_amount': parsed.total_amount,
                    'confidence': parsed.confidence,
                    'reasoning': parsed.reasoning,
                    'validation_passed': parsed.validation_passed
                }
            else:
                # Fallback to manual parsing if structured output fails
                content = response.choices[0].message.content
                return self._parse_fallback_response(content, line_items_sum)
                
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _build_prompt(self, footer_text: str, line_items_sum: Optional[float] = None) -> str:
        """Build prompt for AI extraction.
        
        Args:
            footer_text: Footer text
            line_items_sum: Optional line items sum
            
        Returns:
            Prompt string
        """
        prompt = f"""Extract the total amount (totalsumma) from this Swedish invoice footer text:

{footer_text}

"""
        if line_items_sum is not None:
            prompt += f"The sum of all line items is: {line_items_sum:.2f} SEK. Use this to validate the total amount.\n"
        
        prompt += """
Return:
- total_amount: The extracted total amount as a float
- confidence: Your confidence in the extraction (0.0-1.0)
- reasoning: Brief explanation of how you found the total
- validation_passed: True if the total matches the line items sum (within ±1 SEK tolerance), False otherwise
"""
        return prompt
    
    def _parse_fallback_response(
        self,
        content: str,
        line_items_sum: Optional[float] = None
    ) -> Dict[str, Any]:
        """Parse fallback response if structured output fails.
        
        Args:
            content: Response content
            line_items_sum: Optional line items sum
            
        Returns:
            Parsed response dict
        """
        # Simple fallback parsing (extract number from response)
        import re
        numbers = re.findall(r'\d+[.,]\d+|\d+', content)
        if numbers:
            # Try to parse as float
            try:
                total = float(numbers[-1].replace(',', '.'))
                return {
                    'total_amount': total,
                    'confidence': 0.7,  # Lower confidence for fallback
                    'reasoning': 'Fallback parsing from AI response',
                    'validation_passed': False
                }
            except ValueError:
                pass
        
        raise ValueError("Failed to parse AI response")


class ClaudeProvider(AIProvider):
    """Claude provider using Anthropic API with structured outputs."""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        """Initialize Claude provider.
        
        Args:
            api_key: Anthropic API key
            model: Model name (default: claude-3-opus-20240229)
        """
        if Anthropic is None:
            raise ImportError(
                "anthropic library is required. Install with: pip install anthropic"
            )
        
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def extract_total_amount(
        self,
        footer_text: str,
        line_items_sum: Optional[float] = None
    ) -> Dict[str, Any]:
        """Extract total amount using Claude API.
        
        Args:
            footer_text: Footer text from invoice
            line_items_sum: Optional sum of line items for validation
            
        Returns:
            Dict with total_amount, confidence, reasoning, validation_passed
            
        Raises:
            Exception: If API call fails
        """
        # Build prompt
        prompt = self._build_prompt(footer_text, line_items_sum)
        
        # Call Claude API with structured output
        try:
            from anthropic import AnthropicError
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                # Claude doesn't have built-in structured outputs like OpenAI,
                # so we'll parse JSON from response
            )
            
            # Parse JSON from response
            content = response.content[0].text
            return self._parse_json_response(content, line_items_sum)
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
    
    def _build_prompt(self, footer_text: str, line_items_sum: Optional[float] = None) -> str:
        """Build prompt for AI extraction.
        
        Args:
            footer_text: Footer text
            line_items_sum: Optional line items sum
            
        Returns:
            Prompt string
        """
        prompt = f"""Extract the total amount (totalsumma) from this Swedish invoice footer text:

{footer_text}

"""
        if line_items_sum is not None:
            prompt += f"The sum of all line items is: {line_items_sum:.2f} SEK. Use this to validate the total amount.\n"
        
        prompt += """
Return a JSON object with:
- total_amount: The extracted total amount as a float
- confidence: Your confidence in the extraction (0.0-1.0)
- reasoning: Brief explanation of how you found the total
- validation_passed: True if the total matches the line items sum (within ±1 SEK tolerance), False otherwise

Format: {"total_amount": 1234.56, "confidence": 0.95, "reasoning": "...", "validation_passed": true}
"""
        return prompt
    
    def _parse_json_response(
        self,
        content: str,
        line_items_sum: Optional[float] = None
    ) -> Dict[str, Any]:
        """Parse JSON response from Claude.
        
        Args:
            content: Response content
            line_items_sum: Optional line items sum
            
        Returns:
            Parsed response dict
        """
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                # Validate and return
                response = AITotalResponse(**data)
                return {
                    'total_amount': response.total_amount,
                    'confidence': response.confidence,
                    'reasoning': response.reasoning,
                    'validation_passed': response.validation_passed
                }
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse Claude JSON response: {e}")
        
        # Fallback: try to extract number
        numbers = re.findall(r'\d+[.,]\d+|\d+', content)
        if numbers:
            try:
                total = float(numbers[-1].replace(',', '.'))
                return {
                    'total_amount': total,
                    'confidence': 0.7,
                    'reasoning': 'Fallback parsing from Claude response',
                    'validation_passed': False
                }
            except ValueError:
                pass
        
        raise ValueError("Failed to parse Claude response")

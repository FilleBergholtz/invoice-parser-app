"""AI provider abstraction for OpenAI and Claude.

R3 (14-RESEARCH): Vision input PNG/JPEG, max 4096 px longest side, 20 MB, one image per request.
R4: Max 1 retry on invalid JSON/schema with stricter instruction.
"""

from __future__ import annotations

import base64
import io
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from PIL import Image
except ImportError:
    Image = None

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# R3 limits for vision (14-RESEARCH)
VISION_MAX_PIXELS_LONGEST_SIDE = 4096
VISION_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB
VISION_ALLOWED_FORMATS = ("png", "jpeg")
AI_JSON_RETRY_COUNT = 1  # R4: max retries on invalid JSON


def _prepare_vision_image(image_path: str) -> Tuple[bytes, str]:
    """Prepare image for vision API: enforce R3 limits (PNG/JPEG, max 4096 px, 20 MB).

    Loads from path, scales down if longest side > 4096, ensures size <= 20 MB.
    Returns (image_bytes, mime_type) e.g. (b'...', 'image/png').
    """
    if Image is None:
        raise ImportError("Pillow (PIL) is required for vision. Install with: pip install Pillow")
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Vision image not found: {image_path}")
    ext = path.suffix.lower().lstrip(".")
    if ext not in ("png", "jpg", "jpeg"):
        raise ValueError(f"Vision only supports PNG/JPEG, got: {ext}")
    mime = "image/png" if ext == "png" else "image/jpeg"
    img = Image.open(path).convert("RGB")
    w, h = img.size
    longest = max(w, h)
    if longest > VISION_MAX_PIXELS_LONGEST_SIDE:
        scale = VISION_MAX_PIXELS_LONGEST_SIDE / longest
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    out = buf.getvalue()
    if len(out) > VISION_MAX_FILE_BYTES:
        # Try JPEG with reduced quality to meet size limit
        buf = io.BytesIO()
        for q in [85, 70, 50]:
            buf.seek(0)
            buf.truncate(0)
            img.save(buf, format="JPEG", quality=q, optimize=True)
            if len(buf.getvalue()) <= VISION_MAX_FILE_BYTES:
                return (buf.getvalue(), "image/jpeg")
        raise ValueError(f"Image exceeds {VISION_MAX_FILE_BYTES // (1024*1024)} MB after scaling")
    return (out, "image/png")


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
        line_items_sum: Optional[float] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        page_context: Optional[str] = None,
        image_path: Optional[str] = None,
        strict_json_instruction: bool = False,
    ) -> Dict[str, Any]:
        """Extract total amount from footer text (and optionally page image) using AI.

        When image_path is set, uses vision API (R3: PNG/JPEG, max 4096 px, 20 MB).
        
        Args:
            footer_text: Footer text from invoice
            line_items_sum: Optional sum of line items for validation
            candidates: Optional [{amount, keyword_type}] from heuristics for better context
            page_context: Full page text (header/items/footer) so AI sees PDF hela data
            image_path: Optional path to page image for vision (enforces R3 limits)
            strict_json_instruction: If True, append instruction to return only valid JSON
            
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
        line_items_sum: Optional[float] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        page_context: Optional[str] = None,
        image_path: Optional[str] = None,
        strict_json_instruction: bool = False,
    ) -> Dict[str, Any]:
        """Extract total amount using OpenAI API (text or vision)."""
        prompt = self._build_prompt(
            footer_text, line_items_sum, candidates=candidates, page_context=page_context,
            strict_json_instruction=strict_json_instruction
        )

        if image_path:
            return self._extract_with_vision(prompt, line_items_sum, image_path)

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at extracting total amounts from Swedish invoice footers. Return structured data with confidence score."},
                    {"role": "user", "content": prompt}
                ],
                response_format=AITotalResponse
            )
            parsed = response.choices[0].message.parsed
            if parsed:
                return {
                    "total_amount": parsed.total_amount,
                    "confidence": parsed.confidence,
                    "reasoning": parsed.reasoning,
                    "validation_passed": parsed.validation_passed,
                }
            content = response.choices[0].message.content or ""
            return self._parse_fallback_response(content, line_items_sum)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _extract_with_vision(self, prompt: str, line_items_sum: Optional[float], image_path: str) -> Dict[str, Any]:
        """Call OpenAI vision API and parse response (no structured-output path for vision)."""
        img_bytes, mime = _prepare_vision_image(image_path)
        b64 = base64.b64encode(img_bytes).decode("ascii")
        url = f"data:{mime};base64,{b64}"
        user_content: List[Any] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": url}},
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert at extracting total amounts from Swedish invoice footers. Return structured data with confidence score."},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1024,
        )
        content = (response.choices[0].message.content or "").strip()
        return self._parse_fallback_response(content, line_items_sum)
    
    def _build_prompt(
        self,
        footer_text: str,
        line_items_sum: Optional[float] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        page_context: Optional[str] = None,
        strict_json_instruction: bool = False,
    ) -> str:
        """Build prompt for AI extraction."""
        prompt = "Extract the total amount (totalsumma / att betala) from this Swedish invoice.\n\n"
        if page_context:
            prompt += """Use the FULL PAGE TEXT below as the source of truth. Focus on normal left-to-right lines (Nettobelopp, Momsbelopp, Att betala: SEK). Reversed/watermark-like lines have been filtered out.

--- FULL PAGE (header, items, footer) ---
"""
            prompt += page_context
            prompt += "\n--- END FULL PAGE ---\n\n"
        else:
            prompt += f"Footer text:\n{footer_text}\n\n"
        if line_items_sum is not None:
            prompt += f"Line items sum: {line_items_sum:.2f} SEK. Use to validate if plausible; if it looks wrong (e.g. very small vs large page amounts), ignore it and use the page text. Total often equals or slightly exceeds line sum (VAT, rounding).\n"
        if candidates and not page_context:
            parts = [f"{c.get('amount')} SEK ({c.get('keyword_type', '?')})" for c in candidates]
            prompt += f"We detected these candidates: {', '.join(parts)}. Prefer 'with_vat' (att betala) when relevant.\n"
        elif candidates and page_context:
            parts = [f"{c.get('amount')} SEK ({c.get('keyword_type', '?')})" for c in candidates]
            prompt += f"Heuristic candidates (may be wrong): {', '.join(parts)}. Prefer the amount from the full page text.\n"
        prompt += """
Return:
- total_amount: The extracted total as float
- confidence: 0.0-1.0
- reasoning: Brief explanation
- validation_passed: True if (a) total matches line items sum within ±1 SEK, OR (b) total is clearly from page (e.g. Att betala, Nettobelopp+Moms) and line_items_sum seems wrong—then trust the footer and set True.
"""
        if strict_json_instruction:
            prompt += "\nReturn only valid JSON matching this schema; no additional text or markdown.\n"
        return prompt

    def _parse_fallback_response(
        self,
        content: str,
        line_items_sum: Optional[float] = None
    ) -> Dict[str, Any]:
        """Parse fallback response if structured output fails (JSON or plain text)."""
        import json
        import re
        # Try JSON first (e.g. from vision or strict retry)
        content_stripped = content.strip()
        for start in ("{", "```json", "```"):
            try:
                idx = content_stripped.find(start)
                if idx < 0:
                    continue
                if start == "```json":
                    idx = content_stripped.find("{", idx)
                if idx < 0:
                    continue
                end = content_stripped.rfind("}")
                if end > idx:
                    js = content_stripped[idx : end + 1]
                    data = json.loads(js)
                    r = AITotalResponse(**data)
                    return {"total_amount": r.total_amount, "confidence": r.confidence, "reasoning": r.reasoning, "validation_passed": r.validation_passed}
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        numbers = re.findall(r"\d+[.,]\d+|\d+", content)
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
        line_items_sum: Optional[float] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        page_context: Optional[str] = None,
        image_path: Optional[str] = None,
        strict_json_instruction: bool = False,
    ) -> Dict[str, Any]:
        """Extract total amount using Claude API (text or vision)."""
        prompt = self._build_prompt(
            footer_text, line_items_sum, candidates=candidates, page_context=page_context,
            strict_json_instruction=strict_json_instruction
        )
        if image_path:
            img_bytes, mime = _prepare_vision_image(image_path)
            b64 = base64.b64encode(img_bytes).decode("ascii")
            user_content: List[Any] = [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text", "text": prompt},
            ]
        else:
            user_content = prompt
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": user_content}],
            )
            content = response.content[0].text
            return self._parse_json_response(content, line_items_sum)
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    def _build_prompt(
        self,
        footer_text: str,
        line_items_sum: Optional[float] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
        page_context: Optional[str] = None,
        strict_json_instruction: bool = False,
    ) -> str:
        """Build prompt for AI extraction."""
        prompt = "Extract the total amount (totalsumma / att betala) from this Swedish invoice.\n\n"
        if page_context:
            prompt += """Use the FULL PAGE TEXT below as the source of truth. Focus on normal left-to-right lines (Nettobelopp, Momsbelopp, Att betala: SEK). Reversed/watermark-like lines have been filtered out.

--- FULL PAGE (header, items, footer) ---
"""
            prompt += page_context
            prompt += "\n--- END FULL PAGE ---\n\n"
        else:
            prompt += f"Footer text:\n{footer_text}\n\n"
        if line_items_sum is not None:
            prompt += f"Line items sum: {line_items_sum:.2f} SEK. Use to validate if plausible; if it looks wrong (e.g. very small vs large page amounts), ignore it and use the page text. Total often equals or slightly exceeds line sum (VAT, rounding).\n"
        if candidates and not page_context:
            parts = [f"{c.get('amount')} SEK ({c.get('keyword_type', '?')})" for c in candidates]
            prompt += f"We detected these candidates: {', '.join(parts)}. Prefer 'with_vat' (att betala) when relevant.\n"
        elif candidates and page_context:
            parts = [f"{c.get('amount')} SEK ({c.get('keyword_type', '?')})" for c in candidates]
            prompt += f"Heuristic candidates (may be wrong): {', '.join(parts)}. Prefer the amount from the full page text.\n"
        prompt += """
Return JSON: {"total_amount": float, "confidence": 0.0-1.0, "reasoning": "...", "validation_passed": true/false}
validation_passed: true if (a) total matches line items sum within ±1 SEK, OR (b) total is clearly from page (Att betala, Nettobelopp+Moms) and line_items_sum seems wrong—then trust footer, set true.
"""
        if strict_json_instruction:
            prompt += "\nReturn only valid JSON matching the schema above; no additional text or markdown.\n"
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

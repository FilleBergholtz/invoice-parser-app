"""HTTP client for AI enrichment service."""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests

from .schemas import AIInvoiceRequest, AIInvoiceResponse

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """Base exception for AI client errors."""
    pass


class AIConnectionError(AIClientError):
    """Raised when connection to AI service fails."""
    pass


class AIAPIError(AIClientError):
    """Raised when AI API returns an error."""
    pass


class AIClient:
    """Client for AI enrichment service."""
    
    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """Initialize AI client.
        
        Args:
            endpoint: Base URL for AI service (e.g., "https://api.example.com/v1/")
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint.rstrip('/') + '/'
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        self.session.headers.update(headers)
    
    def enrich_invoice(
        self,
        request: AIInvoiceRequest
    ) -> AIInvoiceResponse:
        """Enrich invoice data using AI service.
        
        Args:
            request: Invoice data to enrich
            
        Returns:
            AI-enriched invoice data
            
        Raises:
            AIConnectionError: If connection fails
            AIAPIError: If API returns an error
        """
        url = urljoin(self.endpoint, 'enrich')
        
        try:
            response = self.session.post(
                url,
                json=request.to_dict(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return AIInvoiceResponse.from_dict(response.json())
            
        except requests.exceptions.Timeout:
            raise AIConnectionError(f"Request to {url} timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise AIConnectionError(f"Failed to connect to {url}: {e}")
        except requests.exceptions.HTTPError as e:
            error_msg = f"API error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('error', 'Unknown error')}"
            except:
                error_msg += f" - {e.response.text[:200]}"
            raise AIAPIError(error_msg)
        except Exception as e:
            raise AIClientError(f"Unexpected error: {e}")
    
    def health_check(self) -> bool:
        """Check if AI service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        url = urljoin(self.endpoint, 'health')
        try:
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False


def create_ai_diff(
    original: AIInvoiceRequest,
    enriched: AIInvoiceResponse
) -> Dict[str, Any]:
    """Create diff between original and enriched data.
    
    Args:
        original: Original invoice data
        enriched: AI-enriched invoice data
        
    Returns:
        Dictionary with differences
    """
    diff = {
        'header_changes': {},
        'line_item_changes': []
    }
    
    # Compare header fields
    if original.invoice_number != enriched.invoice_number:
        diff['header_changes']['invoice_number'] = {
            'original': original.invoice_number,
            'enriched': enriched.invoice_number
        }
    
    if original.invoice_date != enriched.invoice_date:
        diff['header_changes']['invoice_date'] = {
            'original': original.invoice_date,
            'enriched': enriched.invoice_date
        }
    
    if original.supplier_name != enriched.supplier_name:
        diff['header_changes']['supplier_name'] = {
            'original': original.supplier_name,
            'enriched': enriched.supplier_name
        }
    
    if original.total_amount != enriched.total_amount:
        diff['header_changes']['total_amount'] = {
            'original': original.total_amount,
            'enriched': enriched.total_amount
        }
    
    # Compare line items
    for i, (orig_line, enrich_line) in enumerate(zip(original.line_items, enriched.line_items)):
        line_diff = {}
        if orig_line.description != enrich_line.description:
            line_diff['description'] = {
                'original': orig_line.description,
                'enriched': enrich_line.description
            }
        if orig_line.quantity != enrich_line.quantity:
            line_diff['quantity'] = {
                'original': orig_line.quantity,
                'enriched': enrich_line.quantity
            }
        if orig_line.unit_price != enrich_line.unit_price:
            line_diff['unit_price'] = {
                'original': orig_line.unit_price,
                'enriched': enrich_line.unit_price
            }
        if orig_line.total_amount != enrich_line.total_amount:
            line_diff['total_amount'] = {
                'original': orig_line.total_amount,
                'enriched': enrich_line.total_amount
            }
        
        if line_diff:
            line_diff['line_number'] = i + 1
            diff['line_item_changes'].append(line_diff)
    
    return diff


def save_ai_artifacts(
    artifacts_dir: Path,
    request: AIInvoiceRequest,
    response: Optional[AIInvoiceResponse] = None,
    diff: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):
    """Save AI artifacts to artifacts directory.
    
    Args:
        artifacts_dir: Directory to save artifacts
        request: Original request
        response: AI response (if available)
        diff: Diff between original and enriched (if available)
        error: Error message (if request failed)
    """
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Save request
    request_path = artifacts_dir / 'ai_request.json'
    with open(request_path, 'w', encoding='utf-8') as f:
        json.dump(request.to_dict(), f, indent=2, ensure_ascii=False)
    
    # Save response (if available)
    if response:
        response_path = artifacts_dir / 'ai_response.json'
        with open(response_path, 'w', encoding='utf-8') as f:
            json.dump({
                'invoice_number': response.invoice_number,
                'invoice_date': response.invoice_date,
                'supplier_name': response.supplier_name,
                'customer_name': response.customer_name,
                'total_amount': response.total_amount,
                'line_items': [
                    {
                        'description': item.description,
                        'quantity': item.quantity,
                        'unit': item.unit,
                        'unit_price': item.unit_price,
                        'discount': item.discount,
                        'total_amount': item.total_amount,
                        'line_number': item.line_number,
                        'confidence': item.confidence,
                        'category': item.category
                    }
                    for item in response.line_items
                ],
                'confidence': response.confidence,
                'warnings': response.warnings,
                'suggestions': response.suggestions
            }, f, indent=2, ensure_ascii=False)
    
    # Save diff (if available)
    if diff:
        diff_path = artifacts_dir / 'ai_diff.json'
        with open(diff_path, 'w', encoding='utf-8') as f:
            json.dump(diff, f, indent=2, ensure_ascii=False)
    
    # Save error (if request failed)
    if error:
        error_path = artifacts_dir / 'ai_error.json'
        with open(error_path, 'w', encoding='utf-8') as f:
            json.dump({'error': error, 'timestamp': str(Path(__file__).stat().st_mtime)}, f, indent=2)

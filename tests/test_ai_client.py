"""Unit tests for AI client."""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from src.ai.client import (
    AIClient, AIClientError, AIConnectionError, AIAPIError,
    create_ai_diff, save_ai_artifacts
)
from src.ai.schemas import AIInvoiceRequest, AIInvoiceLineRequest, AIInvoiceResponse, AIInvoiceLineResponse


class TestAIClient:
    """Test AI client functionality."""
    
    def test_init(self):
        """Test client initialization."""
        client = AIClient("https://api.example.com/v1", "test-key")
        assert client.endpoint == "https://api.example.com/v1/"
        assert client.api_key == "test-key"
        assert client.timeout == 30
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "Bearer test-key"
    
    def test_init_no_key(self):
        """Test client initialization without API key."""
        client = AIClient("https://api.example.com/v1")
        assert client.api_key is None
        assert "Authorization" not in client.session.headers
    
    @patch('src.ai.client.requests.Session.post')
    def test_enrich_invoice_success(self, mock_post):
        """Test successful invoice enrichment."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "invoice_number": "INV-123",
            "invoice_date": "2024-01-15",
            "supplier_name": "Test Supplier",
            "total_amount": 1000.0,
            "line_items": [
                {
                    "description": "Item 1",
                    "quantity": 2.0,
                    "unit_price": 100.0,
                    "total_amount": 200.0,
                    "line_number": 1,
                    "confidence": 0.95
                }
            ],
            "confidence": 0.90
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Create client and request
        client = AIClient("https://api.example.com/v1", "test-key")
        request = AIInvoiceRequest(
            invoice_number="INV-123",
            invoice_date="2024-01-15",
            supplier_name="Test Supplier",
            total_amount=1000.0,
            line_items=[
                AIInvoiceLineRequest(
                    description="Item 1",
                    quantity=2.0,
                    unit_price=100.0,
                    total_amount=200.0,
                    line_number=1
                )
            ]
        )
        
        # Call enrich
        response = client.enrich_invoice(request)
        
        # Verify
        assert response.invoice_number == "INV-123"
        assert response.total_amount == 1000.0
        assert len(response.line_items) == 1
        assert response.line_items[0].description == "Item 1"
        assert response.confidence == 0.90
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.example.com/v1/enrich"
        assert call_args[1]['json'] == request.to_dict()
    
    @patch('src.ai.client.requests.Session.post')
    def test_enrich_invoice_timeout(self, mock_post):
        """Test timeout handling."""
        mock_post.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        client = AIClient("https://api.example.com/v1", "test-key")
        request = AIInvoiceRequest()
        
        with pytest.raises(AIConnectionError) as exc_info:
            client.enrich_invoice(request)
        
        assert "timed out" in str(exc_info.value)
    
    @patch('src.ai.client.requests.Session.post')
    def test_enrich_invoice_connection_error(self, mock_post):
        """Test connection error handling."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        client = AIClient("https://api.example.com/v1", "test-key")
        request = AIInvoiceRequest()
        
        with pytest.raises(AIConnectionError) as exc_info:
            client.enrich_invoice(request)
        
        assert "Failed to connect" in str(exc_info.value)
    
    @patch('src.ai.client.requests.Session.post')
    def test_enrich_invoice_api_error(self, mock_post):
        """Test API error handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid request"}
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        
        client = AIClient("https://api.example.com/v1", "test-key")
        request = AIInvoiceRequest()
        
        with pytest.raises(AIAPIError) as exc_info:
            client.enrich_invoice(request)
        
        assert "API error" in str(exc_info.value)
        assert "400" in str(exc_info.value)
    
    @patch('src.ai.client.requests.Session.get')
    def test_health_check_success(self, mock_get):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        client = AIClient("https://api.example.com/v1", "test-key")
        assert client.health_check() is True
    
    @patch('src.ai.client.requests.Session.get')
    def test_health_check_failure(self, mock_get):
        """Test failed health check."""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        client = AIClient("https://api.example.com/v1", "test-key")
        assert client.health_check() is False


class TestAIDiff:
    """Test AI diff functionality."""
    
    def test_create_ai_diff_no_changes(self):
        """Test diff with no changes."""
        request = AIInvoiceRequest(
            invoice_number="INV-123",
            total_amount=1000.0
        )
        response = AIInvoiceResponse(
            invoice_number="INV-123",
            total_amount=1000.0
        )
        
        diff = create_ai_diff(request, response)
        assert not diff['header_changes']
        assert not diff['line_item_changes']
    
    def test_create_ai_diff_header_changes(self):
        """Test diff with header changes."""
        request = AIInvoiceRequest(
            invoice_number="INV-123",
            total_amount=1000.0
        )
        response = AIInvoiceResponse(
            invoice_number="INV-456",
            total_amount=1200.0
        )
        
        diff = create_ai_diff(request, response)
        assert 'invoice_number' in diff['header_changes']
        assert 'total_amount' in diff['header_changes']
        assert diff['header_changes']['invoice_number']['original'] == "INV-123"
        assert diff['header_changes']['invoice_number']['enriched'] == "INV-456"
    
    def test_create_ai_diff_line_changes(self):
        """Test diff with line item changes."""
        request = AIInvoiceRequest(
            line_items=[
                AIInvoiceLineRequest(description="Item 1", quantity=2.0, total_amount=200.0)
            ]
        )
        response = AIInvoiceResponse(
            line_items=[
                AIInvoiceLineResponse(description="Item 1 Updated", quantity=3.0, total_amount=300.0)
            ]
        )
        
        diff = create_ai_diff(request, response)
        assert len(diff['line_item_changes']) == 1
        assert 'description' in diff['line_item_changes'][0]
        assert 'quantity' in diff['line_item_changes'][0]


class TestSaveArtifacts:
    """Test artifact saving functionality."""
    
    def test_save_ai_artifacts(self, tmp_path):
        """Test saving AI artifacts."""
        artifacts_dir = tmp_path / "artifacts"
        
        request = AIInvoiceRequest(invoice_number="INV-123")
        response = AIInvoiceResponse(invoice_number="INV-456")
        diff = {"header_changes": {"invoice_number": {"original": "INV-123", "enriched": "INV-456"}}}
        
        save_ai_artifacts(artifacts_dir, request, response, diff)
        
        # Verify files were created
        assert (artifacts_dir / "ai_request.json").exists()
        assert (artifacts_dir / "ai_response.json").exists()
        assert (artifacts_dir / "ai_diff.json").exists()
        
        # Verify content
        with open(artifacts_dir / "ai_request.json", 'r', encoding='utf-8') as f:
            request_data = json.load(f)
            assert request_data['invoice_number'] == "INV-123"
        
        with open(artifacts_dir / "ai_response.json", 'r', encoding='utf-8') as f:
            response_data = json.load(f)
            assert response_data['invoice_number'] == "INV-456"
    
    def test_save_ai_artifacts_with_error(self, tmp_path):
        """Test saving AI artifacts with error."""
        artifacts_dir = tmp_path / "artifacts"
        
        request = AIInvoiceRequest(invoice_number="INV-123")
        
        save_ai_artifacts(artifacts_dir, request, error="Connection failed")
        
        # Verify error file was created
        assert (artifacts_dir / "ai_error.json").exists()
        
        with open(artifacts_dir / "ai_error.json", 'r', encoding='utf-8') as f:
            error_data = json.load(f)
            assert error_data['error'] == "Connection failed"

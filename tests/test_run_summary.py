"""Tests for run summary functionality."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from src.run_summary import RunSummary
from src.cli.main import process_batch

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir

@pytest.fixture
def temp_input_dir(tmp_path):
    """Create a temporary input directory with a dummy PDF."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    
    # Create dummy PDF file
    pdf_path = input_dir / "test.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n...")
        
    return input_dir

def test_run_summary_creation(temp_output_dir):
    """Test RunSummary model creation and serialization."""
    summary = RunSummary.create(
        input_path="input",
        output_dir=str(temp_output_dir)
    )
    
    assert summary.run_id is not None
    assert summary.input_path == "input"
    assert summary.output_dir == str(temp_output_dir)
    assert summary.status == "RUNNING"
    assert summary.started_at is not None
    
    # Test saving
    summary.complete(status="COMPLETED")
    summary_path = temp_output_dir / "summary.json"
    summary.save(summary_path)
    
    assert summary_path.exists()
    
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["run_id"] == summary.run_id
        assert data["status"] == "COMPLETED"
        assert data["finished_at"] is not None

@patch("src.cli.main.process_pdf")
def test_process_batch_creates_summary(mock_process_pdf, temp_input_dir, temp_output_dir):
    """Test that process_batch creates a run summary."""
    # Mock successful processing
    mock_result = MagicMock()
    mock_result.status = "OK"
    mock_result.virtual_invoice_id = "test__1"
    mock_result.virtual_invoice_index = 1
    mock_result.invoice_header = MagicMock()
    mock_result.invoice_header.invoice_number = "INV-123"
    mock_result.invoice_header.invoice_date = None  # Will be set if needed
    mock_result.invoice_header.total_amount = 100.0
    mock_result.invoice_header.supplier_name = "Test Supplier"
    mock_result.invoice_header.customer_name = None
    mock_result.invoice_header.invoice_number_confidence = 0.95
    mock_result.invoice_header.total_confidence = 0.90
    mock_result.validation_result = MagicMock()
    mock_result.validation_result.status = "OK"
    mock_result.validation_result.diff = 0.0
    mock_result.validation_result.lines_sum = 100.0
    mock_result.validation_result.hard_gate_passed = True
    # Create mock invoice lines with all required attributes
    # Using a simple object with real values instead of MagicMock to avoid serialization issues
    from types import SimpleNamespace
    mock_line = SimpleNamespace()
    mock_line.rows = []  # Empty list for rows
    mock_line.description = "Test Product"
    mock_line.quantity = 1.0
    mock_line.unit = "st"
    mock_line.unit_price = 100.0
    mock_line.discount = None
    mock_line.total_amount = 100.0
    mock_line.vat_rate = None
    mock_line.line_number = 1
    mock_line.segment = None
    mock_result.invoice_lines = [mock_line]
    mock_result.line_count = 1  # Match number of invoice_lines
    # Explicitly set ai_request to None to avoid MagicMock auto-creation
    mock_result.ai_request = None
    # Avoid MagicMock leaking into Excel export (getattr(virtual_result, "extraction_source", None))
    mock_result.extraction_source = None

    # Needs to return a list of virtual results
    mock_process_pdf.return_value = [mock_result]
    
    process_batch(
        input_path=str(temp_input_dir),
        output_dir=str(temp_output_dir)
    )
    
    # Check if run_summary.json exists
    summary_path = temp_output_dir / "run_summary.json"
    assert summary_path.exists()
    
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["total_files"] == 1
        assert data["processed_files"] == 1
        assert data["ok_count"] == 1
        assert data["status"] == "COMPLETED"
        assert "artifacts" in data["artifacts_dir"]

@patch("src.cli.main.process_pdf")
def test_process_batch_artifacts_dir(mock_process_pdf, temp_input_dir, temp_output_dir):
    """Test custom artifacts directory."""
    # Mock successful processing
    mock_process_pdf.return_value = []
    
    custom_artifacts = temp_output_dir / "custom_artifacts"
    
    process_batch(
        input_path=str(temp_input_dir),
        output_dir=str(temp_output_dir),
        artifacts_dir=str(custom_artifacts)
    )
    
    summary_path = temp_output_dir / "run_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["artifacts_dir"] == str(custom_artifacts)
    
    assert custom_artifacts.exists()

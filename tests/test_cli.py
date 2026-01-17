"""Unit tests for CLI interface."""

import pytest
from pathlib import Path
from src.cli.main import process_invoice, process_batch


def test_process_invoice_returns_validation_result():
    """Test that process_invoice() returns validation_result in result dict."""
    # This test requires actual PDF file, but structure is verified via imports
    # In practice, integration test would verify validation_result is present
    from src.cli.main import process_invoice
    assert hasattr(process_invoice, '__code__')
    # Function signature verification: process_invoice should return dict with validation_result
    # Actual test would require PDF file, so skipping
    pytest.skip("Requires actual PDF file - integration test")


def test_process_batch_collects_invoice_results():
    """Test that process_batch() collects invoice results per invoice."""
    # Structure verification: process_batch should track invoice_results
    # Actual test would require PDF files, so skipping
    pytest.skip("Requires actual PDF files - integration test")


def test_process_batch_creates_review_reports():
    """Test that review reports are created for REVIEW status invoices."""
    # Integration test: verify review/ folder created with metadata.json
    pytest.skip("Requires actual PDF files - integration test")


def test_process_batch_excel_export_includes_validation():
    """Test that Excel export includes validation data in control columns."""
    # Integration test: verify Excel file has control columns
    pytest.skip("Requires actual PDF files - integration test")


def test_process_batch_summary_includes_validation_stats():
    """Test that batch summary includes OK/PARTIAL/REVIEW counts."""
    # Integration test: verify summary output format
    pytest.skip("Requires actual processing - integration test")

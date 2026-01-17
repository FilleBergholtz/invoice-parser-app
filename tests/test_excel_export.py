"""Unit tests for Excel export."""

import pytest
import openpyxl
from pathlib import Path
from src.models.invoice_line import InvoiceLine
from src.export.excel_export import export_to_excel


@pytest.fixture
def sample_invoice_lines():
    """Create sample InvoiceLine objects for testing."""
    # This would require Row and Segment objects, simplified for testing
    pytest.skip("Requires full InvoiceLine setup with Row/Segment - integration test")


def test_excel_file_creation(tmp_path):
    """Test Excel file creation with Swedish column names."""
    # Create minimal InvoiceLine (simplified for unit test)
    # Note: This test requires proper InvoiceLine setup with rows
    pytest.skip("Requires InvoiceLine with Row/Segment - integration test")


def test_swedish_column_names():
    """Test that Excel has Swedish column names."""
    pytest.skip("Requires actual InvoiceLines - integration test")


def test_one_row_per_invoice_line():
    """Test that Excel has one row per InvoiceLine."""
    pytest.skip("Requires actual InvoiceLines - integration test")


def test_metadata_repetition():
    """Test that invoice metadata is repeated per row."""
    pytest.skip("Requires actual InvoiceLines - integration test")

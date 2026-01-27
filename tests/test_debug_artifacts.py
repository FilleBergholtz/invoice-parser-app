"""Unit tests for table debug artifacts (Phase 22)."""

import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.debug.table_debug import save_table_debug_artifacts
from src.models.document import Document
from src.models.invoice_line import InvoiceLine
from src.models.page import Page
from src.models.row import Row
from src.models.token import Token
from src.models.validation_result import ValidationResult


@pytest.fixture
def sample_page():
    """Create a sample page for testing."""
    doc = Document(filename="test.pdf", filepath="test.pdf", page_count=0, pages=[])
    page = Page(page_number=1, width=612, height=792, document=doc)
    doc.pages.append(page)
    doc.page_count = 1
    return page


@pytest.fixture
def table_rows(sample_page):
    """Create sample table rows."""
    rows = []
    
    # Row 1
    tokens1 = [
        Token(text="Product", x=50, y=100, width=200, height=12, page=sample_page),
        Token(text="5", x=300, y=100, width=20, height=12, page=sample_page),
        Token(text="100.00", x=450, y=100, width=60, height=12, page=sample_page),
    ]
    row1 = Row(tokens=tokens1, text="Product 5 100.00", x_min=50, x_max=510, y=100, page=sample_page)
    rows.append(row1)
    
    # Row 2
    tokens2 = [
        Token(text="Service", x=50, y=120, width=200, height=12, page=sample_page),
        Token(text="2", x=300, y=120, width=20, height=12, page=sample_page),
        Token(text="50.00", x=450, y=120, width=60, height=12, page=sample_page),
    ]
    row2 = Row(tokens=tokens2, text="Service 2 50.00", x_min=50, x_max=510, y=120, page=sample_page)
    rows.append(row2)
    
    return rows


@pytest.fixture
def line_items(sample_page, table_rows):
    """Create sample invoice lines."""
    segment = None  # Not needed for this test
    return [
        InvoiceLine(
            rows=[table_rows[0]],
            description="Product",
            quantity=Decimal("5"),
            unit="st",
            unit_price=Decimal("100.00"),
            total_amount=Decimal("500.00"),
            line_number=1,
            segment=segment
        ),
        InvoiceLine(
            rows=[table_rows[1]],
            description="Service",
            quantity=Decimal("2"),
            unit="h",
            unit_price=Decimal("50.00"),
            total_amount=Decimal("100.00"),
            line_number=2,
            segment=segment
        ),
    ]


@pytest.fixture
def validation_result():
    """Create sample validation result."""
    return ValidationResult(
        status="REVIEW",
        lines_sum=Decimal("600.00"),
        diff=Decimal("50.00"),
        tolerance=Decimal("0.50"),
        hard_gate_passed=False,
        invoice_number_confidence=0.90,
        total_confidence=0.85,
        errors=["Mode B validation failed: diff=50.00 SEK"],
        warnings=["Mode A also failed: diff=60.00 SEK"]
    )


class TestSaveTableDebugArtifacts:
    """Tests for save_table_debug_artifacts function."""
    
    def test_save_table_debug_artifacts(self, table_rows, line_items, validation_result):
        """Test that debug artifacts are saved correctly."""
        with TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)
            invoice_id = "test_invoice_001"
            
            save_table_debug_artifacts(
                artifacts_dir=artifacts_dir,
                invoice_id=invoice_id,
                table_rows=table_rows,
                line_items=line_items,
                validation_result=validation_result,
                netto_total=Decimal("650.00"),
                mode_used="B"
            )
            
            # Check that debug directory was created
            debug_dir = artifacts_dir / "invoices" / invoice_id / "table_debug"
            assert debug_dir.exists()
            
            # Check that all files were created
            raw_text_path = debug_dir / "table_block_raw_text.txt"
            parsed_lines_path = debug_dir / "parsed_lines.json"
            validation_result_path = debug_dir / "validation_result.json"
            tokens_path = debug_dir / "table_block_tokens.json"
            
            assert raw_text_path.exists()
            assert parsed_lines_path.exists()
            assert validation_result_path.exists()
            assert tokens_path.exists()
    
    def test_table_block_raw_text_format(self, table_rows, line_items, validation_result):
        """Test that raw text file has correct format."""
        with TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)
            invoice_id = "test_invoice_002"
            
            save_table_debug_artifacts(
                artifacts_dir=artifacts_dir,
                invoice_id=invoice_id,
                table_rows=table_rows,
                line_items=line_items,
                validation_result=validation_result,
                netto_total=Decimal("650.00"),
                mode_used="A"
            )
            
            raw_text_path = artifacts_dir / "invoices" / invoice_id / "table_debug" / "table_block_raw_text.txt"
            
            with open(raw_text_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Should contain row texts, newline-separated
            assert "Product 5 100.00" in content
            assert "Service 2 50.00" in content
            assert content.count('\n') == len(table_rows)  # One line per row
    
    def test_parsed_lines_json_format(self, table_rows, line_items, validation_result):
        """Test that parsed_lines.json has correct format."""
        with TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)
            invoice_id = "test_invoice_003"
            
            save_table_debug_artifacts(
                artifacts_dir=artifacts_dir,
                invoice_id=invoice_id,
                table_rows=table_rows,
                line_items=line_items,
                validation_result=validation_result,
                netto_total=Decimal("650.00"),
                mode_used="B"
            )
            
            parsed_lines_path = artifacts_dir / "invoices" / invoice_id / "table_debug" / "parsed_lines.json"
            
            with open(parsed_lines_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check structure
            assert 'timestamp' in data
            assert 'line_count' in data
            assert 'lines' in data
            assert data['line_count'] == len(line_items)
            
            # Check line data
            assert len(data['lines']) == 2
            line1 = data['lines'][0]
            assert line1['line_number'] == 1
            assert line1['description'] == "Product"
            assert line1['quantity'] == "5"
            assert line1['unit'] == "st"
            assert line1['unit_price'] == "100.00"
            assert line1['total_amount'] == "500.00"
    
    def test_validation_result_json_format(self, table_rows, line_items, validation_result):
        """Test that validation_result.json has correct format."""
        with TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)
            invoice_id = "test_invoice_004"
            
            save_table_debug_artifacts(
                artifacts_dir=artifacts_dir,
                invoice_id=invoice_id,
                table_rows=table_rows,
                line_items=line_items,
                validation_result=validation_result,
                netto_total=Decimal("650.00"),
                mode_used="B"
            )
            
            validation_result_path = artifacts_dir / "invoices" / invoice_id / "table_debug" / "validation_result.json"
            
            with open(validation_result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check structure
            assert 'timestamp' in data
            assert 'mode_used' in data
            assert 'netto_sum' in data
            assert 'netto_total' in data
            assert 'diff' in data
            assert 'validation_passed' in data
            assert 'status' in data
            assert 'errors' in data
            assert 'warnings' in data
            
            # Check values
            assert data['mode_used'] == "B"
            assert data['netto_sum'] == "600.00"
            assert data['netto_total'] == "650.00"
            assert data['diff'] == "50.00"
            assert data['validation_passed'] is False
            assert data['status'] == "REVIEW"
            assert len(data['errors']) > 0
            assert len(data['warnings']) > 0
    
    def test_table_block_tokens_json_format(self, table_rows, line_items, validation_result):
        """Test that table_block_tokens.json has correct format."""
        with TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)
            invoice_id = "test_invoice_005"
            
            save_table_debug_artifacts(
                artifacts_dir=artifacts_dir,
                invoice_id=invoice_id,
                table_rows=table_rows,
                line_items=line_items,
                validation_result=validation_result,
                netto_total=Decimal("650.00"),
                mode_used="A"
            )
            
            tokens_path = artifacts_dir / "invoices" / invoice_id / "table_debug" / "table_block_tokens.json"
            
            with open(tokens_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check structure
            assert 'timestamp' in data
            assert 'row_count' in data
            assert 'rows' in data
            assert data['row_count'] == len(table_rows)
            
            # Check row data
            assert len(data['rows']) == 2
            row1 = data['rows'][0]
            assert row1['row_index'] == 0
            assert row1['text'] == "Product 5 100.00"
            assert 'tokens' in row1
            assert len(row1['tokens']) == 3  # Product, 5, 100.00
            
            # Check token data
            token1 = row1['tokens'][0]
            assert 'text' in token1
            assert 'x' in token1
            assert 'y' in token1
            assert 'width' in token1
            assert 'height' in token1
    
    def test_debug_artifacts_on_mismatch(self, table_rows, line_items):
        """Test that artifacts are saved when validation mismatch occurs."""
        with TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)
            invoice_id = "test_invoice_006"
            
            # Create validation result with mismatch
            validation_result = ValidationResult(
                status="REVIEW",
                lines_sum=Decimal("600.00"),
                diff=Decimal("50.00"),  # Mismatch
                tolerance=Decimal("0.50"),
                hard_gate_passed=False,
                errors=["Validation failed"],
                warnings=[]
            )
            
            save_table_debug_artifacts(
                artifacts_dir=artifacts_dir,
                invoice_id=invoice_id,
                table_rows=table_rows,
                line_items=line_items,
                validation_result=validation_result,
                netto_total=Decimal("650.00"),
                mode_used="B"
            )
            
            # Check that files were created
            debug_dir = artifacts_dir / "invoices" / invoice_id / "table_debug"
            assert debug_dir.exists()
            
            validation_result_path = debug_dir / "validation_result.json"
            with open(validation_result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Should indicate mismatch
            assert data['validation_passed'] is False
            assert data['status'] == "REVIEW"
            assert float(data['diff']) > 0.50  # Outside tolerance
    
    def test_debug_artifacts_with_none_netto_total(self, table_rows, line_items, validation_result):
        """Test that artifacts work with None netto_total."""
        with TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)
            invoice_id = "test_invoice_007"
            
            save_table_debug_artifacts(
                artifacts_dir=artifacts_dir,
                invoice_id=invoice_id,
                table_rows=table_rows,
                line_items=line_items,
                validation_result=validation_result,
                netto_total=None,  # None netto_total
                mode_used="A"
            )
            
            validation_result_path = artifacts_dir / "invoices" / invoice_id / "table_debug" / "validation_result.json"
            
            with open(validation_result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # netto_total should be None in JSON
            assert data['netto_total'] is None

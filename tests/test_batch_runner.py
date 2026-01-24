"""Unit tests for batch processing runner."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.batch.runner import process_pdf_isolated, run_batch
from src.batch.batch_summary import create_batch_summary
from src.models.virtual_invoice_result import VirtualInvoiceResult
from src.models.validation_result import ValidationResult
from src.models.invoice_header import InvoiceHeader
from src.models.invoice_line import InvoiceLine


class TestProcessPdfIsolated:
    """Test isolated PDF processing."""
    
    @patch('src.cli.main.process_pdf')
    def test_process_pdf_success(self, mock_process_pdf, tmp_path):
        """Test successful PDF processing."""
        from unittest.mock import Mock
        from datetime import date
        
        # Setup mock
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b'fake pdf')
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create mock virtual invoice result
        segment = Mock()
        segment.rows = []
        header = InvoiceHeader(
            segment=segment,
            invoice_number="INV-123",
            invoice_date=date(2024, 1, 15),
            total_amount=1000.0,
            invoice_number_confidence=0.98,
            total_confidence=0.97,
            raw_text="Test"
        )
        
        row = Mock()
        line = InvoiceLine(rows=[row], description="Item", total_amount=1000.0, line_number=1)
        
        validation = ValidationResult(
            status="OK",
            lines_sum=1000.0,
            diff=0.0,
            hard_gate_passed=True,
            invoice_number_confidence=0.98,
            total_confidence=0.97
        )
        
        virtual_result = VirtualInvoiceResult(
            virtual_invoice_id="test__1",
            source_pdf="test.pdf",
            virtual_invoice_index=1,
            page_start=1,
            page_end=1,
            status="OK",
            invoice_header=header,
            invoice_lines=[line],
            validation_result=validation
        )
        
        mock_process_pdf.return_value = [virtual_result]
        
        # Process
        result = process_pdf_isolated(pdf_path, output_dir, verbose=False)
        
        # Verify
        assert result["filename"] == "test.pdf"
        assert result["status"] == "OK"
        assert result["quality_score"] > 0.0
        assert result["error"] is None
        assert len(result["virtual_invoices"]) == 1
    
    @patch('src.cli.main.process_pdf')
    def test_process_pdf_no_invoices(self, mock_process_pdf, tmp_path):
        """Test PDF with no invoices."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b'fake pdf')
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        mock_process_pdf.return_value = []
        
        result = process_pdf_isolated(pdf_path, output_dir, verbose=False)
        
        assert result["status"] == "FAILED"
        assert result["quality_score"] == 0.0
        assert "No invoices found" in result["error"]
    
    @patch('src.cli.main.process_pdf')
    def test_process_pdf_exception(self, mock_process_pdf, tmp_path):
        """Test exception during processing."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b'fake pdf')
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        mock_process_pdf.side_effect = Exception("Processing error")
        
        result = process_pdf_isolated(pdf_path, output_dir, verbose=False)
        
        assert result["status"] == "FAILED"
        assert result["quality_score"] == 0.0
        assert "Processing error" in result["error"]


class TestRunBatch:
    """Test batch processing."""
    
    @patch('src.batch.runner.process_pdf_isolated')
    def test_run_batch_success(self, mock_process_pdf, tmp_path):
        """Test successful batch processing."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        
        # Create test PDFs
        (input_dir / "invoice1.pdf").write_bytes(b'pdf1')
        (input_dir / "invoice2.pdf").write_bytes(b'pdf2')
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock results
        mock_process_pdf.side_effect = [
            {
                "filename": "invoice1.pdf",
                "status": "OK",
                "quality_score": 95.0,
                "output_path": str(output_dir / "invoice1.xlsx"),
                "error": None,
                "virtual_invoices": []
            },
            {
                "filename": "invoice2.pdf",
                "status": "PARTIAL",
                "quality_score": 80.0,
                "output_path": str(output_dir / "invoice2.xlsx"),
                "error": None,
                "virtual_invoices": []
            }
        ]
        
        results = run_batch(input_dir, output_dir, fail_fast=False, verbose=False)
        
        assert results["total_files"] == 2
        assert results["processed"] == 2
        assert results["ok"] == 1
        assert results["partial"] == 1
        assert results["failed"] == 0
        assert len(results["results"]) == 2
    
    @patch('src.batch.runner.process_pdf_isolated')
    def test_run_batch_with_failures(self, mock_process_pdf, tmp_path):
        """Test batch processing with some failures."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        
        (input_dir / "invoice1.pdf").write_bytes(b'pdf1')
        (input_dir / "invoice2.pdf").write_bytes(b'pdf2')
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        mock_process_pdf.side_effect = [
            {
                "filename": "invoice1.pdf",
                "status": "OK",
                "quality_score": 95.0,
                "output_path": str(output_dir / "invoice1.xlsx"),
                "error": None,
                "virtual_invoices": []
            },
            {
                "filename": "invoice2.pdf",
                "status": "FAILED",
                "quality_score": 0.0,
                "output_path": None,
                "error": "Processing error",
                "virtual_invoices": []
            }
        ]
        
        results = run_batch(input_dir, output_dir, fail_fast=False, verbose=False)
        
        assert results["total_files"] == 2
        assert results["processed"] == 1
        assert results["ok"] == 1
        assert results["failed"] == 1
        assert len(results["results"]) == 2
    
    @patch('src.batch.runner.process_pdf_isolated')
    def test_run_batch_fail_fast(self, mock_process_pdf, tmp_path):
        """Test batch processing with fail_fast=True."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        
        (input_dir / "invoice1.pdf").write_bytes(b'pdf1')
        (input_dir / "invoice2.pdf").write_bytes(b'pdf2')
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "filename": "invoice1.pdf",
                    "status": "FAILED",
                    "quality_score": 0.0,
                    "output_path": None,
                    "error": "Error",
                    "virtual_invoices": []
                }
            return {
                "filename": "invoice2.pdf",
                "status": "OK",
                "quality_score": 95.0,
                "output_path": str(output_dir / "invoice2.xlsx"),
                "error": None,
                "virtual_invoices": []
            }
        
        mock_process_pdf.side_effect = side_effect
        
        results = run_batch(input_dir, output_dir, fail_fast=True, verbose=False)
        
        # Should stop after first failure
        assert call_count == 1
        assert results["failed"] == 1


class TestBatchSummary:
    """Test batch summary Excel generation."""
    
    def test_create_batch_summary(self, tmp_path):
        """Test creating batch summary Excel."""
        batch_results = [
            {
                "filename": "invoice1.pdf",
                "status": "OK",
                "quality_score": 95.5,
                "output_path": "/path/to/invoice1.xlsx",
                "error": None
            },
            {
                "filename": "invoice2.pdf",
                "status": "PARTIAL",
                "quality_score": 80.0,
                "output_path": "/path/to/invoice2.xlsx",
                "error": None
            },
            {
                "filename": "invoice3.pdf",
                "status": "FAILED",
                "quality_score": 0.0,
                "output_path": None,
                "error": "Processing error"
            }
        ]
        
        excel_path = create_batch_summary(batch_results, tmp_path)
        
        assert excel_path.exists()
        assert excel_path.name == "batch_summary.xlsx"
        
        # Verify Excel content
        import pandas as pd
        df = pd.read_excel(excel_path, engine="openpyxl")
        
        assert len(df) == 3
        assert "Filnamn" in df.columns
        assert "Status" in df.columns
        assert "Quality Score" in df.columns
        assert "Output Path" in df.columns
        assert "Error" in df.columns
        
        # Check sorting (OK, PARTIAL, FAILED)
        assert df.iloc[0]["Status"] == "OK"
        assert df.iloc[1]["Status"] == "PARTIAL"
        assert df.iloc[2]["Status"] == "FAILED"

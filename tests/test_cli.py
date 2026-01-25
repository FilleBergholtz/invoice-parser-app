"""Unit tests for CLI interface."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from src.cli.main import process_invoice, process_batch


def _make_minimal_pdf(path: Path) -> None:
    """Minimal PDF som pdfplumber kan läsa (för process_invoice)."""
    import fitz
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(str(path))
    doc.close()


@pytest.fixture
def minimal_pdf_path(tmp_path):
    """En minimal PDF-fil för process_invoice."""
    p = tmp_path / "minimal.pdf"
    _make_minimal_pdf(p)
    return p


@pytest.fixture
def temp_output_dir(tmp_path):
    """Tillfällig output-katalog."""
    d = tmp_path / "output"
    d.mkdir()
    return d


@pytest.fixture
def temp_input_dir(tmp_path):
    """Tillfällig input-katalog med en minimal PDF."""
    d = tmp_path / "input"
    d.mkdir()
    p = d / "test.pdf"
    _make_minimal_pdf(p)
    return d


def test_process_invoice_returns_validation_result(minimal_pdf_path, temp_output_dir):
    """process_invoice() returnerar dict med 'status'; vid lyckad körning finns 'validation_result'."""
    result = process_invoice(str(minimal_pdf_path), str(temp_output_dir))
    assert isinstance(result, dict)
    assert "status" in result
    if result["status"] != "FAILED":
        assert "validation_result" in result


def _mock_virtual_result(status="OK", virtual_invoice_id="test__1"):
    """Hjälp: en mock virtual result för process_batch."""
    r = MagicMock()
    r.status = status
    r.virtual_invoice_id = virtual_invoice_id
    r.virtual_invoice_index = 1
    r.invoice_header = MagicMock()
    r.invoice_header.invoice_number = "INV-123"
    r.invoice_header.invoice_date = None
    r.invoice_header.total_amount = 100.0
    r.invoice_header.supplier_name = "Test"
    r.invoice_header.invoice_number_confidence = 0.95
    r.invoice_header.total_confidence = 0.90
    r.invoice_header.reference = None
    r.validation_result = MagicMock()
    r.validation_result.status = status
    r.validation_result.lines_sum = 100.0
    r.validation_result.diff = 0.0
    r.validation_result.hard_gate_passed = (status == "OK")
    line = SimpleNamespace(rows=[], description="X", quantity=1.0, unit="st", unit_price=100.0, discount=None, total_amount=100.0, vat_rate=None, line_number=1, segment=None)
    r.invoice_lines = [line]
    r.line_count = 1
    r.ai_request = None
    r.extraction_source = None
    r.extraction_detail = None
    r.error = None
    return r


@patch("src.cli.main.process_pdf")
def test_process_batch_collects_invoice_results(mock_process_pdf, temp_input_dir, temp_output_dir):
    """process_batch() samlar resultat per faktura; processed_files och total_files i summary."""
    mock_process_pdf.return_value = [_mock_virtual_result(status="OK")]
    process_batch(str(temp_input_dir), str(temp_output_dir))
    summary_path = temp_output_dir / "run_summary.json"
    assert summary_path.exists()
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_files"] == 1
    assert data["processed_files"] == 1


@patch("src.cli.main.create_review_package")
@patch("src.cli.main.create_review_report")
@patch("src.cli.main.process_pdf")
def test_process_batch_creates_review_reports(mock_process_pdf, mock_create_review, mock_create_package, temp_input_dir, temp_output_dir):
    """Vid REVIEW anropas create_review_report och summary får review_count."""
    mock_process_pdf.return_value = [_mock_virtual_result(status="REVIEW")]
    review_folder = temp_output_dir / "review" / "test__1"
    review_folder.mkdir(parents=True)
    (review_folder / "metadata.json").write_text("{}", encoding="utf-8")
    mock_create_review.return_value = review_folder
    process_batch(str(temp_input_dir), str(temp_output_dir))
    assert mock_create_review.called
    with open(temp_output_dir / "run_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("review_count", 0) >= 1


@patch("src.cli.main.process_pdf")
def test_process_batch_excel_export_includes_validation(mock_process_pdf, temp_input_dir, temp_output_dir):
    """Excel-export innehåller valideringskolumner (t.ex. Status, Radsumma, Totalsumma-konfidens)."""
    mock_process_pdf.return_value = [_mock_virtual_result(status="OK")]
    process_batch(str(temp_input_dir), str(temp_output_dir))
    with open(temp_output_dir / "run_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    excel_path = data.get("excel_path")
    assert excel_path and Path(excel_path).exists()
    import openpyxl
    wb = openpyxl.load_workbook(excel_path)
    ws = wb["Invoices"]
    headers = [c.value for c in ws[1]]
    assert "Status" in headers
    assert "Radsumma" in headers
    assert "Totalsumma-konfidens" in headers


@patch("src.cli.main.process_pdf")
def test_process_batch_summary_includes_validation_stats(mock_process_pdf, temp_input_dir, temp_output_dir):
    """run_summary innehåller ok_count, partial_count, review_count."""
    mock_process_pdf.return_value = [_mock_virtual_result(status="OK")]
    process_batch(str(temp_input_dir), str(temp_output_dir))
    with open(temp_output_dir / "run_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "ok_count" in data
    assert "partial_count" in data
    assert "review_count" in data
    assert "failed_count" in data
    assert "processed_files" in data
    assert data["status"] == "COMPLETED"

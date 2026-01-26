"""Unit tests for AI policy gating."""

from src.ai.fallback import evaluate_ai_policy
from src.models.validation_result import ValidationResult
from src.pipeline.ocr_routing import evaluate_edi_signals


def _policy_config():
    return {
        "allow_ai_for_edi": False,
        "force_review_on_edi_fail": True,
        "min_edi_signals": 2,
        "min_text_quality": 0.5,
        "edi_anchor_rules": {
            "required": [r"Faktura\s"],
            "extra": [r"Sida\s*\d+\s*/\s*\d+"],
        },
        "edi_table_patterns": [r"\bArtikel\b", r"\bAntal\b"],
    }


def _ok_validation() -> ValidationResult:
    return ValidationResult(
        status="OK",
        lines_sum=100.0,
        diff=0.0,
        tolerance=1.0,
        hard_gate_passed=True,
        invoice_number_confidence=0.98,
        total_confidence=0.97,
        errors=[],
        warnings=[],
    )


def test_edi_like_validation_ok_blocks_ai():
    text = "Faktura 2025-01-01\nSida 1/1\nArtikel A 1 st 100 SEK"
    edi_signals = evaluate_edi_signals(
        text=text,
        text_layer_used=True,
        text_quality=0.8,
        anchor_rules=_policy_config()["edi_anchor_rules"],
        table_patterns=_policy_config()["edi_table_patterns"],
        min_signals=2,
        min_text_quality=0.5,
    )
    decision = evaluate_ai_policy(
        extraction_source="pdfplumber",
        text_quality=0.8,
        validation_result=_ok_validation(),
        edi_signals=edi_signals,
        policy_config=_policy_config(),
        fallback_attempted=False,
        fallback_passed=None,
    )
    assert decision["allow_ai"] is False
    assert "edi_like" in decision["reason_flags"]
    assert "edi_blocked_validation_ok" in decision["reason_flags"]


def test_edi_like_fallback_passed_blocks_ai():
    text = "Faktura 2025-01-01\nSida 1/1\nArtikel A 1 st 100 SEK"
    edi_signals = evaluate_edi_signals(
        text=text,
        text_layer_used=True,
        text_quality=0.9,
        anchor_rules=_policy_config()["edi_anchor_rules"],
        table_patterns=_policy_config()["edi_table_patterns"],
        min_signals=2,
        min_text_quality=0.5,
    )
    decision = evaluate_ai_policy(
        extraction_source="pdfplumber",
        text_quality=0.9,
        validation_result=_ok_validation(),
        edi_signals=edi_signals,
        policy_config=_policy_config(),
        fallback_attempted=True,
        fallback_passed=True,
    )
    assert decision["allow_ai"] is False
    assert "fallback_passed" in decision["reason_flags"]


def test_non_edi_missing_patterns_allows_ai():
    text = "Random text without anchors or table patterns"
    edi_signals = evaluate_edi_signals(
        text=text,
        text_layer_used=False,
        text_quality=0.2,
        anchor_rules=_policy_config()["edi_anchor_rules"],
        table_patterns=_policy_config()["edi_table_patterns"],
        min_signals=2,
        min_text_quality=0.5,
    )
    validation = ValidationResult(
        status="REVIEW",
        lines_sum=0.0,
        diff=None,
        tolerance=1.0,
        hard_gate_passed=False,
        invoice_number_confidence=0.4,
        total_confidence=0.2,
        errors=["no lines"],
        warnings=[],
    )
    decision = evaluate_ai_policy(
        extraction_source="ocr",
        text_quality=0.2,
        validation_result=validation,
        edi_signals=edi_signals,
        policy_config=_policy_config(),
        fallback_attempted=True,
        fallback_passed=False,
    )
    assert decision["allow_ai"] is True


def test_compare_path_edi_blocks_ai_and_records_policy(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from src.cli import main as main_module

    page = SimpleNamespace(page_number=1)
    doc = SimpleNamespace(
        filename="dummy.pdf",
        filepath=str(tmp_path / "dummy.pdf"),
        pages=[page],
    )

    header_row = SimpleNamespace(text="Faktura 2025-01-01", tokens=[], y=0, x_min=0, x_max=1, page=page)
    footer_row = SimpleNamespace(text="Sida 1/1 Artikel A 1 st 100 SEK", tokens=[], y=100, x_min=0, x_max=1, page=page)
    header_segment = SimpleNamespace(segment_type="header", rows=[header_row], y_min=0, y_max=10, page=page)
    footer_segment = SimpleNamespace(segment_type="footer", rows=[footer_row], y_min=100, y_max=110, page=page)

    monkeypatch.setattr(main_module, "render_page_to_image", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module, "extract_tokens_from_page", lambda *args, **kwargs: [SimpleNamespace(text="token")])
    monkeypatch.setattr(main_module, "group_tokens_to_rows", lambda *args, **kwargs: [])
    monkeypatch.setattr(main_module, "identify_segments", lambda *args, **kwargs: [header_segment, footer_segment])
    monkeypatch.setattr(main_module, "extract_invoice_lines", lambda *args, **kwargs: [])
    monkeypatch.setattr(main_module, "extract_header_fields", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module, "score_text_quality", lambda *args, **kwargs: 0.8)

    pdf_stub = SimpleNamespace(pages=[SimpleNamespace()], close=lambda: None)
    monkeypatch.setattr(main_module.pdfplumber, "open", lambda *args, **kwargs: pdf_stub)

    calls = []

    def _fake_extract_total_amount(*args, **kwargs):
        calls.append(kwargs.get("allow_ai", True))
        invoice_header = args[2]
        invoice_header.total_amount = 100.0
        invoice_header.total_confidence = 0.2

    monkeypatch.setattr(main_module, "extract_total_amount", _fake_extract_total_amount)
    monkeypatch.setattr(main_module, "run_deterministic_fallback", lambda extract_func, **kwargs: extract_func())

    from src.models.validation_result import ValidationResult

    def _fake_validate_invoice(invoice_header, line_items):
        return ValidationResult(
            status="REVIEW",
            lines_sum=100.0,
            diff=5.0,
            tolerance=1.0,
            hard_gate_passed=False,
            invoice_number_confidence=invoice_header.invoice_number_confidence,
            total_confidence=invoice_header.total_confidence,
            errors=[],
            warnings=[],
        )

    monkeypatch.setattr(main_module, "validate_invoice", _fake_validate_invoice)
    monkeypatch.setattr("src.pipeline.retry_extraction.extract_with_retry", lambda extract_func, **kwargs: extract_func())

    result = main_module.process_virtual_invoice(
        doc,
        page_start=1,
        page_end=1,
        virtual_invoice_index=1,
        extraction_path="pdfplumber",
        verbose=False,
    )

    assert calls
    assert all(call is False for call in calls)
    assert result.extraction_detail is not None
    assert result.extraction_detail["ai_policy"]["allow_ai"] is False
    assert "edi_like" in result.extraction_detail["ai_policy"]["reason_flags"]

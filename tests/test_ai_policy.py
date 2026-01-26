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

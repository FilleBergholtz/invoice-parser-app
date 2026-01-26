"""Unit tests for OCR routing decisions."""

from src.pipeline.ocr_routing import evaluate_text_layer


def test_evaluate_text_layer_requires_required_and_extra_anchors():
    routing = {
        "min_text_chars": 20,
        "required_anchors": [r"Faktura\s"],
        "extra_anchors": [r"Sida\s*\d+\s*/\s*\d+"],
        "min_word_tokens": 5,
        "min_text_quality": 0.5,
        "allow_quality_override": False,
    }
    text = "Faktura\t ABC-123\nSida 1/2\nTotalt 100 SEK\nExtra ord här"
    decision = evaluate_text_layer(text, [], routing)
    assert decision["use_text_layer"] is True
    assert decision["required_anchor_hits"]
    assert decision["extra_anchor_hits"]


def test_evaluate_text_layer_blocks_missing_extra_anchor():
    routing = {
        "min_text_chars": 10,
        "required_anchors": [r"Faktura\s"],
        "extra_anchors": [r"Sida\s*\d+\s*/\s*\d+"],
        "min_word_tokens": 5,
        "min_text_quality": 0.5,
        "allow_quality_override": False,
    }
    text = "Faktura 2025-01-01\nTotalt 100 SEK"
    decision = evaluate_text_layer(text, [], routing)
    assert decision["use_text_layer"] is False
    assert "extra_anchor_missing" in decision["reason_flags"]


def test_evaluate_text_layer_quality_override():
    routing = {
        "min_text_chars": 10,
        "required_anchors": [r"Faktura\s"],
        "extra_anchors": [r"Sida\s*\d+\s*/\s*\d+"],
        "min_word_tokens": 8,
        "min_text_quality": 0.4,
        "allow_quality_override": True,
    }
    text = "Detta är en fakturarad med många ord och rimlig text kvalitet"
    decision = evaluate_text_layer(text, [], routing)
    assert decision["use_text_layer"] is True
    assert "quality_override" in decision["reason_flags"]

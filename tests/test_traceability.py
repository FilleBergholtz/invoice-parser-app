"""Unit tests for Traceability model."""

import pytest
from src.models.traceability import Traceability


def test_traceability_creation():
    """Test Traceability creation with evidence dict."""
    evidence = {
        "page_number": 1,
        "bbox": [100.0, 50.0, 90.0, 12.0],
        "row_index": 0,
        "text_excerpt": "Fakturanummer: INV-2024-001",
        "tokens": [
            {"text": "Fakturanummer", "bbox": [100.0, 50.0, 80.0, 12.0], "conf": 0.98},
            {"text": "INV-2024-001", "bbox": [190.0, 50.0, 90.0, 12.0], "conf": 0.95}
        ]
    }
    
    trace = Traceability(
        field="invoice_no",
        value="INV-2024-001",
        confidence=0.95,
        evidence=evidence
    )
    
    assert trace.field == "invoice_no"
    assert trace.value == "INV-2024-001"
    assert trace.confidence == 0.95
    assert trace.evidence == evidence


def test_traceability_json_serialization():
    """Test Traceability JSON serialization (to_dict method)."""
    evidence = {
        "page_number": 1,
        "bbox": [100.0, 50.0, 90.0, 12.0],
        "row_index": 0,
        "text_excerpt": "Total: 1000.00",
        "tokens": []
    }
    
    trace = Traceability(
        field="total",
        value="1000.00",
        confidence=0.98,
        evidence=evidence
    )
    
    dict_repr = trace.to_dict()
    
    assert dict_repr["field"] == "total"
    assert dict_repr["value"] == "1000.00"
    assert dict_repr["confidence"] == 0.98
    assert dict_repr["evidence"] == evidence


def test_traceability_from_dict():
    """Test Traceability creation from dict (from_dict method)."""
    data = {
        "field": "invoice_no",
        "value": "INV-001",
        "confidence": 0.95,
        "evidence": {
            "page_number": 1,
            "bbox": [100.0, 50.0, 90.0, 12.0],
            "row_index": 0,
            "text_excerpt": "Test",
            "tokens": []
        }
    }
    
    trace = Traceability.from_dict(data)
    
    assert trace.field == "invoice_no"
    assert trace.value == "INV-001"
    assert trace.confidence == 0.95


def test_traceability_confidence_range_validation():
    """Test that confidence must be between 0.0 and 1.0."""
    evidence = {
        "page_number": 1,
        "bbox": [100.0, 50.0, 90.0, 12.0],
        "row_index": 0,
        "text_excerpt": "Test",
        "tokens": []
    }
    
    # Valid confidence
    trace1 = Traceability(field="invoice_no", value="INV", confidence=0.5, evidence=evidence)
    assert trace1.confidence == 0.5
    
    # Invalid confidence (> 1.0)
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        Traceability(field="invoice_no", value="INV", confidence=1.5, evidence=evidence)
    
    # Invalid confidence (< 0.0)
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        Traceability(field="invoice_no", value="INV", confidence=-0.1, evidence=evidence)


def test_traceability_field_validation():
    """Test that field must be 'invoice_no' or 'total'."""
    evidence = {
        "page_number": 1,
        "bbox": [100.0, 50.0, 90.0, 12.0],
        "row_index": 0,
        "text_excerpt": "Test",
        "tokens": []
    }
    
    # Valid fields
    trace1 = Traceability(field="invoice_no", value="INV", confidence=0.95, evidence=evidence)
    trace2 = Traceability(field="total", value="100", confidence=0.95, evidence=evidence)
    
    # Invalid field
    with pytest.raises(ValueError, match="field must be 'invoice_no' or 'total'"):
        Traceability(field="invalid", value="test", confidence=0.95, evidence=evidence)


def test_traceability_evidence_structure_validation():
    """Test that evidence must contain required keys."""
    # Missing required key
    incomplete_evidence = {
        "page_number": 1,
        "bbox": [100.0, 50.0, 90.0, 12.0],
        # Missing row_index, text_excerpt, tokens
    }
    
    with pytest.raises(ValueError, match="evidence must contain"):
        Traceability(
            field="invoice_no",
            value="INV",
            confidence=0.95,
            evidence=incomplete_evidence
        )


def test_traceability_bbox_validation():
    """Test that bbox must be list of 4 floats."""
    evidence_invalid_bbox = {
        "page_number": 1,
        "bbox": [100.0, 50.0],  # Only 2 values, need 4
        "row_index": 0,
        "text_excerpt": "Test",
        "tokens": []
    }
    
    with pytest.raises(ValueError, match="evidence.bbox must be list of 4 floats"):
        Traceability(
            field="invoice_no",
            value="INV",
            confidence=0.95,
            evidence=evidence_invalid_bbox
        )

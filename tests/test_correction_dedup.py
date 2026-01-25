"""Tests for correction storage: one best correction per invoice_id by confidence."""

import json
import pytest
from pathlib import Path

from src.learning.correction_collector import CorrectionCollector
from src.learning.database import LearningDatabase


def _correction(invoice_id: str, corrected_total: float, corrected_confidence: float) -> dict:
    return {
        "invoice_id": invoice_id,
        "supplier_name": "Test AB",
        "original_total": 100.0,
        "original_confidence": 0.5,
        "corrected_total": corrected_total,
        "corrected_confidence": corrected_confidence,
        "raw_confidence": None,
        "candidate_index": 0,
        "timestamp": "2026-01-01T12:00:00",
        "correction_type": "total_amount",
    }


class TestCorrectionCollectorDedup:
    """Corrections JSON: at most one entry per invoice_id, keep highest confidence."""

    def test_save_then_higher_replaces(self, tmp_path):
        path = tmp_path / "corrections.json"
        c = CorrectionCollector(storage_path=path)
        c.save_correction(_correction("INV-1", 1000.0, 0.7))
        c.save_correction(_correction("INV-1", 1000.0, 0.95))
        all_ = c.get_corrections()
        assert len(all_) == 1
        assert all_[0]["invoice_id"] == "INV-1"
        assert all_[0]["corrected_confidence"] == 0.95

    def test_save_then_lower_ignored(self, tmp_path):
        path = tmp_path / "corrections.json"
        c = CorrectionCollector(storage_path=path)
        c.save_correction(_correction("INV-1", 1000.0, 0.95))
        c.save_correction(_correction("INV-1", 999.0, 0.7))
        all_ = c.get_corrections()
        assert len(all_) == 1
        assert all_[0]["corrected_confidence"] == 0.95
        assert all_[0]["corrected_total"] == 1000.0

    def test_same_confidence_keeps_existing(self, tmp_path):
        """Vid lika confidence behålls befintlig post (ingen dubblett, ingen ersättning)."""
        path = tmp_path / "corrections.json"
        c = CorrectionCollector(storage_path=path)
        c.save_correction(_correction("INV-1", 1000.0, 0.9))
        c.save_correction(_correction("INV-1", 1001.0, 0.9))
        all_ = c.get_corrections()
        assert len(all_) == 1
        assert all_[0]["corrected_total"] == 1000.0
        assert all_[0]["corrected_confidence"] == 0.9

    def test_different_invoice_ids_both_kept(self, tmp_path):
        path = tmp_path / "corrections.json"
        c = CorrectionCollector(storage_path=path)
        c.save_correction(_correction("INV-1", 1000.0, 0.8))
        c.save_correction(_correction("INV-2", 2000.0, 0.9))
        all_ = c.get_corrections()
        assert len(all_) == 2
        by_id = {x["invoice_id"]: x for x in all_}
        assert by_id["INV-1"]["corrected_confidence"] == 0.8
        assert by_id["INV-2"]["corrected_confidence"] == 0.9


class TestLearningDatabaseDedup:
    """Learning DB: add_correction upserts by invoice_id, keeps highest confidence."""

    def test_add_then_higher_updates(self, tmp_path):
        db_path = tmp_path / "learning.db"
        db = LearningDatabase(db_path=db_path)
        db.add_correction(_correction("INV-1", 1000.0, 0.7))
        db.add_correction(_correction("INV-1", 1000.0, 0.95))
        rows = db.get_corrections()
        inv1 = [r for r in rows if r["invoice_id"] == "INV-1"]
        assert len(inv1) == 1
        assert inv1[0]["corrected_confidence"] == 0.95

    def test_add_then_lower_keeps_existing(self, tmp_path):
        db_path = tmp_path / "learning.db"
        db = LearningDatabase(db_path=db_path)
        db.add_correction(_correction("INV-1", 1000.0, 0.95))
        db.add_correction(_correction("INV-1", 999.0, 0.7))
        rows = db.get_corrections()
        inv1 = [r for r in rows if r["invoice_id"] == "INV-1"]
        assert len(inv1) == 1
        assert inv1[0]["corrected_confidence"] == 0.95
        assert inv1[0]["corrected_total"] == 1000.0

    def test_different_invoice_ids_both_kept(self, tmp_path):
        db_path = tmp_path / "learning.db"
        db = LearningDatabase(db_path=db_path)
        db.add_correction(_correction("INV-1", 1000.0, 0.8))
        db.add_correction(_correction("INV-2", 2000.0, 0.9))
        rows = db.get_corrections()
        by_id = {r["invoice_id"]: r for r in rows}
        assert len(by_id) == 2
        assert by_id["INV-1"]["corrected_confidence"] == 0.8
        assert by_id["INV-2"]["corrected_confidence"] == 0.9

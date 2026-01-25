"""SQLite learning database for storing corrections and patterns."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LearningDatabase:
    """Manages SQLite learning database for corrections and patterns.
    
    Stores user corrections and extracted patterns for learning system.
    Supports supplier-specific queries and pattern matching.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize learning database.
        
        Args:
            db_path: Path to SQLite database file. Defaults to data/learning.db
        """
        if db_path is None:
            # Default to data/learning.db in project root
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "learning.db"
        
        self.db_path = Path(db_path)
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection.
        
        Returns:
            SQLite connection
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def _init_schema(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create corrections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id TEXT NOT NULL,
                    supplier_name TEXT NOT NULL,
                    original_total REAL,
                    original_confidence REAL,
                    corrected_total REAL NOT NULL,
                    corrected_confidence REAL,
                    raw_confidence REAL,
                    candidate_index INTEGER,
                    timestamp TEXT NOT NULL,
                    correction_type TEXT DEFAULT 'total_amount'
                )
            """)
            
            # Create patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_name TEXT NOT NULL,
                    layout_hash TEXT,
                    position_x REAL,
                    position_y REAL,
                    position_width REAL,
                    position_height REAL,
                    correct_total REAL NOT NULL,
                    confidence_boost REAL DEFAULT 0.1,
                    usage_count INTEGER DEFAULT 1,
                    last_used TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_corrections_supplier 
                ON corrections(supplier_name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_supplier 
                ON patterns(supplier_name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_layout_hash 
                ON patterns(layout_hash)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_corrections_invoice_id 
                ON corrections(invoice_id)
            """)
            
            conn.commit()
            logger.debug(f"Database schema initialized: {self.db_path}")
    
    def import_corrections_from_json(self, json_path: Path) -> int:
        """Import corrections from JSON file.
        
        Args:
            json_path: Path to corrections JSON file
            
        Returns:
            Number of corrections imported
            
        Raises:
            FileNotFoundError: If JSON file doesn't exist
            ValueError: If JSON format is invalid
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"Corrections file not found: {json_path}")
        
        # Load corrections from JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                corrections = json.load(f)
            
            if not isinstance(corrections, list):
                raise ValueError(f"JSON file must contain a list, got {type(corrections)}")
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in corrections file: {e}") from e
        
        # Import corrections
        imported_count = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for correction in corrections:
                try:
                    cursor.execute("""
                        INSERT INTO corrections (
                            invoice_id, supplier_name, original_total,
                            original_confidence, corrected_total, corrected_confidence,
                            raw_confidence, candidate_index, timestamp, correction_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        correction.get('invoice_id', ''),
                        correction.get('supplier_name', 'Unknown'),
                        correction.get('original_total'),
                        correction.get('original_confidence'),
                        correction.get('corrected_total'),
                        correction.get('corrected_confidence'),
                        correction.get('raw_confidence'),
                        correction.get('candidate_index'),
                        correction.get('timestamp', datetime.now().isoformat()),
                        correction.get('correction_type', 'total_amount')
                    ))
                    imported_count += 1
                except Exception as e:
                    logger.warning(f"Failed to import correction {correction.get('invoice_id')}: {e}")
                    continue
            
            conn.commit()
        
        logger.info(f"Imported {imported_count} corrections from {json_path}")
        return imported_count
    
    def add_correction(self, correction: Dict[str, Any]) -> None:
        """Insert or replace a single correction; per invoice_id only the
        row with highest corrected_confidence is kept (no duplicates).
        
        Same format as produced by correction_collector.save_correction.
        Used when saving from GUI so corrections go to both JSON and DB.
        
        Args:
            correction: Dict with invoice_id, supplier_name, original_total,
                corrected_total, corrected_confidence, timestamp, correction_type, etc.
                
        Raises:
            ValueError: If required fields are missing
        """
        required = ('invoice_id', 'corrected_total', 'timestamp')
        for k in required:
            if k not in correction:
                raise ValueError(f"Missing required field: {k}")
        invoice_id = correction.get('invoice_id', '')
        new_conf = float(correction.get('corrected_confidence') or 0.0)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, corrected_confidence FROM corrections WHERE invoice_id = ?",
                (invoice_id,),
            )
            row = cursor.fetchone()
            if row is not None:
                old_conf = float(row['corrected_confidence'] or 0.0)
                if new_conf <= old_conf:
                    logger.debug(f"Kept existing correction for invoice {invoice_id} (conf {old_conf} >= {new_conf})")
                    return
                cursor.execute("""
                    UPDATE corrections SET
                        supplier_name = ?, original_total = ?, original_confidence = ?,
                        corrected_total = ?, corrected_confidence = ?, raw_confidence = ?,
                        candidate_index = ?, timestamp = ?, correction_type = ?
                    WHERE invoice_id = ?
                """, (
                    correction.get('supplier_name', 'Unknown'),
                    correction.get('original_total'),
                    correction.get('original_confidence'),
                    correction.get('corrected_total'),
                    correction.get('corrected_confidence'),
                    correction.get('raw_confidence'),
                    correction.get('candidate_index'),
                    correction.get('timestamp', datetime.now().isoformat()),
                    correction.get('correction_type', 'total_amount'),
                    invoice_id,
                ))
                logger.info(f"Updated correction for invoice {invoice_id} (higher confidence {new_conf})")
            else:
                cursor.execute("""
                    INSERT INTO corrections (
                        invoice_id, supplier_name, original_total,
                        original_confidence, corrected_total, corrected_confidence,
                        raw_confidence, candidate_index, timestamp, correction_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id,
                    correction.get('supplier_name', 'Unknown'),
                    correction.get('original_total'),
                    correction.get('original_confidence'),
                    correction.get('corrected_total'),
                    correction.get('corrected_confidence'),
                    correction.get('raw_confidence'),
                    correction.get('candidate_index'),
                    correction.get('timestamp', datetime.now().isoformat()),
                    correction.get('correction_type', 'total_amount')
                ))
                logger.info(f"Added correction for invoice {invoice_id} to learning DB")
            conn.commit()
    
    def get_corrections(self, supplier: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get corrections, optionally filtered by supplier.
        
        Args:
            supplier: Optional supplier name to filter by
            
        Returns:
            List of correction dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if supplier:
                cursor.execute("""
                    SELECT * FROM corrections 
                    WHERE supplier_name = ?
                    ORDER BY timestamp DESC
                """, (supplier,))
            else:
                cursor.execute("""
                    SELECT * FROM corrections 
                    ORDER BY timestamp DESC
                """)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def save_pattern(self, pattern: Dict[str, Any]) -> None:
        """Save extracted pattern.
        
        Args:
            pattern: Pattern dict with supplier_name, layout_hash, position, correct_total, etc.
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ['supplier_name', 'correct_total']
        for field in required_fields:
            if field not in pattern:
                raise ValueError(f"Missing required field: {field}")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO patterns (
                    supplier_name, layout_hash,
                    position_x, position_y, position_width, position_height,
                    correct_total, confidence_boost, usage_count,
                    last_used, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.get('supplier_name'),
                pattern.get('layout_hash'),
                pattern.get('position_x'),
                pattern.get('position_y'),
                pattern.get('position_width'),
                pattern.get('position_height'),
                pattern.get('correct_total'),
                pattern.get('confidence_boost', 0.1),
                pattern.get('usage_count', 1),
                pattern.get('last_used', datetime.now().isoformat()),
                pattern.get('created_at', datetime.now().isoformat())
            ))
            
            conn.commit()
            logger.debug(f"Saved pattern for supplier {pattern.get('supplier_name')}")
    
    def get_patterns(self, supplier: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get patterns, optionally filtered by supplier.
        
        Args:
            supplier: Optional supplier name to filter by
            
        Returns:
            List of pattern dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if supplier:
                cursor.execute("""
                    SELECT * FROM patterns 
                    WHERE supplier_name = ?
                    ORDER BY usage_count DESC, last_used DESC
                """, (supplier,))
            else:
                cursor.execute("""
                    SELECT * FROM patterns 
                    ORDER BY usage_count DESC, last_used DESC
                """)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_pattern_usage(self, pattern_id: int) -> None:
        """Update pattern usage count and last_used timestamp.
        
        Args:
            pattern_id: Pattern ID to update
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE patterns 
                SET usage_count = usage_count + 1,
                    last_used = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), pattern_id))
            
            conn.commit()
    
    def delete_pattern(self, pattern_id: int) -> None:
        """Delete pattern by ID.
        
        Args:
            pattern_id: Pattern ID to delete
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
            conn.commit()
            
            logger.debug(f"Deleted pattern {pattern_id}")
    
    def update_pattern(self, pattern_id: int, updates: Dict[str, Any]) -> None:
        """Update pattern fields.
        
        Args:
            pattern_id: Pattern ID to update
            updates: Dict of fields to update
        """
        if not updates:
            return
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build UPDATE query dynamically
            set_clauses = []
            values = []
            
            allowed_fields = [
                'usage_count', 'last_used', 'confidence_boost',
                'position_x', 'position_y', 'position_width', 'position_height'
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    set_clauses.append(f"{field} = ?")
                    values.append(value)
            
            if not set_clauses:
                return
            
            values.append(pattern_id)
            
            query = f"UPDATE patterns SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            
            logger.debug(f"Updated pattern {pattern_id}")

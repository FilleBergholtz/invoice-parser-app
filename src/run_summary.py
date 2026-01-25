"""Run summary model and serialization."""

import json
import math
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively replace NaN/Inf floats so JSON round-trip works (json.load rejects them)."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return 0.0
    return obj

@dataclass
class RunSummary:
    """Summary of a processing run."""
    run_id: str
    input_path: str
    output_dir: str
    started_at: str
    finished_at: Optional[str] = None
    status: str = "RUNNING"  # RUNNING, COMPLETED, FAILED
    
    # Statistics
    total_files: int = 0
    processed_files: int = 0
    ok_count: int = 0
    partial_count: int = 0
    review_count: int = 0
    failed_count: int = 0
    
    # Paths
    excel_path: Optional[str] = None
    errors_path: Optional[str] = None
    artifacts_dir: Optional[str] = None
    
    # Details
    errors: List[Dict[str, Any]] = field(default_factory=list)
    durations: Dict[str, float] = field(default_factory=dict)  # Stage durations
    quality_scores: List[Dict[str, Any]] = field(default_factory=list)  # Quality scores per invoice
    profile_name: Optional[str] = None  # Configuration profile used
    validation: Optional[Dict[str, Any]] = None  # Candidates + traceability for GUI (single-PDF REVIEW)
    
    @classmethod
    def create(cls, input_path: str, output_dir: str) -> 'RunSummary':
        """Create a new run summary."""
        return cls(
            run_id=str(uuid.uuid4()),
            input_path=str(input_path),
            output_dir=str(output_dir),
            started_at=datetime.now().isoformat()
        )
        
    def complete(self, status: str = "COMPLETED"):
        """Mark run as completed."""
        self.status = status
        self.finished_at = datetime.now().isoformat()
        
    def save(self, path: Path):
        """Save summary to JSON file."""
        data = _sanitize_for_json(asdict(self))
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

"""Run summary model and serialization."""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

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
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

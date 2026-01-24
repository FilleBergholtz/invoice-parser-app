"""Artifact manifest model for deterministic debug artifacts."""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class ArtifactEntry:
    """Entry for a single artifact file."""
    filename: str
    artifact_type: str  # tokens, rows, segments, ai, excel, debug, summary
    pipeline_stage: Optional[str] = None  # e.g., "tokenization", "row_grouping", "ai_enrichment"
    relative_path: str = ""  # Relative to artifacts root
    file_size: int = 0
    checksum: str = ""  # SHA256 hash
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ArtifactManifest:
    """Manifest of all artifacts for a processing run."""
    manifest_version: str = "1.0"
    run_id: str = ""
    created_at: str = ""
    artifacts: List[ArtifactEntry] = field(default_factory=list)
    
    def add_artifact(
        self,
        filename: str,
        artifact_type: str,
        relative_path: str,
        file_size: int,
        checksum: str,
        pipeline_stage: Optional[str] = None,
        created_at: Optional[str] = None
    ):
        """Add an artifact entry."""
        entry = ArtifactEntry(
            filename=filename,
            artifact_type=artifact_type,
            pipeline_stage=pipeline_stage,
            relative_path=relative_path,
            file_size=file_size,
            checksum=checksum,
            created_at=created_at or datetime.now().isoformat()
        )
        self.artifacts.append(entry)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "manifest_version": self.manifest_version,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "artifacts": [entry.to_dict() for entry in self.artifacts]
        }
    
    def save(self, path: Path):
        """Save manifest to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: Path) -> 'ArtifactManifest':
        """Load manifest from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        manifest = cls(
            manifest_version=data.get('manifest_version', '1.0'),
            run_id=data.get('run_id', ''),
            created_at=data.get('created_at', ''),
            artifacts=[]
        )
        
        for artifact_data in data.get('artifacts', []):
            entry = ArtifactEntry(
                filename=artifact_data['filename'],
                artifact_type=artifact_data['artifact_type'],
                pipeline_stage=artifact_data.get('pipeline_stage'),
                relative_path=artifact_data.get('relative_path', ''),
                file_size=artifact_data.get('file_size', 0),
                checksum=artifact_data.get('checksum', ''),
                created_at=artifact_data.get('created_at')
            )
            manifest.artifacts.append(entry)
        
        return manifest


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Hexadecimal SHA256 hash string
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

"""Index artifacts in a directory and create manifest."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .artifact_manifest import ArtifactManifest, calculate_file_hash


def determine_artifact_type(filename: str, relative_path: str) -> tuple[str, Optional[str]]:
    """Determine artifact type and pipeline stage from filename/path.
    
    Args:
        filename: Name of the file
        relative_path: Relative path from artifacts root
        
    Returns:
        Tuple of (artifact_type, pipeline_stage)
    """
    filename_lower = filename.lower()
    path_lower = relative_path.lower()
    
    # AI artifacts
    if filename_lower.startswith('ai_'):
        if 'request' in filename_lower:
            return ('ai', 'ai_enrichment')
        elif 'response' in filename_lower:
            return ('ai', 'ai_enrichment')
        elif 'diff' in filename_lower:
            return ('ai', 'ai_enrichment')
        elif 'error' in filename_lower:
            return ('ai', 'ai_enrichment')
        return ('ai', 'ai_enrichment')
    
    # Summary files
    if filename_lower == 'run_summary.json':
        return ('summary', None)
    
    # Excel files
    if filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls'):
        return ('excel', 'export')
    
    # Review reports
    if 'review' in path_lower or 'review' in filename_lower:
        return ('debug', 'validation')
    
    # Check if in subdirectory that might indicate type
    if 'tokens' in path_lower:
        return ('tokens', 'tokenization')
    elif 'rows' in path_lower:
        return ('rows', 'row_grouping')
    elif 'segments' in path_lower:
        return ('segments', 'segment_identification')
    
    # Default to debug for unknown types
    return ('debug', None)


def index_artifacts(
    artifacts_dir: Path,
    run_id: str,
    exclude_patterns: Optional[list[str]] = None
) -> ArtifactManifest:
    """Index all artifacts in a directory and create manifest.
    
    Args:
        artifacts_dir: Root directory containing artifacts
        run_id: Run ID for this processing run
        exclude_patterns: Optional list of filename patterns to exclude
        
    Returns:
        ArtifactManifest with all indexed artifacts
    """
    if exclude_patterns is None:
        exclude_patterns = ['.git', '__pycache__', '.pytest_cache']
    
    manifest = ArtifactManifest(
        run_id=run_id,
        created_at=datetime.now().isoformat()
    )
    
    # Normalize artifacts_dir to absolute path
    artifacts_dir = artifacts_dir.resolve()
    
    # Walk through all files in artifacts directory
    for file_path in artifacts_dir.rglob('*'):
        # Skip directories
        if file_path.is_dir():
            continue
        
        # Skip excluded patterns
        if any(pattern in str(file_path) for pattern in exclude_patterns):
            continue
        
        # Calculate relative path from artifacts root
        try:
            relative_path = str(file_path.relative_to(artifacts_dir))
        except ValueError:
            # File is outside artifacts_dir, skip
            continue
        
        filename = file_path.name
        
        # Determine artifact type and pipeline stage
        artifact_type, pipeline_stage = determine_artifact_type(filename, relative_path)
        
        # Calculate file size and checksum
        try:
            file_size = file_path.stat().st_size
            checksum = calculate_file_hash(file_path)
        except (OSError, IOError) as e:
            # Skip files that can't be read
            continue
        
        # Add to manifest
        manifest.add_artifact(
            filename=filename,
            artifact_type=artifact_type,
            relative_path=relative_path,
            file_size=file_size,
            checksum=checksum,
            pipeline_stage=pipeline_stage
        )
    
    return manifest


def create_manifest_for_run(
    artifacts_dir: Path,
    run_id: str,
    output_dir: Optional[Path] = None
) -> ArtifactManifest:
    """Create and save artifact manifest for a processing run.
    
    Args:
        artifacts_dir: Root directory containing artifacts
        run_id: Run ID for this processing run
        output_dir: Optional output directory to also index (for run_summary.json, Excel files)
        
    Returns:
        Created ArtifactManifest
    """
    # Index all artifacts in artifacts directory
    manifest = index_artifacts(artifacts_dir, run_id)
    
    # Also index output directory if provided (for run_summary.json, Excel files)
    if output_dir and output_dir.exists():
        output_manifest = index_artifacts(output_dir, run_id)
        # Merge artifacts from output directory
        for artifact in output_manifest.artifacts:
            # Only add if not already in manifest (avoid duplicates)
            if not any(a.relative_path == artifact.relative_path for a in manifest.artifacts):
                manifest.artifacts.append(artifact)
    
    # Save manifest to artifacts directory
    manifest_path = artifacts_dir / 'artifact_manifest.json'
    manifest.save(manifest_path)
    
    return manifest

"""Backward compatibility checks for pipeline versions."""

import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..config import get_app_version


class CompatibilityStatus(Enum):
    """Compatibility status for artifacts."""
    COMPATIBLE = "compatible"
    WARNING = "warning"  # May work but not guaranteed
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"  # Cannot determine


@dataclass
class CompatibilityResult:
    """Result of compatibility check."""
    status: CompatibilityStatus
    current_version: str
    artifact_version: Optional[str]
    message: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


def get_pipeline_version() -> str:
    """Get current pipeline version.
    
    Returns:
        Pipeline version string (e.g., "0.1.0")
    """
    return get_app_version()


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse version string into major, minor, patch.
    
    Args:
        version_str: Version string (e.g., "0.1.0")
        
    Returns:
        Tuple of (major, minor, patch)
    """
    try:
        parts = version_str.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def check_compatibility(
    artifact_version: Optional[str],
    current_version: Optional[str] = None
) -> CompatibilityResult:
    """Check compatibility between artifact version and current version.
    
    Args:
        artifact_version: Version string from artifact (e.g., from run_summary.json)
        current_version: Current pipeline version (defaults to get_pipeline_version())
        
    Returns:
        CompatibilityResult with status and message
        
    Compatibility Policy:
    - Same major.minor.patch: COMPATIBLE
    - Same major.minor, different patch: WARNING (patch changes may affect behavior)
    - Same major, different minor: WARNING (minor changes may affect behavior)
    - Different major: INCOMPATIBLE (breaking changes)
    - Missing version: UNKNOWN (cannot determine)
    """
    if current_version is None:
        current_version = get_pipeline_version()
    
    if artifact_version is None:
        return CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN,
            current_version=current_version,
            artifact_version=None,
            message="Artifact version not found - cannot determine compatibility",
            details={"reason": "missing_version"}
        )
    
    # Parse versions
    current_parts = parse_version(current_version)
    artifact_parts = parse_version(artifact_version)
    
    current_major, current_minor, current_patch = current_parts
    artifact_major, artifact_minor, artifact_patch = artifact_parts
    
    # Check compatibility
    if current_major == artifact_major and current_minor == artifact_minor and current_patch == artifact_patch:
        # Exact match
        status = CompatibilityStatus.COMPATIBLE
        message = f"Artifact version {artifact_version} matches current version {current_version}"
    elif current_major == artifact_major and current_minor == artifact_minor:
        # Same major.minor, different patch
        status = CompatibilityStatus.WARNING
        message = (
            f"Artifact version {artifact_version} differs in patch version from current {current_version}. "
            f"Compatibility is likely but not guaranteed."
        )
    elif current_major == artifact_major:
        # Same major, different minor
        status = CompatibilityStatus.WARNING
        message = (
            f"Artifact version {artifact_version} differs in minor version from current {current_version}. "
            f"Some features may have changed. Review recommended."
        )
    else:
        # Different major version
        status = CompatibilityStatus.INCOMPATIBLE
        message = (
            f"Artifact version {artifact_version} is incompatible with current version {current_version}. "
            f"Major version changes indicate breaking changes."
        )
    
    return CompatibilityResult(
        status=status,
        current_version=current_version,
        artifact_version=artifact_version,
        message=message,
        details={
            "current_major": current_major,
            "current_minor": current_minor,
            "current_patch": current_patch,
            "artifact_major": artifact_major,
            "artifact_minor": artifact_minor,
            "artifact_patch": artifact_patch
        }
    )


def check_run_summary_compatibility(run_summary_path: Path) -> CompatibilityResult:
    """Check compatibility of a run_summary.json file.
    
    Args:
        run_summary_path: Path to run_summary.json
        
    Returns:
        CompatibilityResult
    """
    if not run_summary_path.exists():
        return CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN,
            current_version=get_pipeline_version(),
            artifact_version=None,
            message=f"Run summary file not found: {run_summary_path}",
            details={"reason": "file_not_found"}
        )
    
    try:
        with open(run_summary_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        artifact_version = data.get('pipeline_version')
        return check_compatibility(artifact_version)
    except (json.JSONDecodeError, IOError) as e:
        return CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN,
            current_version=get_pipeline_version(),
            artifact_version=None,
            message=f"Error reading run summary: {e}",
            details={"reason": "read_error", "error": str(e)}
        )


def check_artifact_manifest_compatibility(manifest_path: Path) -> CompatibilityResult:
    """Check compatibility of an artifact_manifest.json file.
    
    Args:
        manifest_path: Path to artifact_manifest.json
        
    Returns:
        CompatibilityResult
    """
    if not manifest_path.exists():
        return CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN,
            current_version=get_pipeline_version(),
            artifact_version=None,
            message=f"Artifact manifest file not found: {manifest_path}",
            details={"reason": "file_not_found"}
        )
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # ArtifactManifest has manifest_version, not pipeline_version
        # For now, we'll check manifest_version format
        manifest_version = data.get('manifest_version', '1.0')
        
        # If manifest_version is "1.0", assume it's from current pipeline version
        # In future, we could add pipeline_version to ArtifactManifest
        if manifest_version == "1.0":
            # Assume compatible for now (same manifest format)
            return CompatibilityResult(
                status=CompatibilityStatus.COMPATIBLE,
                current_version=get_pipeline_version(),
                artifact_version=None,  # Not stored in manifest yet
                message="Artifact manifest format is compatible (version 1.0)",
                details={"manifest_version": manifest_version}
            )
        else:
            return CompatibilityResult(
                status=CompatibilityStatus.WARNING,
                current_version=get_pipeline_version(),
                artifact_version=None,
                message=f"Artifact manifest version {manifest_version} may not be fully compatible",
                details={"manifest_version": manifest_version}
            )
    except (json.JSONDecodeError, IOError) as e:
        return CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN,
            current_version=get_pipeline_version(),
            artifact_version=None,
            message=f"Error reading artifact manifest: {e}",
            details={"reason": "read_error", "error": str(e)}
        )


def check_artifacts_compatibility(artifacts_dir: Path) -> Dict[str, CompatibilityResult]:
    """Check compatibility of all artifacts in a directory.
    
    Args:
        artifacts_dir: Directory containing artifacts
        
    Returns:
        Dict mapping artifact type to CompatibilityResult
    """
    results = {}
    
    # Check run_summary.json if exists
    run_summary_path = artifacts_dir / "run_summary.json"
    if not run_summary_path.exists():
        # Try parent directory
        run_summary_path = artifacts_dir.parent / "run_summary.json"
    
    if run_summary_path.exists():
        results['run_summary'] = check_run_summary_compatibility(run_summary_path)
    
    # Check artifact_manifest.json
    manifest_path = artifacts_dir / "artifact_manifest.json"
    if manifest_path.exists():
        results['artifact_manifest'] = check_artifact_manifest_compatibility(manifest_path)
    
    return results

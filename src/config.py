"""Central configuration for EPG PDF Extraherare."""

import os
from pathlib import Path


def get_app_name() -> str:
    """Get application name."""
    return "EPG PDF Extraherare"


def get_app_version() -> str:
    """Get application version from pyproject.toml."""
    try:
        import tomli
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomli.load(f)
            return pyproject.get("project", {}).get("version", "0.1.0")
    except Exception:
        # Fallback version if pyproject.toml cannot be read
        return "0.1.0"


def get_default_output_dir() -> Path:
    """Get default output directory based on OS.
    
    Returns:
        Path object to default output directory (created if needed)
    """
    if os.name == 'nt':  # Windows
        userprofile = os.getenv('USERPROFILE', '')
        if userprofile:
            base = Path(userprofile) / 'Documents' / 'EPG PDF Extraherare'
        else:
            # Fallback to home directory
            base = Path.home() / 'Documents' / 'EPG PDF Extraherare'
    else:
        # Linux/Mac
        base = Path.home() / '.epg-pdf-extraherare'
    
    output_dir = base / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_output_subdirs(base_output_dir: Path) -> dict:
    """Get output subdirectory structure.
    
    Args:
        base_output_dir: Base output directory path
        
    Returns:
        Dict with keys: 'excel', 'review', 'errors', 'temp'
    """
    subdirs = {
        'excel': base_output_dir / 'excel',
        'review': base_output_dir / 'review',
        'errors': base_output_dir / 'errors',
        'temp': base_output_dir / 'temp',
    }
    
    # Create subdirectories if needed
    for subdir in subdirs.values():
        subdir.mkdir(parents=True, exist_ok=True)
    
    return subdirs

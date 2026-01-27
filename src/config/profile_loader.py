"""Profile loader for configurable pipeline behavior."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ProfileConfig:
    """Configuration profile for pipeline behavior."""
    name: str
    description: str = ""
    header: Dict[str, Any] = field(default_factory=dict)
    footer: Dict[str, Any] = field(default_factory=dict)
    zones: Dict[str, float] = field(default_factory=dict)
    tolerances: Dict[str, float] = field(default_factory=dict)
    ocr_routing: Dict[str, Any] = field(default_factory=dict)
    ai_policy: Dict[str, Any] = field(default_factory=dict)
    table_parser_mode: str = "auto"  # "auto" | "text" | "pos"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProfileConfig':
        """Create ProfileConfig from dictionary."""
        return cls(
            name=data.get('name', 'default'),
            description=data.get('description', ''),
            header=data.get('header', {}),
            footer=data.get('footer', {}),
            zones=data.get('zones', {}),
            tolerances=data.get('tolerances', {}),
            ocr_routing=data.get('ocr_routing', {}),
            ai_policy=data.get('ai_policy', {}),
            table_parser_mode=data.get('table_parser_mode', 'auto')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'header': self.header,
            'footer': self.footer,
            'zones': self.zones,
            'tolerances': self.tolerances,
            'ocr_routing': self.ocr_routing,
            'ai_policy': self.ai_policy,
            'table_parser_mode': self.table_parser_mode
        }


def get_profiles_dir() -> Path:
    """Get directory containing profile YAML files.
    
    Returns:
        Path to profiles directory
    """
    # Look for profiles in configs/profiles relative to project root
    current_file = Path(__file__).resolve()
    # src/config/profile_loader.py -> src/config -> src -> root
    project_root = current_file.parent.parent.parent
    profiles_dir = project_root / "configs" / "profiles"
    return profiles_dir


def load_profile(profile_name: str = "default") -> ProfileConfig:
    """Load a configuration profile.
    
    Args:
        profile_name: Name of profile to load (without .yaml extension)
        
    Returns:
        ProfileConfig object
        
    Raises:
        FileNotFoundError: If profile file doesn't exist
        ValueError: If profile file is invalid
    """
    profiles_dir = get_profiles_dir()
    profile_path = profiles_dir / f"{profile_name}.yaml"
    
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_name} (expected at {profile_path})")
    
    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError(f"Profile file is empty: {profile_path}")
        
        return ProfileConfig.from_dict(data)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in profile {profile_name}: {e}")
    except Exception as e:
        raise ValueError(f"Error loading profile {profile_name}: {e}")


def list_available_profiles() -> list[str]:
    """List all available profile names.
    
    Returns:
        List of profile names (without .yaml extension)
    """
    profiles_dir = get_profiles_dir()
    
    if not profiles_dir.exists():
        return ["default"]
    
    profiles = []
    for profile_file in profiles_dir.glob("*.yaml"):
        profiles.append(profile_file.stem)
    
    return sorted(profiles) if profiles else ["default"]


def get_default_profile() -> ProfileConfig:
    """Get default profile (always available).
    
    Returns:
        Default ProfileConfig
    """
    try:
        return load_profile("default")
    except FileNotFoundError:
        # Fallback: return minimal default config
        return ProfileConfig(
            name="default",
            description="Default configuration",
            header={},
            footer={},
            zones={},
            tolerances={},
            table_parser_mode="auto"
        )

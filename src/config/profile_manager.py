"""Global profile manager for pipeline configuration."""

from typing import Optional
from .profile_loader import ProfileConfig, load_profile, get_default_profile

# Global profile instance
_current_profile: Optional[ProfileConfig] = None


def set_profile(profile_name: str = "default") -> ProfileConfig:
    """Set the active profile for the pipeline.
    
    Args:
        profile_name: Name of profile to load
        
    Returns:
        Loaded ProfileConfig
        
    Raises:
        FileNotFoundError: If profile doesn't exist
        ValueError: If profile is invalid
    """
    global _current_profile
    _current_profile = load_profile(profile_name)
    return _current_profile


def get_profile() -> ProfileConfig:
    """Get the current active profile.
    
    Returns:
        Current ProfileConfig (default if none set)
    """
    global _current_profile
    if _current_profile is None:
        _current_profile = get_default_profile()
    return _current_profile


def reset_profile():
    """Reset to default profile."""
    global _current_profile
    _current_profile = None

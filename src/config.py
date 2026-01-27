"""Central configuration for EPG PDF Extraherare."""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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
    """Get default output directory based on run context and OS.

    - Running from source (dev): uses project root / "out".
    - Running from built app (frozen/PyInstaller): uses Documents/... on Windows,
      ~/.epg-pdf-extraherare/output on Linux/Mac.

    Returns:
        Path object to default output directory (created if needed)
    """
    if getattr(sys, "frozen", False):
        # Built app: use user-facing locations
        if os.name == "nt":  # Windows
            userprofile = os.getenv("USERPROFILE", "")
            base = Path(userprofile) / "Documents" / "EPG PDF Extraherare" if userprofile else Path.home() / "Documents" / "EPG PDF Extraherare"
        else:
            base = Path.home() / ".epg-pdf-extraherare"
        output_dir = base / "output"
    else:
        # Dev/source: use project root / out
        output_dir = Path(__file__).resolve().parent.parent / "out"
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


def get_ai_enabled() -> bool:
    """Check if AI enrichment is enabled.
    
    Returns:
        True if AI_ENABLED environment variable is set to 'true' (case-insensitive)
        Also checks saved config file if env var not set
    """
    env_value = os.getenv('AI_ENABLED')
    if env_value is not None:
        return env_value.lower() == 'true'
    
    # Fallback to saved config
    config = load_ai_config()
    return config.get('enabled', False)


def get_ai_endpoint() -> Optional[str]:
    """Get AI service endpoint URL.
    
    Returns:
        AI endpoint URL from AI_ENDPOINT environment variable, or None
    """
    return os.getenv('AI_ENDPOINT')


def get_ai_provider() -> str:
    """Get AI provider name.
    
    Returns:
        Provider name ("openai" or "claude"), default "openai"
    """
    provider = os.getenv('AI_PROVIDER', 'openai').lower()
    if provider not in ['openai', 'claude']:
        logger.warning(f"Invalid AI provider: {provider}, using 'openai'")
        return 'openai'
    return provider


def get_ai_model() -> str:
    """Get AI model name.
    
    Returns:
        Model name (provider-specific default if not set)
        Also checks saved config file if env var not set
    """
    model = os.getenv('AI_MODEL')
    if model:
        return model
    
    # Fallback to saved config
    config = load_ai_config()
    model = config.get('model')
    if model:
        return model
    
    # Use provider-specific defaults
    provider = get_ai_provider()
    if provider == 'openai':
        return 'gpt-4-turbo-preview'
    elif provider == 'claude':
        return 'claude-3-opus-20240229'
    
    return 'gpt-4-turbo-preview'  # Default fallback


def get_ai_key() -> Optional[str]:
    """Get AI service API key.
    
    Returns:
        API key from AI_KEY environment variable, or from saved config, or None
    """
    key = os.getenv('AI_KEY')
    if key:
        return key
    
    # Fallback to saved config
    config = load_ai_config()
    return config.get('api_key')


def get_calibration_enabled() -> bool:
    """Check if confidence calibration is enabled.
    
    Returns:
        True if CALIBRATION_ENABLED environment variable is set to 'true' (case-insensitive),
        defaults to True if not set
    """
    env_value = os.getenv('CALIBRATION_ENABLED', 'true')
    return env_value.lower() == 'true'


def get_calibration_model_path() -> Path:
    """Get path to calibration model file.
    
    Returns:
        Path to calibration model file (default: configs/calibration_model.joblib)
    """
    env_path = os.getenv('CALIBRATION_MODEL_PATH')
    if env_path:
        return Path(env_path)
    return Path(__file__).parent.parent / "configs" / "calibration_model.joblib"


def get_learning_enabled() -> bool:
    """Check if learning system is enabled.
    
    Returns:
        True if LEARNING_ENABLED environment variable is set to 'true' (case-insensitive),
        defaults to True if not set
    """
    env_value = os.getenv('LEARNING_ENABLED', 'true')
    return env_value.lower() == 'true'


def get_learning_db_path() -> Path:
    """Get path to learning database file.
    
    Returns:
        Path to learning database file (default: data/learning.db)
    """
    env_path = os.getenv('LEARNING_DB_PATH')
    if env_path:
        return Path(env_path)
    return Path(__file__).parent.parent / "data" / "learning.db"


def get_ai_config_path() -> Path:
    """Get path to AI configuration file.
    
    Returns:
        Path to AI config file (default: configs/ai_config.json)
    """
    return Path(__file__).parent.parent / "configs" / "ai_config.json"


def load_ai_config() -> dict:
    """Load AI configuration from file.
    
    Returns:
        Dict with AI configuration (enabled, provider, model, api_key)
    """
    config_path = get_ai_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            logger.warning(f"Failed to load AI config: {e}")
    
    return {}


def save_ai_config(config: dict) -> None:
    """Save AI configuration to file.
    
    Args:
        config: Dict with AI configuration (enabled, provider, model, api_key)
    """
    config_path = get_ai_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save AI config: {e}")
        raise


def set_ai_config(
    enabled: bool,
    provider: str,
    model: str,
    api_key: Optional[str] = None
) -> None:
    """Set AI configuration and save to file.
    
    Args:
        enabled: Whether AI is enabled
        provider: AI provider ("openai" or "claude")
        model: Model name
        api_key: Optional API key (if None, keeps existing key)
    """
    config = load_ai_config()
    
    config['enabled'] = enabled
    config['provider'] = provider
    config['model'] = model
    
    # Only update API key if provided
    if api_key is not None:
        config['api_key'] = api_key
    # If api_key is None and no existing key, don't set it
    
    save_ai_config(config)
    
    # Also set environment variables for current session
    os.environ['AI_ENABLED'] = 'true' if enabled else 'false'
    os.environ['AI_PROVIDER'] = provider
    os.environ['AI_MODEL'] = model
    if api_key:
        os.environ['AI_KEY'] = api_key


def clear_ai_config() -> None:
    """Remove all AI configuration (provider, model, key, enabled)."""
    save_ai_config({})
    for k in ('AI_ENABLED', 'AI_PROVIDER', 'AI_MODEL', 'AI_KEY'):
        os.environ.pop(k, None)


def _load_ai_config_from_file() -> None:
    """Load AI config from file and set environment variables.
    Called at module import to initialize from saved config.
    """
    config = load_ai_config()
    
    if 'enabled' in config:
        os.environ['AI_ENABLED'] = 'true' if config['enabled'] else 'false'
    if 'provider' in config:
        os.environ['AI_PROVIDER'] = config['provider']
    if 'model' in config:
        os.environ['AI_MODEL'] = config['model']
    if 'api_key' in config:
        os.environ['AI_KEY'] = config['api_key']


def get_table_parser_mode() -> str:
    """Get table parser mode from active profile.
    
    Returns:
        "auto" | "text" | "pos"
        - "auto": Run mode A (text-based), fallback to mode B (position-based) on validation failure
        - "text": Always use mode A (text-based)
        - "pos": Always use mode B (position-based)
        
    Default: "auto"
    """
    try:
        from .config.profile_manager import get_profile
        profile = get_profile()
        mode = profile.table_parser_mode
        # Validate mode
        if mode not in ("auto", "text", "pos"):
            logger.warning(f"Invalid table_parser_mode '{mode}', using 'auto'")
            return "auto"
        return mode
    except Exception as e:
        logger.warning(f"Failed to get table_parser_mode from profile: {e}, using 'auto'")
        return "auto"


def set_table_parser_mode(mode: str) -> None:
    """Set table parser mode (for testing/debugging).
    
    Args:
        mode: "auto" | "text" | "pos"
        
    Note:
        This sets the mode on the current profile instance, but does not persist
        to YAML file. For persistent configuration, edit the profile YAML file.
    """
    if mode not in ("auto", "text", "pos"):
        raise ValueError(f"Invalid table_parser_mode: {mode} (must be 'auto', 'text', or 'pos')")
    
    try:
        from .config.profile_manager import get_profile
        profile = get_profile()
        profile.table_parser_mode = mode
    except Exception as e:
        logger.warning(f"Failed to set table_parser_mode: {e}")


# Load saved config at module import
_load_ai_config_from_file()

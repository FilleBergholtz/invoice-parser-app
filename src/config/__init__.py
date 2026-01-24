"""Configuration package."""

# Re-export functions from parent config module
# Note: config.py is in src/, not src/config/, so we import from parent
import importlib.util
from pathlib import Path

# Import config module from parent directory
config_path = Path(__file__).parent.parent / "config.py"
spec = importlib.util.spec_from_file_location("config", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)

# Re-export
get_app_name = config_module.get_app_name
get_app_version = config_module.get_app_version
get_default_output_dir = config_module.get_default_output_dir
get_output_subdirs = config_module.get_output_subdirs
get_ai_enabled = config_module.get_ai_enabled
get_ai_endpoint = config_module.get_ai_endpoint
get_ai_key = config_module.get_ai_key
get_calibration_enabled = config_module.get_calibration_enabled
get_calibration_model_path = config_module.get_calibration_model_path
get_learning_enabled = config_module.get_learning_enabled
get_learning_db_path = config_module.get_learning_db_path
get_ai_provider = config_module.get_ai_provider
get_ai_model = config_module.get_ai_model

__all__ = [
    'get_app_name',
    'get_app_version',
    'get_default_output_dir',
    'get_output_subdirs',
    'get_ai_enabled',
    'get_ai_endpoint',
    'get_ai_key',
    'get_ai_provider',
    'get_ai_model',
    'get_calibration_enabled',
    'get_calibration_model_path',
    'get_learning_enabled',
    'get_learning_db_path',
]

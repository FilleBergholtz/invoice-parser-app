"""Unit tests for profile loader."""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config.profile_loader import (
    ProfileConfig,
    load_profile,
    list_available_profiles,
    get_default_profile,
    get_profiles_dir
)
from src.config.profile_manager import set_profile, get_profile, reset_profile


class TestProfileConfig:
    """Test ProfileConfig dataclass."""
    
    def test_profile_config_creation(self):
        """Test creating ProfileConfig."""
        config = ProfileConfig(
            name="test",
            description="Test profile",
            header={"keywords": ["test"]},
            footer={"keywords": ["total"]},
            zones={"header_zone": 0.3},
            tolerances={"validation": 1.0}
        )
        
        assert config.name == "test"
        assert config.description == "Test profile"
        assert config.header["keywords"] == ["test"]
        assert config.footer["keywords"] == ["total"]
        assert config.zones["header_zone"] == 0.3
        assert config.tolerances["validation"] == 1.0
    
    def test_profile_config_from_dict(self):
        """Test creating ProfileConfig from dictionary."""
        data = {
            "name": "test",
            "description": "Test",
            "header": {"keywords": ["test"]},
            "footer": {"keywords": ["total"]},
            "zones": {"header_zone": 0.3},
            "tolerances": {"validation": 1.0}
        }
        
        config = ProfileConfig.from_dict(data)
        
        assert config.name == "test"
        assert config.header["keywords"] == ["test"]
    
    def test_profile_config_to_dict(self):
        """Test converting ProfileConfig to dictionary."""
        config = ProfileConfig(
            name="test",
            description="Test",
            header={"keywords": ["test"]}
        )
        
        data = config.to_dict()
        
        assert data["name"] == "test"
        assert data["description"] == "Test"
        assert data["header"]["keywords"] == ["test"]


class TestLoadProfile:
    """Test profile loading."""
    
    def test_load_profile_default(self, tmp_path):
        """Test loading default profile."""
        # Mock profiles directory
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        
        default_profile = {
            "name": "default",
            "description": "Default profile",
            "header": {"keywords": ["fakturanummer"]},
            "footer": {"keywords": ["total"]},
            "zones": {"header_zone": 0.3},
            "tolerances": {"validation": 1.0}
        }
        
        (profiles_dir / "default.yaml").write_text(
            yaml.dump(default_profile),
            encoding='utf-8'
        )
        
        with patch('src.config.profile_loader.get_profiles_dir', return_value=profiles_dir):
            profile = load_profile("default")
            
            assert profile.name == "default"
            assert profile.description == "Default profile"
            assert "fakturanummer" in profile.header["keywords"]
    
    def test_load_profile_not_found(self, tmp_path):
        """Test loading non-existent profile."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        
        with patch('src.config.profile_loader.get_profiles_dir', return_value=profiles_dir):
            with pytest.raises(FileNotFoundError):
                load_profile("nonexistent")
    
    def test_load_profile_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML profile."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        
        (profiles_dir / "invalid.yaml").write_text("invalid: yaml: content: [", encoding='utf-8')
        
        with patch('src.config.profile_loader.get_profiles_dir', return_value=profiles_dir):
            with pytest.raises(ValueError):
                load_profile("invalid")


class TestProfileManager:
    """Test profile manager."""
    
    def test_set_and_get_profile(self, tmp_path):
        """Test setting and getting profile."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        
        test_profile = {
            "name": "test",
            "description": "Test profile"
        }
        
        (profiles_dir / "test.yaml").write_text(
            yaml.dump(test_profile),
            encoding='utf-8'
        )
        
        with patch('src.config.profile_loader.get_profiles_dir', return_value=profiles_dir):
            reset_profile()
            profile = set_profile("test")
            
            assert profile.name == "test"
            
            current = get_profile()
            assert current.name == "test"
    
    def test_get_default_profile(self):
        """Test getting default profile."""
        reset_profile()
        profile = get_profile()
        
        # Should return default profile (even if file doesn't exist, returns minimal config)
        assert profile.name == "default"


class TestListProfiles:
    """Test listing available profiles."""
    
    def test_list_available_profiles(self, tmp_path):
        """Test listing profiles."""
        profiles_dir = tmp_path / "profiles"
        profiles_dir.mkdir()
        
        (profiles_dir / "default.yaml").write_text("name: default", encoding='utf-8')
        (profiles_dir / "custom.yaml").write_text("name: custom", encoding='utf-8')
        
        with patch('src.config.profile_loader.get_profiles_dir', return_value=profiles_dir):
            profiles = list_available_profiles()
            
            assert "default" in profiles
            assert "custom" in profiles

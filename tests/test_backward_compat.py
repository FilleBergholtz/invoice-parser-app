"""Unit tests for backward compatibility checks."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch

from src.versioning.compat import (
    CompatibilityStatus,
    CompatibilityResult,
    get_pipeline_version,
    parse_version,
    check_compatibility,
    check_run_summary_compatibility,
    check_artifact_manifest_compatibility,
    check_artifacts_compatibility
)


class TestParseVersion:
    """Test version parsing."""
    
    def test_parse_version_standard(self):
        """Test parsing standard version string."""
        assert parse_version("0.1.0") == (0, 1, 0)
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("10.20.30") == (10, 20, 30)
    
    def test_parse_version_incomplete(self):
        """Test parsing incomplete version string."""
        assert parse_version("1.2") == (1, 2, 0)
        assert parse_version("1") == (1, 0, 0)
        assert parse_version("") == (0, 0, 0)
    
    def test_parse_version_invalid(self):
        """Test parsing invalid version string."""
        assert parse_version("invalid") == (0, 0, 0)
        assert parse_version("1.2.3.4") == (1, 2, 3)  # Extra parts ignored


class TestCheckCompatibility:
    """Test compatibility checking."""
    
    def test_compatible_exact_match(self):
        """Test exact version match."""
        result = check_compatibility("0.1.0", "0.1.0")
        assert result.status == CompatibilityStatus.COMPATIBLE
        assert "matches" in result.message.lower()
    
    def test_warning_patch_difference(self):
        """Test patch version difference."""
        result = check_compatibility("0.1.0", "0.1.1")
        assert result.status == CompatibilityStatus.WARNING
        assert "patch" in result.message.lower()
    
    def test_warning_minor_difference(self):
        """Test minor version difference."""
        result = check_compatibility("0.1.0", "0.2.0")
        assert result.status == CompatibilityStatus.WARNING
        assert "minor" in result.message.lower()
    
    def test_incompatible_major_difference(self):
        """Test major version difference."""
        result = check_compatibility("0.1.0", "1.0.0")
        assert result.status == CompatibilityStatus.INCOMPATIBLE
        assert "incompatible" in result.message.lower()
    
    def test_unknown_missing_version(self):
        """Test missing artifact version."""
        result = check_compatibility(None, "0.1.0")
        assert result.status == CompatibilityStatus.UNKNOWN
        assert "not found" in result.message.lower()
    
    @patch('src.versioning.compat.get_app_version')
    def test_check_compatibility_defaults(self, mock_version):
        """Test check_compatibility uses default version."""
        mock_version.return_value = "0.1.0"
        result = check_compatibility("0.1.0")
        assert result.current_version == "0.1.0"
        assert result.status == CompatibilityStatus.COMPATIBLE


class TestCheckRunSummaryCompatibility:
    """Test run summary compatibility checking."""
    
    def test_check_run_summary_compatible(self, tmp_path):
        """Test checking compatible run summary."""
        run_summary_path = tmp_path / "run_summary.json"
        
        with patch('src.versioning.compat.get_pipeline_version', return_value="0.1.0"):
            run_summary_data = {
                "run_id": "test-123",
                "pipeline_version": "0.1.0"
            }
            run_summary_path.write_text(
                json.dumps(run_summary_data),
                encoding='utf-8'
            )
            
            result = check_run_summary_compatibility(run_summary_path)
            assert result.status == CompatibilityStatus.COMPATIBLE
            assert result.artifact_version == "0.1.0"
    
    def test_check_run_summary_incompatible(self, tmp_path):
        """Test checking incompatible run summary."""
        run_summary_path = tmp_path / "run_summary.json"
        
        with patch('src.versioning.compat.get_pipeline_version', return_value="1.0.0"):
            run_summary_data = {
                "run_id": "test-123",
                "pipeline_version": "0.1.0"
            }
            run_summary_path.write_text(
                json.dumps(run_summary_data),
                encoding='utf-8'
            )
            
            result = check_run_summary_compatibility(run_summary_path)
            assert result.status == CompatibilityStatus.INCOMPATIBLE
    
    def test_check_run_summary_missing_file(self, tmp_path):
        """Test checking non-existent run summary."""
        run_summary_path = tmp_path / "nonexistent.json"
        
        result = check_run_summary_compatibility(run_summary_path)
        assert result.status == CompatibilityStatus.UNKNOWN
        assert "not found" in result.message.lower()
    
    def test_check_run_summary_invalid_json(self, tmp_path):
        """Test checking invalid JSON."""
        run_summary_path = tmp_path / "run_summary.json"
        run_summary_path.write_text("invalid json", encoding='utf-8')
        
        result = check_run_summary_compatibility(run_summary_path)
        assert result.status == CompatibilityStatus.UNKNOWN
        assert "error" in result.message.lower()


class TestCheckArtifactManifestCompatibility:
    """Test artifact manifest compatibility checking."""
    
    def test_check_manifest_compatible(self, tmp_path):
        """Test checking compatible manifest."""
        manifest_path = tmp_path / "artifact_manifest.json"
        
        manifest_data = {
            "manifest_version": "1.0",
            "run_id": "test-123"
        }
        manifest_path.write_text(
            json.dumps(manifest_data),
            encoding='utf-8'
        )
        
        result = check_artifact_manifest_compatibility(manifest_path)
        assert result.status == CompatibilityStatus.COMPATIBLE
    
    def test_check_manifest_missing_file(self, tmp_path):
        """Test checking non-existent manifest."""
        manifest_path = tmp_path / "nonexistent.json"
        
        result = check_artifact_manifest_compatibility(manifest_path)
        assert result.status == CompatibilityStatus.UNKNOWN


class TestCheckArtifactsCompatibility:
    """Test checking all artifacts in directory."""
    
    def test_check_artifacts_with_summary(self, tmp_path):
        """Test checking artifacts directory with run summary."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        
        run_summary_path = tmp_path / "run_summary.json"
        with patch('src.versioning.compat.get_pipeline_version', return_value="0.1.0"):
            run_summary_data = {
                "run_id": "test-123",
                "pipeline_version": "0.1.0"
            }
            run_summary_path.write_text(
                json.dumps(run_summary_data),
                encoding='utf-8'
            )
            
            results = check_artifacts_compatibility(artifacts_dir)
            assert 'run_summary' in results
            assert results['run_summary'].status == CompatibilityStatus.COMPATIBLE
    
    def test_check_artifacts_with_manifest(self, tmp_path):
        """Test checking artifacts directory with manifest."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        
        manifest_path = artifacts_dir / "artifact_manifest.json"
        manifest_data = {
            "manifest_version": "1.0",
            "run_id": "test-123"
        }
        manifest_path.write_text(
            json.dumps(manifest_data),
            encoding='utf-8'
        )
        
        results = check_artifacts_compatibility(artifacts_dir)
        assert 'artifact_manifest' in results
        assert results['artifact_manifest'].status == CompatibilityStatus.COMPATIBLE

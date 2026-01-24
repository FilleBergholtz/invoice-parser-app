"""Unit tests for artifact manifest."""

import json
from pathlib import Path
from datetime import datetime

import pytest

from src.debug.artifact_manifest import (
    ArtifactManifest, ArtifactEntry, calculate_file_hash
)
from src.debug.artifact_index import (
    index_artifacts, create_manifest_for_run, determine_artifact_type
)


class TestArtifactManifest:
    """Test artifact manifest model."""
    
    def test_artifact_entry_creation(self):
        """Test creating an artifact entry."""
        entry = ArtifactEntry(
            filename="test.json",
            artifact_type="ai",
            pipeline_stage="ai_enrichment",
            relative_path="invoice_1/ai_request.json",
            file_size=1024,
            checksum="abc123"
        )
        
        assert entry.filename == "test.json"
        assert entry.artifact_type == "ai"
        assert entry.pipeline_stage == "ai_enrichment"
        assert entry.file_size == 1024
        assert entry.checksum == "abc123"
    
    def test_manifest_creation(self):
        """Test creating a manifest."""
        manifest = ArtifactManifest(
            run_id="test-run-123",
            created_at="2024-01-01T12:00:00"
        )
        
        assert manifest.run_id == "test-run-123"
        assert manifest.manifest_version == "1.0"
        assert len(manifest.artifacts) == 0
    
    def test_manifest_add_artifact(self):
        """Test adding artifacts to manifest."""
        manifest = ArtifactManifest(run_id="test-run-123")
        
        manifest.add_artifact(
            filename="ai_request.json",
            artifact_type="ai",
            relative_path="invoice_1/ai_request.json",
            file_size=1024,
            checksum="abc123",
            pipeline_stage="ai_enrichment"
        )
        
        assert len(manifest.artifacts) == 1
        assert manifest.artifacts[0].filename == "ai_request.json"
        assert manifest.artifacts[0].artifact_type == "ai"
    
    def test_manifest_save_and_load(self, tmp_path):
        """Test saving and loading manifest."""
        manifest = ArtifactManifest(
            run_id="test-run-123",
            created_at="2024-01-01T12:00:00"
        )
        
        manifest.add_artifact(
            filename="test.json",
            artifact_type="ai",
            relative_path="test.json",
            file_size=100,
            checksum="abc123"
        )
        
        # Save
        manifest_path = tmp_path / "manifest.json"
        manifest.save(manifest_path)
        
        assert manifest_path.exists()
        
        # Load
        loaded = ArtifactManifest.load(manifest_path)
        
        assert loaded.run_id == "test-run-123"
        assert len(loaded.artifacts) == 1
        assert loaded.artifacts[0].filename == "test.json"
    
    def test_calculate_file_hash(self, tmp_path):
        """Test file hash calculation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!", encoding='utf-8')
        
        hash1 = calculate_file_hash(test_file)
        hash2 = calculate_file_hash(test_file)
        
        # Same file should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex chars
        
        # Different content should produce different hash
        test_file.write_text("Different content", encoding='utf-8')
        hash3 = calculate_file_hash(test_file)
        assert hash1 != hash3


class TestArtifactIndex:
    """Test artifact indexing."""
    
    def test_determine_artifact_type(self):
        """Test artifact type determination."""
        # AI artifacts
        assert determine_artifact_type("ai_request.json", "invoice_1/ai_request.json") == ("ai", "ai_enrichment")
        assert determine_artifact_type("ai_response.json", "invoice_1/ai_response.json") == ("ai", "ai_enrichment")
        assert determine_artifact_type("ai_diff.json", "invoice_1/ai_diff.json") == ("ai", "ai_enrichment")
        
        # Summary
        assert determine_artifact_type("run_summary.json", "run_summary.json") == ("summary", None)
        
        # Excel
        assert determine_artifact_type("output.xlsx", "output.xlsx") == ("excel", "export")
        
        # Unknown
        assert determine_artifact_type("unknown.txt", "unknown.txt") == ("debug", None)
    
    def test_index_artifacts(self, tmp_path):
        """Test indexing artifacts in a directory."""
        # Create test artifacts
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        
        # Create some test files
        (artifacts_dir / "run_summary.json").write_text('{"run_id": "test"}', encoding='utf-8')
        (artifacts_dir / "invoice_1").mkdir()
        (artifacts_dir / "invoice_1" / "ai_request.json").write_text('{"test": "data"}', encoding='utf-8')
        (artifacts_dir / "invoice_1" / "ai_response.json").write_text('{"result": "ok"}', encoding='utf-8')
        
        # Index
        manifest = index_artifacts(artifacts_dir, "test-run-123")
        
        assert manifest.run_id == "test-run-123"
        assert len(manifest.artifacts) == 3  # run_summary + 2 AI files
        
        # Check that all files are indexed
        filenames = {a.filename for a in manifest.artifacts}
        assert "run_summary.json" in filenames
        assert "ai_request.json" in filenames
        assert "ai_response.json" in filenames
        
        # Check checksums are calculated
        for artifact in manifest.artifacts:
            assert artifact.checksum
            assert len(artifact.checksum) == 64  # SHA256
            assert artifact.file_size > 0
    
    def test_create_manifest_for_run(self, tmp_path):
        """Test creating and saving manifest for a run."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create test files
        (artifacts_dir / "test.json").write_text('{"test": "data"}', encoding='utf-8')
        (output_dir / "run_summary.json").write_text('{"run_id": "test-run-123"}', encoding='utf-8')
        
        # Create manifest
        manifest = create_manifest_for_run(artifacts_dir, "test-run-123", output_dir=output_dir)
        
        # Check manifest was created
        assert manifest.run_id == "test-run-123"
        assert len(manifest.artifacts) >= 1
        
        # Check manifest file was saved
        manifest_path = artifacts_dir / "artifact_manifest.json"
        assert manifest_path.exists()
        
        # Verify manifest can be loaded
        loaded = ArtifactManifest.load(manifest_path)
        assert loaded.run_id == "test-run-123"
        assert len(loaded.artifacts) == len(manifest.artifacts)
    
    def test_index_excludes_patterns(self, tmp_path):
        """Test that excluded patterns are not indexed."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        
        # Create files including excluded patterns
        (artifacts_dir / "test.json").write_text('{"test": "data"}', encoding='utf-8')
        (artifacts_dir / "__pycache__").mkdir()
        (artifacts_dir / "__pycache__" / "test.pyc").write_bytes(b'compiled')
        
        # Index
        manifest = index_artifacts(artifacts_dir, "test-run")
        
        # Should only include test.json, not .pyc files
        filenames = {a.filename for a in manifest.artifacts}
        assert "test.json" in filenames
        assert "test.pyc" not in filenames


class TestManifestCompleteness:
    """Test that manifest captures all expected artifacts."""
    
    def test_manifest_includes_all_types(self, tmp_path):
        """Test that manifest includes artifacts of all expected types."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        
        # Create various artifact types
        (artifacts_dir / "run_summary.json").write_text('{}', encoding='utf-8')
        (artifacts_dir / "output.xlsx").write_bytes(b'fake excel')
        
        invoice_dir = artifacts_dir / "invoice_1"
        invoice_dir.mkdir()
        (invoice_dir / "ai_request.json").write_text('{}', encoding='utf-8')
        (invoice_dir / "ai_response.json").write_text('{}', encoding='utf-8')
        
        # Index
        manifest = index_artifacts(artifacts_dir, "test-run")
        
        # Check artifact types are present
        artifact_types = {a.artifact_type for a in manifest.artifacts}
        assert "summary" in artifact_types
        assert "excel" in artifact_types
        assert "ai" in artifact_types
        
        # Check pipeline stages
        stages = {a.pipeline_stage for a in manifest.artifacts if a.pipeline_stage}
        assert "ai_enrichment" in stages
        assert "export" in stages

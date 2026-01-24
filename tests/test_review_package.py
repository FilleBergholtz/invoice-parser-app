"""Unit tests for review package export."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import zipfile

from src.review.review_package import (
    create_review_package,
    _generate_readme_content,
    _create_zip_from_folder
)


class TestCreateReviewPackage:
    """Test review package creation."""
    
    def test_create_review_package_basic(self, tmp_path):
        """Test creating a basic review package."""
        review_folder = tmp_path / "review" / "test_invoice__1"
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b'fake pdf')
        
        # Create package
        package_path = create_review_package(
            review_folder,
            pdf_path,
            excel_path=None,
            run_summary_path=None,
            artifact_manifest_path=None,
            create_zip=False
        )
        
        assert package_path == review_folder
        assert review_folder.exists()
        
        # Check README.txt exists
        readme_path = review_folder / "README.txt"
        assert readme_path.exists()
        
        # Check README content
        readme_content = readme_path.read_text(encoding='utf-8')
        assert "REVIEW PACKAGE" in readme_content
        assert "INSTRUKTIONER" in readme_content
    
    def test_create_review_package_with_excel(self, tmp_path):
        """Test creating review package with Excel file."""
        review_folder = tmp_path / "review" / "test_invoice__1"
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b'fake pdf')
        
        excel_path = tmp_path / "test.xlsx"
        excel_path.write_bytes(b'fake excel')
        
        package_path = create_review_package(
            review_folder,
            pdf_path,
            excel_path=excel_path,
            run_summary_path=None,
            artifact_manifest_path=None,
            create_zip=False
        )
        
        # Check Excel was copied
        copied_excel = review_folder / excel_path.name
        assert copied_excel.exists()
    
    def test_create_review_package_with_all_files(self, tmp_path):
        """Test creating review package with all files."""
        review_folder = tmp_path / "review" / "test_invoice__1"
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b'fake pdf')
        
        excel_path = tmp_path / "test.xlsx"
        excel_path.write_bytes(b'fake excel')
        
        run_summary_path = tmp_path / "run_summary.json"
        run_summary_path.write_text('{"run_id": "test"}', encoding='utf-8')
        
        artifact_manifest_path = tmp_path / "artifact_manifest.json"
        artifact_manifest_path.write_text('{"manifest_version": "1.0"}', encoding='utf-8')
        
        package_path = create_review_package(
            review_folder,
            pdf_path,
            excel_path=excel_path,
            run_summary_path=run_summary_path,
            artifact_manifest_path=artifact_manifest_path,
            create_zip=False
        )
        
        # Check all files exist
        assert (review_folder / excel_path.name).exists()
        assert (review_folder / "run_summary.json").exists()
        assert (review_folder / "artifact_manifest.json").exists()
        assert (review_folder / "README.txt").exists()
    
    def test_create_review_package_zip(self, tmp_path):
        """Test creating review package as ZIP file."""
        review_folder = tmp_path / "review" / "test_invoice__1"
        review_folder.mkdir(parents=True)
        
        # Create some test files
        (review_folder / "test.pdf").write_bytes(b'fake pdf')
        (review_folder / "test.xlsx").write_bytes(b'fake excel')
        (review_folder / "metadata.json").write_text('{}', encoding='utf-8')
        
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b'fake pdf')
        
        zip_path = create_review_package(
            review_folder,
            pdf_path,
            excel_path=None,
            run_summary_path=None,
            artifact_manifest_path=None,
            create_zip=True
        )
        
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"
        
        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            files = zipf.namelist()
            assert "test.pdf" in files or any("test.pdf" in f for f in files)
            assert "README.txt" in files or any("README.txt" in f for f in files)


class TestGenerateReadme:
    """Test README generation."""
    
    def test_generate_readme_basic(self):
        """Test generating basic README."""
        content = _generate_readme_content(
            "test.pdf",
            None,
            False,
            False
        )
        
        assert "REVIEW PACKAGE" in content
        assert "test.pdf" in content
        assert "INSTRUKTIONER" in content
    
    def test_generate_readme_with_all_files(self):
        """Test generating README with all files."""
        content = _generate_readme_content(
            "test.pdf",
            "test.xlsx",
            True,
            True
        )
        
        assert "test.pdf" in content
        assert "test.xlsx" in content
        assert "run_summary.json" in content
        assert "artifact_manifest.json" in content


class TestCreateZip:
    """Test ZIP creation."""
    
    def test_create_zip_from_folder(self, tmp_path):
        """Test creating ZIP from folder."""
        folder = tmp_path / "test_folder"
        folder.mkdir()
        
        # Create test files
        (folder / "file1.txt").write_text("content1", encoding='utf-8')
        (folder / "file2.txt").write_text("content2", encoding='utf-8')
        (folder / "subdir").mkdir()
        (folder / "subdir" / "file3.txt").write_text("content3", encoding='utf-8')
        
        zip_path = tmp_path / "test.zip"
        _create_zip_from_folder(folder, zip_path)
        
        assert zip_path.exists()
        
        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            files = zipf.namelist()
            assert "file1.txt" in files
            assert "file2.txt" in files
            assert "subdir/file3.txt" in files or "subdir\\file3.txt" in files

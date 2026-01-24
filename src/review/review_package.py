"""Review package export for invoices requiring manual review."""

import shutil
import zipfile
from pathlib import Path
from typing import Optional
from datetime import datetime


def create_review_package(
    review_folder: Path,
    pdf_path: Path,
    excel_path: Optional[Path] = None,
    run_summary_path: Optional[Path] = None,
    artifact_manifest_path: Optional[Path] = None,
    create_zip: bool = False
) -> Path:
    """Create a complete review package for an invoice requiring manual review.
    
    Args:
        review_folder: Path to review folder (already created by create_review_report)
        pdf_path: Path to original PDF file
        excel_path: Optional path to Excel file for this invoice
        run_summary_path: Optional path to run_summary.json
        artifact_manifest_path: Optional path to artifact_manifest.json
        create_zip: If True, create a ZIP file instead of just a folder
        
    Returns:
        Path to review package (folder or ZIP file)
        
    Creates:
    - Original PDF (already in review folder from create_review_report)
    - Excel file (if provided)
    - run_summary.json (if provided)
    - artifact_manifest.json (if provided)
    - README.txt (instructions for reviewer)
    """
    # Ensure review folder exists
    review_folder.mkdir(parents=True, exist_ok=True)
    
    # Copy Excel file if provided
    if excel_path and excel_path.exists():
        try:
            shutil.copy2(excel_path, review_folder / excel_path.name)
        except Exception as e:
            print(f"Warning: Failed to copy Excel file to review package: {e}")
    
    # Copy run_summary.json if provided
    if run_summary_path and run_summary_path.exists():
        try:
            shutil.copy2(run_summary_path, review_folder / "run_summary.json")
        except Exception as e:
            print(f"Warning: Failed to copy run_summary.json to review package: {e}")
    
    # Copy artifact_manifest.json if provided
    if artifact_manifest_path and artifact_manifest_path.exists():
        try:
            shutil.copy2(artifact_manifest_path, review_folder / "artifact_manifest.json")
        except Exception as e:
            print(f"Warning: Failed to copy artifact_manifest.json to review package: {e}")
    
    # Create README.txt with instructions
    readme_path = review_folder / "README.txt"
    readme_content = _generate_readme_content(
        pdf_path.name,
        excel_path.name if excel_path and excel_path.exists() else None,
        run_summary_path is not None and run_summary_path.exists(),
        artifact_manifest_path is not None and artifact_manifest_path.exists()
    )
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    # Create ZIP if requested
    if create_zip:
        zip_path = review_folder.parent / f"{review_folder.name}.zip"
        _create_zip_from_folder(review_folder, zip_path)
        return zip_path
    
    return review_folder


def _generate_readme_content(
    pdf_filename: str,
    excel_filename: Optional[str],
    has_run_summary: bool,
    has_artifact_manifest: bool
) -> str:
    """Generate README.txt content with instructions."""
    lines = [
        "=" * 70,
        "REVIEW PACKAGE - MANUELL GRANSKNING",
        "=" * 70,
        "",
        f"Detta paket innehåller all information som behövs för manuell granskning",
        f"av fakturan som kräver extra uppmärksamhet.",
        "",
        "INNEHÅLL:",
        "-" * 70,
        f"1. {pdf_filename}",
        "   Original PDF-faktura",
        ""
    ]
    
    if excel_filename:
        lines.extend([
            f"2. {excel_filename}",
            "   Extraherad data i Excel-format",
            ""
        ])
    
    if has_run_summary:
        lines.extend([
            "3. run_summary.json",
            "   Sammanfattning av processeringen med statistik och kvalitetspoäng",
            ""
        ])
    
    if has_artifact_manifest:
        lines.extend([
            "4. artifact_manifest.json",
            "   Index över alla genererade artifacts (debug-filer, AI-data, etc.)",
            ""
        ])
    
    lines.extend([
        "5. metadata.json",
        "   Extraherade fält, valideringsresultat och spårbarhetsdata",
        "",
        "INSTRUKTIONER:",
        "-" * 70,
        "1. Granska original PDF-fakturan för att verifiera extraherade data",
        "",
        "2. Jämför Excel-filen med original PDF:",
        "   - Kontrollera att alla produktrader är korrekt extraherade",
        "   - Verifiera att belopp, kvantiteter och enhetspriser stämmer",
        "   - Kontrollera att fakturanummer och datum är korrekta",
        "",
        "3. Om fel hittas:",
        "   - Notera vilka fält som är felaktiga i metadata.json",
        "   - Dokumentera eventuella problem i Excel-filen",
        "   - Kontakta utvecklingsteamet med feedback",
        "",
        "4. För teknisk information:",
        "   - Se run_summary.json för processeringsstatistik",
        "   - Se artifact_manifest.json för lista över alla genererade filer",
        "   - Se metadata.json för detaljerad extraktions- och valideringsdata",
        "",
        "=" * 70,
        f"Skapad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70
    ])
    
    return "\n".join(lines)


def _create_zip_from_folder(folder: Path, zip_path: Path):
    """Create a ZIP file from a folder."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in folder.rglob('*'):
            if file_path.is_file():
                # Add file with relative path
                arcname = file_path.relative_to(folder)
                zipf.write(file_path, arcname)

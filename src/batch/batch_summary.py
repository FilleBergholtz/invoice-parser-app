"""Batch summary Excel export."""

from pathlib import Path
from typing import List, Dict
import pandas as pd


def create_batch_summary(
    batch_results: List[Dict],
    output_path: Path
) -> Path:
    """Create batch_summary.xlsx with processing results.
    
    Args:
        batch_results: List of per-PDF result dicts from run_batch()
        output_path: Path where batch_summary.xlsx should be created
        
    Returns:
        Path to created Excel file
        
    Excel columns:
    - Filnamn: PDF filename
    - Status: Validation status (OK/PARTIAL/REVIEW/FAILED)
    - Quality Score: Quality score (0-100)
    - Output Path: Path to generated Excel file (if any)
    - Error: Error message (if failed)
    """
    # Prepare data for DataFrame
    rows = []
    
    for result in batch_results:
        rows.append({
            "Filnamn": result["filename"],
            "Status": result["status"],
            "Quality Score": round(result["quality_score"], 2),
            "Output Path": result["output_path"] or "",
            "Error": result["error"] or ""
        })
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Sort by status (OK, PARTIAL, REVIEW, FAILED) then by filename
    status_order = {"OK": 0, "PARTIAL": 1, "REVIEW": 2, "FAILED": 3}
    df["_status_order"] = df["Status"].map(status_order)
    df = df.sort_values(["_status_order", "Filnamn"])
    df = df.drop(columns=["_status_order"])
    
    # Write to Excel
    excel_path = output_path / "batch_summary.xlsx"
    df.to_excel(excel_path, index=False, engine="openpyxl")
    
    return excel_path

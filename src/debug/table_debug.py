"""Debug artifacts for table parsing validation failures (Phase 22)."""

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..models.invoice_line import InvoiceLine
from ..models.row import Row
from ..models.validation_result import ValidationResult
from .artifact_manifest import ArtifactManifest, calculate_file_hash

logger = logging.getLogger(__name__)


def save_table_debug_artifacts(
    artifacts_dir: Path,
    invoice_id: str,
    table_rows: List[Row],
    line_items: List[InvoiceLine],
    validation_result: ValidationResult,
    netto_total: Optional[Decimal] = None,
    mode_used: str = "A"
) -> None:
    """Save debug artifacts for table parsing validation failures.
    
    Args:
        artifacts_dir: Root artifacts directory
        invoice_id: Invoice identifier (e.g., filename or invoice number)
        table_rows: List of table rows (raw input)
        line_items: List of parsed InvoiceLine objects
        validation_result: ValidationResult with validation status and details
        netto_total: Optional netto total from footer (for validation comparison)
        mode_used: Parser mode used ("A" for text-based, "B" for position-based)
        
    Saves:
        1. table_block_raw_text.txt - Raw text from all table rows
        2. parsed_lines.json - Parsed line items (JSON format)
        3. validation_result.json - Validation result with diff, status, errors
        4. table_block_tokens.json - Token-level data for debugging (optional)
        
    Artifacts are saved to: artifacts_dir/invoices/{invoice_id}/table_debug/
    """
    # Create debug directory
    debug_dir = artifacts_dir / "invoices" / invoice_id / "table_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().isoformat()
    
    # 1. Save table_block_raw_text.txt
    raw_text_path = debug_dir / "table_block_raw_text.txt"
    with open(raw_text_path, 'w', encoding='utf-8') as f:
        for row in table_rows:
            f.write(row.text + '\n')
    
    # 2. Save parsed_lines.json
    parsed_lines_path = debug_dir / "parsed_lines.json"
    parsed_lines_data = {
        'timestamp': timestamp,
        'line_count': len(line_items),
        'lines': [
            {
                'line_number': line.line_number,
                'description': line.description,
                'quantity': str(line.quantity) if line.quantity is not None else None,
                'unit': line.unit,
                'unit_price': str(line.unit_price) if line.unit_price is not None else None,
                'discount': str(line.discount) if line.discount is not None else None,
                'total_amount': str(line.total_amount),
                'vat_rate': str(line.vat_rate) if line.vat_rate is not None else None,
                'row_count': len(line.rows),
            }
            for line in line_items
        ]
    }
    with open(parsed_lines_path, 'w', encoding='utf-8') as f:
        json.dump(parsed_lines_data, f, indent=2, ensure_ascii=False)
    
    # 3. Save validation_result.json
    validation_result_path = debug_dir / "validation_result.json"
    
    # Calculate netto_sum from line items
    netto_sum = sum(
        (line.total_amount for line in line_items),
        Decimal("0")
    )
    
    validation_data = {
        'timestamp': timestamp,
        'mode_used': mode_used,
        'netto_sum': str(netto_sum),
        'netto_total': str(netto_total) if netto_total is not None else None,
        'diff': str(validation_result.diff) if validation_result.diff is not None else None,
        'validation_passed': (
            abs(validation_result.diff) <= validation_result.tolerance
            if validation_result.diff is not None
            else False
        ),
        'tolerance': str(validation_result.tolerance),
        'status': validation_result.status,
        'hard_gate_passed': validation_result.hard_gate_passed,
        'invoice_number_confidence': validation_result.invoice_number_confidence,
        'total_confidence': validation_result.total_confidence,
        'errors': validation_result.errors,
        'warnings': validation_result.warnings,
    }
    with open(validation_result_path, 'w', encoding='utf-8') as f:
        json.dump(validation_data, f, indent=2, ensure_ascii=False)
    
    # 4. Save table_block_tokens.json (optional, for advanced debugging)
    tokens_path = debug_dir / "table_block_tokens.json"
    tokens_data = {
        'timestamp': timestamp,
        'row_count': len(table_rows),
        'rows': [
            {
                'row_index': idx,
                'text': row.text,
                'y': row.y,
                'x_min': row.x_min,
                'x_max': row.x_max,
                'tokens': [
                    {
                        'text': token.text,
                        'x': token.x,
                        'y': token.y,
                        'width': token.width,
                        'height': token.height,
                        'font_size': token.font_size,
                        'font_name': token.font_name,
                    }
                    for token in row.tokens
                ]
            }
            for idx, row in enumerate(table_rows)
        ]
    }
    with open(tokens_path, 'w', encoding='utf-8') as f:
        json.dump(tokens_data, f, indent=2, ensure_ascii=False)
    
    logger.info(
        f"Saved table debug artifacts for invoice {invoice_id} to {debug_dir}"
    )
    
    # Add artifacts to manifest (if manifest exists)
    try:
        manifest_path = artifacts_dir / 'artifact_manifest.json'
        if manifest_path.exists():
            manifest = ArtifactManifest.load(manifest_path)
            
            # Add all debug artifacts to manifest
            for artifact_file in [raw_text_path, parsed_lines_path, validation_result_path, tokens_path]:
                if artifact_file.exists():
                    relative_path = artifact_file.relative_to(artifacts_dir)
                    file_size = artifact_file.stat().st_size
                    checksum = calculate_file_hash(artifact_file)
                    
                    manifest.add_artifact(
                        filename=artifact_file.name,
                        artifact_type='debug',
                        relative_path=str(relative_path),
                        file_size=file_size,
                        checksum=checksum,
                        pipeline_stage='table_parsing_validation',
                        created_at=timestamp
                    )
            
            # Save updated manifest
            manifest.save(manifest_path)
    except Exception as e:
        logger.warning(f"Failed to update artifact manifest: {e}")

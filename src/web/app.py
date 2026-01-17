"""Streamlit web application for invoice parser."""

import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from ..cli.main import process_invoice
from ..export.excel_export import export_to_excel


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Invoice Parser",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Invoice Parser")
    st.markdown("Ladda upp PDF-fakturor för automatisk extraktion och validering")
    
    # Initialize session state
    if "results" not in st.session_state:
        st.session_state.results = []
    
    # File upload section
    st.header("1. Ladda upp fakturor")
    uploaded_files = st.file_uploader(
        "Välj PDF-fakturor",
        type=["pdf"],
        accept_multiple_files=True,
        help="Du kan ladda upp en eller flera PDF-fakturor samtidigt"
    )
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} fil(er) valda")
        
        # Process button
        if st.button("Processa fakturor", type="primary"):
            process_uploaded_files(uploaded_files)
    
    # Display results
    if st.session_state.results:
        display_results()
        
        # Clear results button
        if st.button("Rensa resultat", type="secondary"):
            st.session_state.results = []
            st.rerun()
    
    # Excel download
    if st.session_state.results:
        generate_excel_download()


def process_uploaded_files(uploaded_files: List) -> None:
    """Process uploaded PDF files using the pipeline.
    
    Args:
        uploaded_files: List of uploaded file objects from Streamlit
    """
    results = []
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            # Update progress
            progress = (idx + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"Processar {uploaded_file.name} ({idx + 1}/{len(uploaded_files)})...")
            
            # Save uploaded file temporarily
            temp_file_path = Path(temp_dir) / uploaded_file.name
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Process invoice
            try:
                result = process_invoice(
                    str(temp_file_path),
                    output_dir=temp_dir,
                    verbose=False
                )
                
                # Extract data from invoice_header and validation_result
                invoice_header = result.get("invoice_header")
                validation_result = result.get("validation_result")
                
                # Add filename and extracted fields to result
                result["filename"] = uploaded_file.name
                result["file_size"] = uploaded_file.size
                
                # Extract fields from invoice_header
                if invoice_header:
                    result["invoice_number"] = invoice_header.invoice_number or "TBD"
                    result["vendor_name"] = invoice_header.supplier_name or "TBD"
                    result["invoice_date"] = (
                        invoice_header.invoice_date.isoformat() 
                        if invoice_header.invoice_date else "TBD"
                    )
                    result["total_amount"] = invoice_header.total_amount or 0.0
                    result["invoice_number_confidence"] = invoice_header.invoice_number_confidence
                    result["total_confidence"] = invoice_header.total_confidence
                else:
                    result["invoice_number"] = "TBD"
                    result["vendor_name"] = "TBD"
                    result["invoice_date"] = "TBD"
                    result["total_amount"] = 0.0
                    result["invoice_number_confidence"] = 0.0
                    result["total_confidence"] = 0.0
                
                # Extract fields from validation_result
                if validation_result:
                    result["lines_sum"] = validation_result.lines_sum
                    result["diff"] = validation_result.diff if validation_result.diff is not None else "N/A"
                else:
                    result["lines_sum"] = 0.0
                    result["diff"] = "N/A"
                
                results.append(result)
                
            except Exception as e:
                # Handle errors gracefully
                results.append({
                    "filename": uploaded_file.name,
                    "status": "FAILED",
                    "error": str(e),
                    "line_count": 0,
                    "invoice_lines": []
                })
        
        # Update session state
        st.session_state.results.extend(results)
        
        # Clear progress
        progress_bar.empty()
        status_text.empty()
        st.success(f"✅ {len(results)} fakturor processade!")
        
    except Exception as e:
        st.error(f"Fel vid bearbetning: {str(e)}")
    finally:
        # Cleanup temp files (optional - can keep for download)
        pass


def display_results() -> None:
    """Display processing results in a table.
    
    Shows list of processed invoices with status, invoice number, total amount, etc.
    """
    st.header("2. Resultat")
    
    # Create DataFrame from results
    df_data = []
    for result in st.session_state.results:
        # Format total_amount
        total_amount = result.get("total_amount", 0.0)
        total_str = f"{total_amount:,.2f} SEK" if total_amount else "—"
        
        df_data.append({
            "Filnamn": result.get("filename", "Okänt"),
            "Status": result.get("status", "UNKNOWN"),
            "Fakturanummer": result.get("invoice_number", "TBD"),
            "Totalsumma": total_str,
            "Antal rader": result.get("line_count", 0),
            "Företag": result.get("vendor_name", "TBD"),
            "Datum": result.get("invoice_date", "TBD"),
        })
    
    df = pd.DataFrame(df_data)
    
    # Filter by status
    st.subheader("Filtrera resultat")
    status_filter = st.multiselect(
        "Visa endast status:",
        options=["OK", "PARTIAL", "REVIEW", "FAILED"],
        default=["OK", "PARTIAL", "REVIEW", "FAILED"]
    )
    
    if status_filter:
        df_filtered = df[df["Status"].isin(status_filter)]
    else:
        df_filtered = df
    
    # Display table
    st.dataframe(
        df_filtered,
        use_container_width=True,
        hide_index=True
    )
    
    # Summary statistics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Totalt", len(df))
    with col2:
        ok_count = len(df[df["Status"] == "OK"])
        st.metric("✅ OK", ok_count)
    with col3:
        partial_count = len(df[df["Status"] == "PARTIAL"])
        st.metric("⚠️ PARTIAL", partial_count)
    with col4:
        review_count = len(df[df["Status"] == "REVIEW"])
        st.metric("🔍 REVIEW", review_count)
    with col5:
        failed_count = len(df[df["Status"] == "FAILED"])
        st.metric("❌ FAILED", failed_count)


def generate_excel_download() -> None:
    """Generate Excel file for download.
    
    Creates Excel file with all processed invoices using existing export function.
    """
    st.header("3. Ladda ner resultat")
    
    if not st.session_state.results:
        st.warning("Inga resultat att exportera")
        return
    
    # Prepare data for export
    # export_to_excel expects list of dicts with "invoice_lines" and "invoice_metadata"
    export_data = []
    
    for result in st.session_state.results:
        if result.get("status") == "FAILED":
            continue  # Skip failed invoices
        
        invoice_lines = result.get("invoice_lines", [])
        if not invoice_lines:
            continue
        
        # Create metadata dict
        # Handle diff - can be float, None, or "N/A"
        diff_value = result.get("diff", "N/A")
        if diff_value is None or (isinstance(diff_value, str) and diff_value == "N/A"):
            diff_str = "N/A"
        else:
            diff_str = diff_value
        
        metadata = {
            "fakturanummer": result.get("invoice_number", "TBD"),
            "foretag": result.get("vendor_name", "TBD"),
            "fakturadatum": result.get("invoice_date", "TBD"),
            "status": result.get("status", "REVIEW"),
            "lines_sum": result.get("lines_sum", 0.0),
            "diff": diff_str,
            "invoice_number_confidence": result.get("invoice_number_confidence", 0.0),
            "total_confidence": result.get("total_confidence", 0.0),
        }
        
        export_data.append({
            "invoice_lines": invoice_lines,
            "invoice_metadata": metadata
        })
    
    if not export_data:
        st.warning("Inga fakturor att exportera (alla misslyckades)")
        return
    
    # Generate Excel file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        export_to_excel(export_data, tmp_path)
        
        # Read file for download
        with open(tmp_path, "rb") as f:
            excel_data = f.read()
        
        # Download button
        st.download_button(
            label="📥 Ladda ner Excel-fil",
            data=excel_data,
            file_name="fakturor.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        st.error(f"Fel vid Excel-generering: {str(e)}")
    finally:
        # Cleanup
        try:
            Path(tmp_path).unlink()
        except:
            pass


if __name__ == "__main__":
    main()

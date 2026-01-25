"""Verify that Tesseract and all required programs/libraries are available."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

TESSERACT_WIN_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def check_dependencies() -> List[Tuple[str, bool, str]]:
    """Check required dependencies. Returns list of (name, ok, message)."""
    results: List[Tuple[str, bool, str]] = []

    # --- Python packages (core pipeline) ---
    try:
        import pdfplumber
        results.append(("pdfplumber", True, "OK"))
    except ImportError as e:
        results.append(("pdfplumber", False, f"Saknas: {e}"))

    try:
        import fitz  # pymupdf
        results.append(("pymupdf (fitz)", True, "OK"))
    except ImportError as e:
        results.append(("pymupdf (fitz)", False, f"Saknas: {e}"))

    pt: object = None
    try:
        import pytesseract as pt
        results.append(("pytesseract", True, "OK"))
    except ImportError as e:
        results.append(("pytesseract", False, f"Saknas: {e}"))

    try:
        from PIL import Image
        results.append(("Pillow (PIL)", True, "OK"))
    except ImportError as e:
        results.append(("Pillow (PIL)", False, f"Saknas: {e}"))

    try:
        import pandas
        results.append(("pandas", True, "OK"))
    except ImportError as e:
        results.append(("pandas", False, f"Saknas: {e}"))

    try:
        import openpyxl
        results.append(("openpyxl", True, "OK"))
    except ImportError as e:
        results.append(("openpyxl", False, f"Saknas: {e}"))

    try:
        from PySide6 import QtCore
        results.append(("PySide6 (GUI)", True, "OK"))
    except ImportError as e:
        results.append(("PySide6 (GUI)", False, f"Saknas: {e}"))

    # --- Tesseract binary + Swedish language (kräver pytesseract) ---
    if pt is not None:
        if sys.platform == "win32" and TESSERACT_WIN_PATH.is_file():
            pt.pytesseract.tesseract_cmd = str(TESSERACT_WIN_PATH)  # type: ignore[union-attr]
        try:
            version = pt.get_tesseract_version()  # type: ignore[union-attr]
            results.append(("Tesseract (binär)", True, f"OK, version {version}"))
            try:
                langs = pt.get_languages()  # type: ignore[union-attr]
                if "swe" in langs:
                    results.append(("Tesseract (språk swe)", True, "OK"))
                else:
                    results.append(
                        ("Tesseract (språk swe)", False, f"Saknas. Tillgängliga: {', '.join(sorted(langs)[:8])}…")
                    )
            except Exception as e:
                results.append(("Tesseract (språk swe)", False, str(e)))
        except Exception as e:
            err = str(e).split("\n")[0].strip()
            if len(err) > 60:
                err = err[:57] + "..."
            results.append(("Tesseract (binär)", False, err))
    else:
        results.append(("Tesseract (binär)", False, "Kan inte kontrollera (pytesseract saknas)"))

    return results


def run_check(verbose: bool = True) -> bool:
    """Run dependency check, print report, return True if all OK."""
    results = check_dependencies()
    ok_count = sum(1 for _, ok, _ in results if ok)
    all_ok = ok_count == len(results)

    if verbose:
        print("Beroendekontroll (Tesseract + program som pipet behöver)\n")
        for name, ok, msg in results:
            if ok and msg == "OK":
                print(f"  {name}: OK")
            else:
                status = "OK" if ok else "MISSING/FEL"
                print(f"  {name}: {status}  {msg}")
        print()
        if all_ok:
            print("Alla kontrollerade beroenden finns.")
        else:
            print(f"Problem med {len(results) - ok_count} av {len(results)}. Installera saknade med: pip install -e .")
            print("Tesseract: installera till C:\\Program Files\\Tesseract-OCR (välj swe) så hittar appen den.")

    return all_ok


if __name__ == "__main__":
    success = run_check(verbose=True)
    sys.exit(0 if success else 1)

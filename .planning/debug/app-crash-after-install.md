---
status: verified
trigger: "när appen är installerad så får vi fel meddelande och den kraschar"
created: 2025-01-27T00:00:00Z
updated: 2026-01-24T23:02:00Z
---

## Current Focus

hypothesis: (legacy) Streamlit Runtime instance already exists
next_action: N/A – Streamlit-variant borttagen; nuvarande app är PySide6 (run_gui.py)

## Symptoms

expected: App should start successfully when running `python -m streamlit run run_streamlit.py`
actual: App crashes with RuntimeError: "Runtime instance already exists!"
errors: RuntimeError: "Runtime instance already exists!" at streamlit/runtime/runtime.py:182
reproduction: Run `python -m streamlit run run_streamlit.py` - fails immediately
started: After installation (or when trying to run from source)

## Eliminated

## Evidence

- timestamp: 2025-01-27T00:00:00Z
  checked: run_streamlit.py implementation
  found: Uses stcli.main() directly which can cause Runtime instance conflicts
  implication: Need to check for existing runtime before creating new one

- timestamp: 2025-01-27T00:00:00Z
  checked: Web search for RuntimeError solution
  found: Should use runtime.exists() check or avoid bootstrap.run() when already in Streamlit context
  implication: Fix run_streamlit.py to handle existing runtime gracefully

- timestamp: 2025-01-27T00:00:00Z
  checked: Import error when running Streamlit
  found: ImportError: attempted relative import with no known parent package - relative imports (..cli.main) fail when Streamlit runs src/web/app.py directly because it's not treated as part of a package
  implication: Need to change relative imports to absolute imports (src.cli.main) in app.py

## Resolution

root_cause: Three issues: 1) run_streamlit.py uses stcli.main() directly which can create multiple Runtime instances. 2) When Streamlit runs src/web/app.py directly, relative imports (..cli.main) fail because the file is not treated as part of a package - Python doesn't know the parent package context. 3) PYTHONPATH alone doesn't help because the issue is package context, not module path.

fix: 1) Changed run_streamlit.py to use subprocess.run() instead of stcli.main() to avoid Runtime conflicts. 2) Changed all relative imports in src/web/app.py to absolute imports (from ..cli.main to from src.cli.main) so they work when the file is run directly by Streamlit. 3) Set PYTHONPATH and cwd in subprocess for proper environment.

verification: [done 2026-01-24] Se "## Verification (2026-01-24)" nedan.
files_changed: ['run_streamlit.py', 'src/web/app.py', 'src/pipeline/confidence_scoring.py']  # run_streamlit + src/web finns ej i repo längre

## Verification (2026-01-24)

- **Original repro:** `python -m streamlit run run_streamlit.py` – kan inte köras; `run_streamlit.py` och `src/web/` finns inte i kodbasen. Nuvarande app är **PySide6** (`run_gui.py` → `src.ui.app`).
- **Nuvarande app:** `python run_gui.py`
  - **Utan fulla deps** (t.ex. venv utan `pip install -e .`): kraschar med `ImportError: pymupdf (fitz) is required for PDF viewer`. pymupdf finns i pyproject.toml men var inte installerat i venv.
  - **Efter `pip install -e .`:** GUI startar utan fel, processen lever >5 s. **Verifierat OK.**
- **Rekommendation:** Säkerställ `pip install -e .` (eller `pip install .`) före `run_gui.py`. Överväg att nämna detta i README/setup-instructions.

## Additional Fix: Confidence Scoring Too Strict

- timestamp: 2025-01-27T00:00:00Z
  checked: Why no invoices get OK status
  found: Format validation rejects numeric invoice numbers >6 digits, and total amount scoring too strict when mathematical validation fails
  implication: Need to fix format validation to accept numeric invoice numbers (7-12 digits are common), and improve partial scoring for total amount

- timestamp: 2025-01-27T00:00:00Z
  checked: Format validation in confidence_scoring.py
  found: _validate_invoice_number_format rejects candidate.isdigit() and len > 6, but many invoice numbers are 7-12 digit numbers
  implication: Changed to accept numeric invoice numbers, only reject if looks like org number (10 digits starting with 5 or 6)

- timestamp: 2025-01-27T00:00:00Z
  checked: Total amount scoring
  found: When mathematical validation fails, only gets 0.15 instead of 0.35, making it hard to reach 0.95
  implication: Added graduated partial scoring based on difference size (0.25 for diff <= 5 SEK, 0.15 for diff <= 50 SEK)

- timestamp: 2025-01-27T00:00:00Z
  checked: Total amount extraction and validation issues
  found: Amount pattern too restrictive (only matches with 2 decimals), missing keyword variants, mathematical validation too strict (doesn't account for VAT/shipping on larger amounts)
  implication: Improved amount pattern to match amounts with/without decimals and thousand separators, added more keyword patterns, improved validation to use percentage-based tolerance for larger amounts (0.5% for amounts > 1000 SEK)

- timestamp: 2025-01-27T00:00:00Z
  checked: Two totals problem (with/without VAT)
  found: Many invoices have both "exkl. moms" (subtotal) and "inkl. moms" (total) amounts, but system doesn't distinguish between them
  implication: Added keyword classification to identify "with_vat" (att betala / inkl. moms) vs "without_vat" (exkl. moms / delsumma), prioritize "with_vat" totals, boost score for "with_vat" keywords, penalize "without_vat" keywords

- timestamp: 2025-01-27T00:00:00Z
  checked: Many different ways to express total amount
  found: Swedish invoices use many variants: "att betala", "betalas", "belopp att betala", "slutsumma", "fakturabelopp", "netto att betala", "med moms", "moms inkluderad", etc.
  implication: Expanded keyword patterns to include 30+ variants covering common Swedish invoice terminology, organized by priority (with_vat > generic > without_vat)

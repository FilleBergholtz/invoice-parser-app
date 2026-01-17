---
phase: 03-validation
plan: 01
subsystem: validation-core
tags: [dataclasses, validation, status-assignment, hard-gates]
---

# Dependency graph
requires:
  - phase: 02 (Header + Wrap)
    provides: InvoiceHeader with confidence scores, InvoiceLine objects
provides:
  - ValidationResult data model with status, validation values, errors, warnings
  - validate_invoice() function with status assignment logic
  - calculate_validation_values() helper for mathematical validation
affects: [03-02, 03-03, 03-04 - all depend on ValidationResult and validation logic]

# Tech tracking
tech-stack:
  added: []
  patterns: [Dataclass models with validation, status assignment with hard gates, mathematical validation reuse]

key-files:
  created:
    - src/models/validation_result.py
    - src/pipeline/validation.py
    - tests/test_validation.py
  modified: []

key-decisions:
  - "Reused Phase 2 validation function (validate_total_against_line_items) for mathematical validation"
  - "Status assignment: OK (hard gate pass + diff ≤ ±1 SEK), PARTIAL (hard gate pass + diff > ±1 SEK), REVIEW (hard gate fail)"
  - "Signed difference (diff = total_amount - lines_sum) instead of absolute for Excel reporting"

patterns-established:
  - "Validation pattern: calculate values → check hard gates → assign status → generate errors/warnings"
  - "Edge case handling: None values, empty lists, partial confidence all result in REVIEW status"

# Metrics
duration: ~20min
completed: 2026-01-17
---

# Phase 03: Validation - Plan 01 Summary

**ValidationResult model and status assignment logic implemented**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-01-17
- **Completed:** 2026-01-17
- **Tasks:** 4 completed
- **Files modified:** 3 created

## Accomplishments

- ValidationResult dataclass created with all required fields (status, lines_sum, diff, tolerance, hard_gate_passed, confidence scores, errors, warnings)
- calculate_validation_values() helper implemented (reuses Phase 2 validation function)
- validate_invoice() function implemented with complete status assignment logic from 03-CONTEXT.md
- All edge cases handled (None values, empty lists, partial confidence → REVIEW)
- Comprehensive unit tests created (16 tests, all passing)

## Task Commits

### Task 1: ValidationResult Model ✓
- Created `src/models/validation_result.py` with ValidationResult dataclass
- Implemented __post_init__ validation (status must be OK/PARTIAL/REVIEW, lines_sum >= 0, confidence 0.0-1.0)
- Default values: tolerance=1.0, errors=[], warnings=[]

### Task 2: calculate_validation_values Helper ✓
- Created helper function in `src/pipeline/validation.py`
- Calculates lines_sum, diff (signed), validation_passed
- Reuses validate_total_against_line_items() from Phase 2

### Task 3: validate_invoice Function ✓
- Implemented complete status assignment logic:
  - Hard gate check (both confidences >= 0.95)
  - Mathematical validation (diff <= ±1 SEK)
  - Status: OK/PARTIAL/REVIEW based on conditions
  - Error/warning generation for REVIEW and PARTIAL statuses

### Task 4: Unit Tests ✓
- Created comprehensive test suite in `tests/test_validation.py`
- 16 tests covering:
  - ValidationResult model validation
  - calculate_validation_values() scenarios
  - validate_invoice() status assignment (OK, PARTIAL, REVIEW)
  - Edge cases (None values, empty lists, partial confidence)

## Key Implementation Details

**Status Assignment Logic:**
1. Check hard gate: `invoice_header.meets_hard_gate()`
2. Calculate validation values: `lines_sum`, `diff`, `validation_passed`
3. Assign status:
   - Hard gate fail → REVIEW
   - total_amount None → REVIEW
   - No line_items → REVIEW
   - Hard gate pass + diff <= ±1 SEK → OK
   - Hard gate pass + diff > ±1 SEK → PARTIAL

**Mathematical Validation:**
- Reuses `validate_total_against_line_items()` from Phase 2 (confidence_scoring.py)
- Calculates signed difference: `diff = total_amount - lines_sum` (can be negative)
- Tolerance: ±1.0 SEK (default)

**Edge Cases:**
- invoice_number_confidence >= 0.95 but total_confidence < 0.95 → REVIEW
- total_confidence >= 0.95 but invoice_number_confidence < 0.95 → REVIEW
- No invoice_lines → REVIEW (cannot validate)
- total_amount None → REVIEW (cannot validate)

## Verification

- ✅ All unit tests pass (16/16)
- ✅ ValidationResult model validates correctly
- ✅ Status assignment logic matches 03-CONTEXT.md
- ✅ Hard gates implemented (both confidences >= 0.95)
- ✅ Mathematical validation calculates lines_sum and diff correctly
- ✅ All edge cases handled
- ✅ Errors and warnings generated appropriately

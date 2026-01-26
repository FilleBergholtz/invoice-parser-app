---
phase: 17-ai-policy-fallback-only
plan: 17-01
subsystem: pipeline
tags: [ai-policy, fallback, edi, validation, ocr]

# Dependency graph
requires:
  - phase: Phase 16
    provides: text-layer routing decisions and compare-extraction flow
provides:
  - ai_policy defaults in profile configuration
  - central AI policy evaluation with EDI-like signals
  - deterministic fallback gating before AI usage
  - policy details preserved in compare and normal paths
  - unit tests for policy and retry fallback
affects: [phase-17, phase-18, phase-19]

# Tech tracking
tech-stack:
  added: []
  patterns: [ai-policy gating based on validation + edi signals]

key-files:
  created: [tests/test_ai_policy.py, tests/test_retry_extraction.py]
  modified: [configs/profiles/default.yaml, src/config/profile_loader.py, src/ai/fallback.py, src/pipeline/ocr_routing.py, src/pipeline/retry_extraction.py, src/pipeline/validation.py, src/pipeline/footer_extractor.py, src/cli/main.py]

key-decisions:
  - "AI policy decisions are stored under extraction_detail.ai_policy for traceability."
  - "Deterministic retry fallback runs before any AI fallback is allowed."

patterns-established:
  - "EDI-like detection combines text-layer usage, anchors, and table pattern hits."
  - "Compare and normal extraction paths preserve identical AI policy metadata."

# Metrics
duration: 41min
completed: 2026-01-26
---

# Phase 17 Plan 01: AI-policy (fallback only) Summary

**AI fallback is now gated by centralized policy with EDI-like heuristics and deterministic retry before AI.**

## Performance

- **Duration:** 41 min
- **Started:** 2026-01-26T17:30:00Z
- **Completed:** 2026-01-26T18:11:24Z
- **Tasks:** 5
- **Files modified:** 10

## Accomplishments
- Added ai_policy configuration defaults and profile exposure
- Implemented centralized AI policy evaluation with EDI signal detection
- Integrated deterministic fallback gating and preserved policy metadata in results

## Task Commits

Each task was committed atomically:

1. **Task 1: Konfigurera ai_policy i standardprofil** - `e159bcc` (feat)
2. **Task 2: Implementera central AI-policyfunktion** - `f754e30` (feat)
3. **Task 3: Koppla gating efter deterministisk extraktion** - `5e68001` (feat)
4. **Task 4: Samma policy i compare-path och normal-path** - `66e8507` (fix)
5. **Task 5: Tester for AI-policy och regression** - `3f719e4` (test)

**Plan metadata:** pending

_Note: TDD tasks may have multiple commits (test → feat → refactor)_

## Files Created/Modified
- `configs/profiles/default.yaml` - adds ai_policy defaults for EDI gating
- `src/config/profile_loader.py` - exposes ai_policy on profile config
- `src/ai/fallback.py` - central AI policy evaluation helpers
- `src/pipeline/ocr_routing.py` - EDI signal detection from anchors and patterns
- `src/pipeline/retry_extraction.py` - deterministic fallback helper
- `src/pipeline/validation.py` - validation_passed helper
- `src/pipeline/footer_extractor.py` - allow_ai flag for AI fallback
- `src/cli/main.py` - policy gating and result metadata preservation
- `tests/test_ai_policy.py` - policy unit tests
- `tests/test_retry_extraction.py` - deterministic fallback tests

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
AI-policy gating is in place with traceable reason flags; compare and normal paths aligned.

---
*Phase: 17-ai-policy-fallback-only*
*Completed: 2026-01-26*

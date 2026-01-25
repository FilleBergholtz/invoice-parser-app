# 10-01: Document AI fallback — Summary

**Done:** 2026-01-24

## Objective

Document current AI fallback behaviour so we have a single source of truth for trigger, context sent to AI, prompts, config, UI, and verification. No code changes — documentation only.

## Completed tasks

1. **Create 10-CONTEXT.md with AI fallback documentation**
   - Added `.planning/phases/10-ai-fallback-fixes/10-CONTEXT.md` with eight sections:
     - Phase boundary (goal of Phase 10, role of this doc)
     - Trigger (get_ai_enabled, get_ai_key, no candidates or best heuristic < 0.95)
     - Context sent to AI (footer_text, line_items_sum, up to 10 candidates, page_context), including call chain from CLI → extract_total_amount → _try_ai_fallback → extract_total_with_ai
     - Prompts (location in src/ai/providers.py, OpenAIProvider/ClaudeProvider extract_total_amount)
     - Config (AI_ENABLED, AI_PROVIDER, AI_MODEL, AI_KEY; get_ai_config_path, load_ai_config, set_ai_config; get_ai_enabled, get_ai_key, get_ai_provider, get_ai_model)
     - UI (AISettingsDialog, “Aktivera AI-fallback” checkbox, status “Aktiverad”/“Inaktiverad”, persistence)
     - Error handling and validation (return None on errors; implausible rule; ±1 SEK validation; confidence boost +0.1 / +0.2; selection vs heuristic)
     - Verification (brief pointer; full steps in 10-VERIFICATION.md per plan 10-02)

## Files changed

- `.planning/phases/10-ai-fallback-fixes/10-CONTEXT.md` — created (documentation only).

## Acceptance

- 10-CONTEXT.md exists and describes trigger, context, prompts location, config, UI, errors/validation, and a brief verification pointer.
- Content is consistent with footer_extractor, fallback, providers, config, and ai_settings_dialog.

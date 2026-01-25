# Phase 10: AI Fallback Fixes and Verification — Context

**Gathered:** 2026-01-24  
**Status:** Documentation of current AI fallback behaviour (“what we have today”)

---

## 1. Phase boundary

Phase 10 goal: document what we have fixed/improved regarding AI fallback and ensure it works well in practice.

This document is the single source of truth for current AI fallback behaviour. Detailed verification steps are in `10-VERIFICATION.md`.

---

## 2. Trigger

AI fallback runs when **all** of the following hold:

- `get_ai_enabled()` is true (env `AI_ENABLED` or saved config `enabled`).
- `get_ai_key()` returns a non-empty value (env `AI_KEY` or saved config `api_key`).
- **Either:**
  - **(a)** There are **no** heuristic candidates (`scored_candidates` is empty), or  
  - **(b)** The best heuristic score is **&lt; 0.95** (`top_heuristic_score < 0.95`).

If there are candidates and the best score is ≥ 0.95, AI is skipped (“AI fallback skipped: confidence >= 0.95”).

**Code reference:** `src/pipeline/footer_extractor.py`, `extract_total_amount`, Step 5 (around lines 611–678). Uses `get_ai_enabled()`, `get_ai_key()`, and `scored_candidates` / `top_heuristic_score`.

---

## 3. Context sent to AI

The AI receives:

| Input | Source | Description |
|-------|--------|-------------|
| `footer_text` | Footer segment | `footer_segment.raw_text` or `" ".join(row.text for row in footer_segment.rows)` |
| `line_items_sum` | Sum of `line.total_amount` | Used for validation and “implausible” check |
| `candidates` | Heuristic candidates | Up to 10 entries `[{amount, keyword_type}]` from `scored_candidates` when available |
| `page_context` | Last page only | Full page text (header + items + footer) for the totals page |

**Call chain:**

1. CLI builds `page_context_for_ai = _build_page_context_for_ai(last_page_segments)` in `src/cli/main.py` (function around line 76). It orders segments by `y_min`, skips garbled rows (`_is_likely_garbled`), and joins with `"--- {segment_type} ---"` headers.
2. CLI calls `extract_total_amount(..., page_context_for_ai=page_context_for_ai)`.
3. `extract_total_amount` calls `_try_ai_fallback(footer_segment, line_items, invoice_header, candidates=scored_candidates[:10], page_context=page_context_for_ai)`.
4. `_try_ai_fallback` (footer_extractor) calls `extract_total_with_ai(footer_text, line_items_sum, candidates=cand, page_context=page_context)` from `src/ai/fallback.py`.
5. `AIFallback.extract` passes the same inputs to `self.provider.extract_total_amount(...)`.

So: **footer, line_items_sum, up to 10 candidates, and full last-page context** are sent to the provider when the trigger conditions are met.

---

## 4. Prompts

Prompts are implemented inside the provider’s `extract_total_amount` in **`src/ai/providers.py`**:

- **OpenAIProvider:** uses `_build_prompt(footer_text, line_items_sum, candidates=..., page_context=...)` and sends a single user message. Response is parsed via `response_format=AITotalResponse` (Pydantic).
- **ClaudeProvider:** builds a prompt (system/user or user-only) that includes footer, optional page_context, optional candidates, and line_items_sum; response is parsed from JSON in the reply.

Prompt content is in those methods; it includes footer text, optional full page context, optional candidate list, and line-items sum for validation. Roles are effectively system/user (or user-only) depending on provider.

---

## 5. Config

**Environment variables:**

- `AI_ENABLED` — `'true'` (case-insensitive) to enable. If unset, `get_ai_enabled()` falls back to saved config.
- `AI_PROVIDER` — `"openai"` or `"claude"`, default `"openai"`.
- `AI_MODEL` — model name; if unset, provider-specific default is used (e.g. `gpt-4-turbo-preview`, `claude-3-opus-20240229`).
- `AI_KEY` — API key. If unset, `get_ai_key()` falls back to saved config.

**File-backed config:**

- Path: `get_ai_config_path()` (in `src/config.py`); typically under user app-data / config directory.
- Load: `load_ai_config()` returns a dict with `enabled`, `provider`, `model`, `api_key`.
- Save: `set_ai_config(enabled, provider, model, api_key)` writes the file and can update env.

**Functions:** `get_ai_enabled()`, `get_ai_key()`, `get_ai_provider()`, `get_ai_model()` (all in `src/config.py`).

---

## 6. UI

**`AISettingsDialog`** (`src/ui/views/ai_settings_dialog.py`):

- Window title: “AI-inställningar”.
- Status line: shows provider, model, and “Aktiverad” / “Inaktiverad” (`_status_text()` from `load_ai_config()`).
- **“Aktivera AI-fallback”** checkbox: toggles enabled state. Tooltip: “AI används när confidence < 95 %.”
- Provider (OpenAI/Claude), model (editable combo), API key field.
- Persistence: save uses `set_ai_config(...)`; load uses `load_ai_config()`.

So the UI both shows and sets the enable/disable state that `get_ai_enabled()` reflects.

---

## 7. Error handling and validation

**Errors:**  
If the AI call fails (timeout, API error, invalid response, network error), the provider or `AIFallback.extract` returns `None`. The footer extractor then continues with the best heuristic result (or no total if there were no candidates). Logs use messages like “AI fallback failed” / “AI fallback skipped: no result”. The pipeline does not fail.

**Validation (in `src/ai/fallback.py`):**

- Compare AI `total_amount` to `line_items_sum` when both exist.
- **Implausible rule:** if `line_items_sum` is clearly wrong (e.g. diff > max(500, 0.15×ai_total), or line_items_sum &lt; 100 and ai_total &gt; 1000), we set `validation_passed = True` and trust the AI total.
- Otherwise: `validation_passed = (abs(ai_total - line_items_sum) <= 1.0)` (±1 SEK).
- **Confidence boost:** when `validation_passed` and not implausible: base boost +0.1; if `abs(ai_total - line_items_sum) < 0.01` add another +0.1 (max +0.2). Final confidence capped at 1.0.

**Use of AI result in footer_extractor:**  
AI is used when `ai_confidence > top_heuristic_score` or when `validation_passed` and confidence is within 0.05 of heuristic. Otherwise the heuristic result is kept.

---

## 8. Verification (brief)

To verify AI fallback: enable AI (UI “Aktivera AI-fallback” or env `AI_ENABLED=true`), set an API key, then run on a PDF that yields low heuristic confidence or no candidates, and check logs for “AI fallback …” (e.g. “AI fallback succeeded”, “AI fallback used: no heuristic candidates”) and that the final total is correct.

For full verification steps (automated tests, manual run, log checks), see **`10-VERIFICATION.md`**.

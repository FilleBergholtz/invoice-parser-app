# Phase 10: AI Fallback — Verification

How to verify that AI fallback works in practice. Config and trigger behaviour are described in `10-CONTEXT.md`.

---

## 1. Prerequisites

- **AI enabled:** via desktop UI “AI-inställningar” → “Aktivera AI-fallback”, or set `AI_ENABLED=true` in the environment.
- **API key set:** in the same dialog or via `AI_KEY`.
- **Provider/model:** as in `10-CONTEXT.md` (e.g. OpenAI/Claude, model from config or env).

---

## 2. Automated checks

Run:

```bash
pytest tests/test_footer_extractor.py tests/test_ai_client.py -v
```

**Note:** These tests disable AI (e.g. monkeypatch `get_ai_enabled` and calibration/learning) so they exercise the heuristic path in a stable way. Passing them ensures the footer extractor and AI client are not broken. **AI-on behaviour is not covered by these tests** and is verified manually or via the steps in section 3.

**Senast kört:** 2026-01-25 — `pytest tests/test_footer_extractor.py tests/test_ai_client.py -v` → **16 passed, 1 skipped.**

---

## 3. Manual verification

1. Enable AI (UI or `AI_ENABLED=true`) and set a valid API key.
2. Run the engine (CLI or GUI) on **one PDF** that typically gives low heuristic confidence or few candidates (e.g. unusual layout, scanned page, or known “hard” invoice).
3. In the run logs, look for lines containing **“AI fallback”**, for example:
   - `AI fallback succeeded: confidence …`
   - `AI fallback used: no heuristic candidates, AI extracted total`
   - `AI fallback skipped: …` (when AI is not used, for comparison).
4. Confirm the exported total for that invoice is correct and, if relevant, that it improved compared to heuristic-only.

---

## 4. Optional

If you have a test PDF or fixture that reliably triggers AI when enabled (e.g. low-confidence footer or no heuristic candidates), mention it here for quick reuse. The project’s `tests/fixtures/pdfs/` can hold such files; document the filename and why it triggers AI.

# 14-05: AI vision + retry — Summary

**Done:** 2026-01-25

## Objective

Extend the AI layer for vision-based extraction and one retry on invalid JSON. Per 14-RESEARCH R3 (image format/size limits) and R4 (AI_JSON_RETRY_COUNT=1): optional image input, R3 enforced, and at most one retry with stricter instruction when validation/parsing fails.

## Completed tasks

1. **Vision input and R3 limits** (`src/ai/providers.py`)
   - `_prepare_vision_image(image_path: str) -> (bytes, mime)`: loads image, allows PNG/JPEG only, scales so longest side ≤ 4096 px, keeps size ≤ 20 MB (re‑encode as JPEG if needed). Constants: `VISION_MAX_PIXELS_LONGEST_SIDE = 4096`, `VISION_MAX_FILE_BYTES = 20*1024*1024`, `AI_JSON_RETRY_COUNT = 1`.
   - `AIProvider.extract_total_amount(..., image_path=None, strict_json_instruction=False)`: new optional params; when `image_path` is set, vision is used and R3 is applied before the API call.

2. **OpenAI vision**
   - If `image_path` is set, uses `client.chat.completions.create` with user content `[{ "type": "text", "text": prompt }, { "type": "image_url", "image_url": { "url": "data:{mime};base64,..." } }]`. Response is parsed via `_parse_fallback_response` (supports JSON and number extraction).

3. **Claude vision**
   - If `image_path` is set, user content is `[{ "type": "image", "source": { "type": "base64", "media_type", "data" } }, { "type": "text", "text": prompt }]`. Same response shape and parsing as text-only.

4. **Strict JSON instruction**
   - `_build_prompt(..., strict_json_instruction=False)` in both providers: when True, appends an instruction to return only valid JSON matching the schema, no extra text.

5. **1-retry in fallback** (`src/ai/fallback.py`)
   - `AIFallback.extract(..., image_path=None)` and `extract_total_with_ai(..., image_path=None)`.
   - Up to `AI_JSON_RETRY_COUNT + 1` attempts (i.e. 2 calls): first normal, then if result is missing or `validate_response` fails, one retry with `strict_json_instruction=True`. Exceptions on the first attempt also trigger one retry.

## Files changed

- `src/ai/providers.py` — R3 constants and `_prepare_vision_image`; `image_path` and `strict_json_instruction` on `extract_total_amount`; OpenAI/Claude vision paths; stricter prompt when `strict_json_instruction` is True; OpenAI `_parse_fallback_response` tries JSON before number extraction.
- `src/ai/fallback.py` — `image_path` on `extract()` and `extract_total_with_ai()`; retry loop with at most one retry using `strict_json_instruction=True`.

## Verification

- `extract_total_amount` can be called with `image_path`; R3 is applied and vision API is used; response shape is unchanged.
- On invalid or missing response, fallback performs at most one extra call with stricter instructions, then success or failure.
- R3 limits (4096 px, 20 MB, PNG/JPEG) are enforced in `_prepare_vision_image` before sending to the API.

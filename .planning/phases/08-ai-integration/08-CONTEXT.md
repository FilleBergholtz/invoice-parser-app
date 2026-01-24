# Phase 8: AI Integration - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate AI as fallback when confidence < 0.95 to improve total amount extraction for edge cases. Use structured outputs (Pydantic), handle errors gracefully, and abstract AI provider.

**Core Problem:** Some invoices have unusual layouts or patterns that heuristics can't handle well. AI can help extract total amount when confidence is low.

**Goal:** System uses AI fallback when confidence < 0.95, improving extraction for edge cases while keeping AI usage <20% of invoices.

</domain>

<decisions>
## Implementation Decisions

### 1. AI Fallback Pattern

**Approach:**
- Activate AI only when total_confidence < 0.95 (strict threshold)
- Try heuristics first, then AI if confidence low
- Don't use AI for high-confidence cases (avoid over-reliance)

**Integration Point:**
- In `extract_total_amount()` after heuristic extraction
- Check confidence, if < 0.95, call AI fallback
- Use AI result if validation passes

### 2. AI Provider Abstraction

**Approach:**
- Abstract AI provider (OpenAI/Claude)
- Use existing AIClient but enhance for direct API calls
- Support structured outputs (Pydantic models)

**Provider Support:**
- OpenAI (GPT-4) via API
- Claude (Anthropic) via API
- Configurable via environment variables

### 3. Structured Outputs

**Approach:**
- Use Pydantic models for request/response
- Validate AI responses before using
- Handle invalid responses gracefully

**Response Schema:**
- total_amount: float
- confidence: float (0.0-1.0)
- reasoning: Optional[str] (for debugging)
- validation_passed: bool

### 4. Error Handling

**Approach:**
- Handle timeouts (30s default)
- Handle API errors (rate limits, auth errors)
- Handle invalid responses (malformed JSON, missing fields)
- Log errors but don't break extraction (fallback to heuristic result)

**Graceful Degradation:**
- If AI fails, use heuristic result (even if low confidence)
- Mark as REVIEW if confidence still < 0.95
- Don't fail entire extraction

### 5. Confidence Boosting

**Approach:**
- If AI validation succeeds (matches line items sum), boost confidence
- Boost amount: +0.1 to +0.2 depending on validation quality
- Cap at 1.0
- Only boost if AI result is validated

</decisions>

<current_state>
## Current Implementation

**Files:**
- `src/ai/client.py` - AIClient class (HTTP client for AI service)
- `src/ai/schemas.py` - AIInvoiceRequest, AIInvoiceResponse schemas
- `src/config.py` - get_ai_enabled(), get_ai_endpoint(), get_ai_key()

**Current Features:**
- AI client with HTTP requests
- Request/response schemas
- Error handling (AIConnectionError, AIAPIError)
- Health check

**Missing:**
- Direct OpenAI/Claude API integration
- Structured outputs with Pydantic
- AI fallback in footer extractor
- Confidence boosting from AI validation
- Provider abstraction

</current_state>

<requirements>
## Phase Requirements

- **AI-01**: System activates AI fallback when total amount confidence < 0.95
- **AI-02**: System uses AI (OpenAI/Claude) to extract total amount when heuristics fail
- **AI-03**: System uses structured outputs (Pydantic) for AI responses
- **AI-04**: System handles AI errors gracefully (timeouts, API errors, invalid responses)
- **AI-05**: System validates AI responses before using them
- **AI-06**: System can boost confidence score if AI validation succeeds
- **AI-07**: System abstracts AI provider (can switch between OpenAI/Claude)

</requirements>

<research>
## Research References

- `.planning/research/SUMMARY.md`: AI fallback pattern, structured outputs, error handling
- `.planning/research/ARCHITECTURE.md`: Fallback Chain pattern, AI Fallback component
- `.planning/research/PITFALLS.md`: Over-reliance on AI (avoid with strict fallback pattern)

</research>

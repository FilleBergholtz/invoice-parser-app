# Phase 17 Verification — AI-policy (fallback only)

status: verified  
date: 2026-01-26

## Must-haves
- AI-01 (AI endast fallback när deterministiska mönster saknas): uppfyllt (policy-gating efter deterministisk extraktion + fallback, AI endast när allow_ai=true).
- AI-02 (EDI-lik text-layer ska vara deterministisk, AI ej normalväg): uppfyllt (EDI-signalering blockerar AI om policy kräver).
- Samma AI-policy i normal-path och compare-path: uppfyllt (samma evaluate_ai_policy + edi_signals i båda flöden).
- Reason flags sparas i resultat: uppfyllt (`extraction_detail.ai_policy` skrivs i compare-path och normal-path).

## Evidens
- AI-policy konfigureras i standardprofilen (allow_ai_for_edi=false, anchors, tabellmönster).
```131:149:configs/profiles/default.yaml
ai_policy:
  allow_ai_for_edi: false
  force_review_on_edi_fail: true
  min_edi_signals: 2
  edi_anchor_rules:
    required:
      - "Faktura\\s"
    extra:
      - "Sida\\s*\\d+\\s*/\\s*\\d+"
      - "Bankgiro"
  edi_table_patterns:
    - "\\bArtikel\\b"
    - "\\bArt\\.nr\\b"
    - "\\bAntal\\b"
    - "\\bQty\\b"
    - "\\bPris\\b"
    - "\\bBelopp\\b"
    - "\\bAmount\\b"
```
- Central AI-policyfunktion med reason_flags och EDI-signalbedömning finns.
```59:125:src/ai/fallback.py
def evaluate_ai_policy(
    extraction_source: Optional[str],
    text_quality: Optional[float],
    validation_result: Optional[ValidationResult],
    edi_signals: Optional[Dict[str, Any]] = None,
    policy_config: Optional[Dict[str, Any]] = None,
    fallback_attempted: bool = False,
    fallback_passed: Optional[bool] = None,
) -> Dict[str, Any]:
    """Evaluate AI policy gating decision for fallback usage."""
    policy = policy_config or get_ai_policy_config()
    allow_ai_for_edi = bool(policy.get("allow_ai_for_edi", False))
    force_review_on_edi_fail = bool(policy.get("force_review_on_edi_fail", True))
    ...
    return {
        "allow_ai": allow_ai,
        "reason_flags": reason_flags,
        "policy_version": AI_POLICY_VERSION,
        "edi_like": edi_like,
        "edi_signals": signals,
    }
```
- Normal-path kör deterministisk fallback före AI och gating styrs av policy.
```325:399:src/cli/main.py
            deterministic_validation_result = validate_invoice(invoice_header, all_invoice_lines)
            if not validation_passed(deterministic_validation_result):
                fallback_attempted = True
                ...
                run_deterministic_fallback(
                    extract_total_deterministic,
                    target_confidence=0.90,
                    max_attempts=3,
                    progress_callback=fallback_progress,
                )
                deterministic_validation_result = validate_invoice(invoice_header, all_invoice_lines)
                fallback_passed = validation_passed(deterministic_validation_result)

            policy_config = get_ai_policy_config()
            edi_signals = evaluate_edi_signals(
                text=page_context_for_ai,
                text_layer_used=text_layer_used,
                text_quality=text_quality,
                anchor_rules=policy_config.get("edi_anchor_rules"),
                table_patterns=policy_config.get("edi_table_patterns"),
                min_signals=int(policy_config.get("min_edi_signals", 2) or 2),
                min_text_quality=float(policy_config.get("min_text_quality", 0.5) or 0.5),
            )
            ai_policy_decision = evaluate_ai_policy(
                extraction_source=extraction_path,
                text_quality=text_quality,
                validation_result=deterministic_validation_result,
                edi_signals=edi_signals,
                policy_config=policy_config,
                fallback_attempted=fallback_attempted,
                fallback_passed=fallback_passed,
            )

            if ai_policy_decision.get("allow_ai") and (
                invoice_header.total_amount is None or invoice_header.total_confidence < 0.95
            ):
                extract_total_amount(
                    footer_segment, all_invoice_lines, invoice_header,
                    strategy=None, rows_above_footer=rows_above_footer,
                    page_context_for_ai=page_context_for_ai,
                    allow_ai=True,
                )
```
- Compare-path använder samma policy-gating och sparar ai_policy i extraction_detail.
```721:955:src/cli/main.py
            deterministic_validation_result = validate_invoice(invoice_header, all_invoice_lines)
            if not validation_passed(deterministic_validation_result):
                fallback_attempted = True
                ...
                run_deterministic_fallback(
                    extract_total_deterministic,
                    target_confidence=0.90,
                    max_attempts=3,
                    progress_callback=fallback_progress,
                )
                deterministic_validation_result = validate_invoice(invoice_header, all_invoice_lines)
                fallback_passed = validation_passed(deterministic_validation_result)

            policy_config = get_ai_policy_config()
            edi_signals = evaluate_edi_signals(
                text=page_context_for_ai,
                text_layer_used=text_layer_used,
                text_quality=text_quality,
                anchor_rules=policy_config.get("edi_anchor_rules"),
                table_patterns=policy_config.get("edi_table_patterns"),
                min_signals=int(policy_config.get("min_edi_signals", 2) or 2),
                min_text_quality=float(policy_config.get("min_text_quality", 0.5) or 0.5),
            )
            ai_policy_decision = evaluate_ai_policy(
                extraction_source=extraction_path,
                text_quality=text_quality,
                validation_result=deterministic_validation_result,
                edi_signals=edi_signals,
                policy_config=policy_config,
                fallback_attempted=fallback_attempted,
                fallback_passed=fallback_passed,
            )

            if ai_policy_decision.get("allow_ai") and (
                invoice_header.total_amount is None or invoice_header.total_confidence < 0.95
            ):
                extract_total_amount(
                    footer_segment, all_invoice_lines, invoice_header,
                    strategy=None, rows_above_footer=rows_above_footer,
                    page_context_for_ai=page_context_for_ai,
                    allow_ai=True,
                )
...
        if result.extraction_detail is None:
            result.extraction_detail = {"method_used": extraction_path}
        if ai_policy_decision is not None:
            result.extraction_detail["ai_policy"] = ai_policy_decision
```
- Enhetstester täcker policybeslut (EDI-lik OK → AI blockeras, icke-EDI → AI tillåts).
```1:116:tests/test_ai_policy.py
from src.ai.fallback import evaluate_ai_policy
from src.models.validation_result import ValidationResult
from src.pipeline.ocr_routing import evaluate_edi_signals
...
def test_edi_like_validation_ok_blocks_ai():
    ...
    decision = evaluate_ai_policy(
        extraction_source="pdfplumber",
        text_quality=0.8,
        validation_result=_ok_validation(),
        edi_signals=edi_signals,
        policy_config=_policy_config(),
        fallback_attempted=False,
        fallback_passed=None,
    )
    assert decision["allow_ai"] is False
```

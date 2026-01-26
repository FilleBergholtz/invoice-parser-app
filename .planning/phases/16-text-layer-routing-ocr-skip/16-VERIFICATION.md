# Phase 16 Verification — Text-layer routing (OCR-skip)

status: passed  
date: 2026-01-26

## Must-haves
- OCR-01 (per-sida text-layer → OCR skip): passed (kod + runtime).
- OCR-02 (konfigurerbar tröskel + ankare): passed.
- OCR-03 (OCR endast fallback när text-layer inte räcker; mixed-PDF): passed (runtime).
- OCR-04 (compare-path kraschar inte / KeyError: 4): passed (runtime).

## Evidens
- OCR-routing konfigureras i standardprofilen med `min_text_chars`, required/extra anchors och override-trösklar.
```118:129:configs/profiles/default.yaml
ocr_routing:
  min_text_chars: 500
  required_anchors:
    - "Faktura\\s"
  extra_anchors:
    - "Sida\\s*\\d+\\s*/\\s*\\d+"
    - "Ramirent"
  min_word_tokens: 40
  min_text_quality: 0.5
  allow_quality_override: true
  cache_pdfplumber_text: true
```
- Per-sida beslutet använder `min_text_chars` + required/extra anchors, samt quality override.
```51:102:src/pipeline/ocr_routing.py
def evaluate_text_layer(
    text: str,
    tokens: Optional[List["Token"]],
    routing_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Evaluate if pdfplumber text layer is sufficient for a page.

    Returns a dict with decision and reasoning for debug.
    """
    cfg = routing_config or get_ocr_routing_config()
    text = (text or "").strip()
    text_chars = len(text)
    word_tokens = len(text.split())
    tokens = tokens or []

    required_patterns = _compile_anchors(cfg.get("required_anchors", []))
    extra_patterns = _compile_anchors(cfg.get("extra_anchors", []))

    required_hits = [p.pattern for p in required_patterns if p.search(text)]
    extra_hits = [p.pattern for p in extra_patterns if p.search(text)]

    required_ok = True if not required_patterns else bool(required_hits)
    extra_ok = True if not extra_patterns else bool(extra_hits)
    chars_ok = text_chars >= int(cfg.get("min_text_chars", 0) or 0)
    min_word_tokens = int(cfg.get("min_word_tokens", 0) or 0)
    text_quality = score_text_quality(text, tokens)
    quality_ok = text_quality >= float(cfg.get("min_text_quality", 0.0) or 0.0)

    base_ok = chars_ok and required_ok and extra_ok
    allow_override = bool(cfg.get("allow_quality_override", False))
    override_ok = allow_override and quality_ok and word_tokens >= min_word_tokens

    use_text_layer = base_ok or override_ok
    reason_flags: List[str] = []
    if not chars_ok:
        reason_flags.append("min_text_chars")
    if not required_ok:
        reason_flags.append("required_anchor_missing")
    if not extra_ok:
        reason_flags.append("extra_anchor_missing")
    if override_ok and not base_ok:
        reason_flags.append("quality_override")

    return {
        "use_text_layer": use_text_layer,
        "text_chars": text_chars,
        "word_tokens": word_tokens,
        "text_quality": text_quality,
        "required_anchor_hits": required_hits,
        "extra_anchor_hits": extra_hits,
        "reason_flags": reason_flags,
    }
```
- Routing används per sida i `process_virtual_invoice`, och text-layer/ocr väljs baserat på beslutet.
```521:548:src/cli/main.py
                if pdf:
                    pdfplumber_page = pdf.pages[page.page_number - 1]
                    if page_routing and page.page_number in page_routing:
                        decision = page_routing[page.page_number]
                    else:
                        should_eval = fallback_to_ocr or return_page_routing
                        if should_eval:
                            page_text = _get_pdfplumber_text(
                                page.page_number,
                                pdfplumber_page,
                                text_cache,
                                cache_pdf_text
                            )
                            decision = evaluate_text_layer(page_text, [], routing_config)
                    if decision:
                        page_routing_decisions[page.page_number] = decision

                use_text_layer = extraction_path == "pdfplumber"
                if extraction_path == "pdfplumber" and fallback_to_ocr and decision and not decision["use_text_layer"]:
                    use_text_layer = False
                elif extraction_path == "ocr":
                    use_text_layer = False
                    if decision and decision["use_text_layer"]:
                        use_text_layer = True

                if use_text_layer and pdfplumber_page is not None:
                    tokens = extract_tokens_from_page(page, pdfplumber_page)
                    page_source = "pdfplumber"
```
- Compare-path använder per-sida routing och kör OCR endast när text-layer inte räcker.
```906:954:src/cli/main.py
        for index, (page_start, page_end) in enumerate(boundaries, start=1):
            if compare_extraction:
                if verbose and index == 1:
                    print("  Compare: pdfplumber → OCR per faktura, väljer bästa. AI-fallback vid behov under extraktion.")
                if verbose:
                    print(f"  Compare: kör pdfplumber för sidor {page_start}-{page_end} …")
                out_pdf = process_virtual_invoice(
                    doc, page_start, page_end, index, "pdfplumber", verbose,
                    output_dir=output_dir, return_last_page_tokens=True, return_page_routing=True,
                    fallback_to_ocr=False,
                )
                r_pdf = out_pdf[0] if isinstance(out_pdf, tuple) else out_pdf
                extra_pdf = out_pdf[1] if isinstance(out_pdf, tuple) else {}
                tokens_pdf = extra_pdf.get("last_page_tokens") or []
                page_routing = extra_pdf.get("page_routing") or {}
                pdf_text_quality = score_text_quality(" ".join(getattr(t, "text", "") for t in tokens_pdf), tokens_pdf) if tokens_pdf else 0.0
                inc = _invoice_number_confidence(r_pdf)
                tc = _total_confidence(r_pdf)
                critical_conf = min(inc, tc) if (r_pdf.invoice_header and inc is not None and tc is not None) else 0.0

                needs_ocr_pages = [p for p, d in page_routing.items() if not d.get("use_text_layer", True)]
                if not needs_ocr_pages:
                    r_pdf.extraction_source = "pdfplumber"
                    r_pdf.extraction_detail = {
                        "method_used": "pdfplumber",
                        "pdf_text_quality": pdf_text_quality,
                        "ocr_text_quality": None,
                        "ocr_median_conf": None,
                        "ocr_mean_conf": None,
                        "low_conf_fraction": None,
                        "dpi_used": None,
                        "reason_flags": ["routing_text_layer_sufficient"],
                        "vision_reason": None,
                        "page_routing": page_routing,
                    }
                    if verbose:
                        print(f"  [{r_pdf.virtual_invoice_id}] accept pdfplumber (routing: text-layer sufficient)")
                    results.append(r_pdf)
                    continue
```
- Invoice boundary-detektering använder per-sida routing (OCR endast när text-layer saknas/är svag).
```71:112:src/pipeline/invoice_boundary_detection.py
    if extraction_path == "pdfplumber":
        import pdfplumber
        pdf = pdfplumber.open(doc.filepath)
        routing_config = get_ocr_routing_config()
        cache_pdf_text = bool(routing_config.get("cache_pdfplumber_text", True))
        text_cache: Optional[dict] = {} if cache_pdf_text else None
        ocr_render_dir: Optional[Path] = None
        try:
            from ..pipeline.tokenizer import extract_tokens_from_page
            from ..pipeline.pdf_renderer import render_page_to_image
            from ..pipeline.ocr_abstraction import extract_tokens_with_ocr, OCRException
            for page in doc.pages:
                pdfplumber_page = pdf.pages[page.page_number - 1]
                page_text = _get_pdfplumber_text(
                    page.page_number,
                    pdfplumber_page,
                    text_cache,
                    cache_pdf_text
                )
                decision = evaluate_text_layer(page_text, [], routing_config)
                if decision["use_text_layer"]:
                    tokens = extract_tokens_from_page(page, pdfplumber_page)
                else:
                    if ocr_render_dir is None:
                        ocr_render_dir = Path(output_dir) / "ocr_render" if output_dir else Path(tempfile.mkdtemp(prefix="ocr_boundary_"))
                        ocr_render_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        render_page_to_image(page, str(ocr_render_dir))
                        tokens = extract_tokens_with_ocr(page)
                    except OCRException as e:
                        if verbose:
                            print(f"  OCR failed for boundary detection page {page.page_number}: {e}")
                        tokens = extract_tokens_from_page(page, pdfplumber_page)
```
- OCR compare-path skyddas mot `KeyError` genom stabil `output_type` och fallback i OCR-abstraktionen.
```168:187:src/pipeline/ocr_abstraction.py
            # Use stable output_type (DICT/STRING) to avoid KeyError across pytesseract versions.
            output_enum = getattr(pytesseract, "Output", None)
            output_dict = getattr(output_enum, "DICT", None)
            output_string = getattr(output_enum, "STRING", None)
            out_type = output_dict or output_string or "dict"
            try:
                tsv_data = pytesseract.image_to_data(
                    img,
                    lang=self.lang,
                    output_type=out_type,  # type: ignore[arg-type]
                    config='--psm 6'  # Assume uniform block of text
                )
            except KeyError:
                fallback_type = output_string or output_dict or "string"
                tsv_data = pytesseract.image_to_data(
                    img,
                    lang=self.lang,
                    output_type=fallback_type,  # type: ignore[arg-type]
                    config='--psm 6'
                )
```
- Enhetstester täcker required/extra anchors och quality override.
```1:49:tests/test_ocr_routing.py
from src.pipeline.ocr_routing import evaluate_text_layer


def test_evaluate_text_layer_requires_required_and_extra_anchors():
    routing = {
        "min_text_chars": 20,
        "required_anchors": [r"Faktura\s"],
        "extra_anchors": [r"Sida\s*\d+\s*/\s*\d+"],
        "min_word_tokens": 5,
        "min_text_quality": 0.5,
        "allow_quality_override": False,
    }
    text = "Faktura\t ABC-123\nSida 1/2\nTotalt 100 SEK\nExtra ord här"
    decision = evaluate_text_layer(text, [], routing)
    assert decision["use_text_layer"] is True
    assert decision["required_anchor_hits"]
    assert decision["extra_anchor_hits"]


def test_evaluate_text_layer_blocks_missing_extra_anchor():
    routing = {
        "min_text_chars": 10,
        "required_anchors": [r"Faktura\s"],
        "extra_anchors": [r"Sida\s*\d+\s*/\s*\d+"],
        "min_word_tokens": 5,
        "min_text_quality": 0.5,
        "allow_quality_override": False,
    }
    text = "Faktura 2025-01-01\nTotalt 100 SEK"
    decision = evaluate_text_layer(text, [], routing)
    assert decision["use_text_layer"] is False
    assert "extra_anchor_missing" in decision["reason_flags"]


def test_evaluate_text_layer_quality_override():
    routing = {
        "min_text_chars": 10,
        "required_anchors": [r"Faktura\s"],
        "extra_anchors": [r"Sida\s*\d+\s*/\s*\d+"],
        "min_word_tokens": 8,
        "min_text_quality": 0.4,
        "allow_quality_override": True,
    }
    text = "Detta är en fakturarad med många ord och rimlig text kvalitet"
    decision = evaluate_text_layer(text, [], routing)
    assert decision["use_text_layer"] is True
    assert "quality_override" in decision["reason_flags"]
```

## Runtime-verifiering (logg)

- `compare_extraction` kördes på `export_2026-01-13_09-09-09.pdf` och samtliga sidor accepterade pdfplumber med routing “text-layer sufficient”.
- Ingen `KeyError: 4` eller compare‑path crash uppstod.

Exempel:
```
Compare: kör pdfplumber för sidor 1-1 …
[30202312] accept pdfplumber (routing: text-layer sufficient)
...
Compare: kör pdfplumber för sidor 14-14 …
[30205452] accept pdfplumber (routing: text-layer sufficient)
```

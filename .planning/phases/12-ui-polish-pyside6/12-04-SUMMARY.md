# 12-04: PDF viewer polish — Summary

**Done:** 2026-01-24

## Objective

Add a viewer toolbar to the PDF viewer with zoom in/out, fit width, prev/next page, and page indicator; style via theme. See 12-DISCUSS.md §4, 12-04-PLAN.md.

## Completed tasks

1. **Viewer toolbar: Zoom in, Zoom out, Fit width**
   - Horizontal **QToolBar** (`pdf_viewer_toolbar`) ovanför PDF-visningen med knappar: **Zooma in**, **Zooma ut**, **Fit bredd**.
   - Zooma in/ut anropar `_view.zoom_in()` resp. `_view.zoom_out()` (steg 1.2x, klämda 0.5–4x).
   - Fit bredd anropar `_view.fit_to_width()` som sätter skalan så att sidbredden fyller viewporten (`scale = viewport().width() / item.boundingRect().width()`).

2. **Viewer toolbar: Prev page, Next page, page indicator**
   - **Föregående** och **Nästa** kopplade till `_on_prev_page()` resp. `_on_next_page()` som anropar `_view.set_page(current ± 1)` och uppdaterar sidindikatorn.
   - **Sidindikator:** `QLabel` med texten "Sida n / tot" (`_page_label`), uppdateras vid `load_pdf`, `set_page` och vid klick på Föregående/Nästa.

3. **Style via theme**
   - Ingen inline-styling. Toolbar har `setObjectName("pdf_viewer_toolbar")`; knappar har `pdf_zoom_in`, `pdf_zoom_out`, `pdf_fit_width`, `pdf_prev_page`, `pdf_next_page`, sidindikatorn `pdf_page_indicator`. App-QSS från 12-01 (QToolBar, QPushButton, QLabel) tillämpas automatiskt.

## Structure

- **PDFViewer** är nu en **QWidget**-container med vertikal layout: toolbar överst, sedan den inre vyn.
- **_PDFGraphicsView** (intern klass, **QGraphicsView**) innehåller all renderings- och zoomlogik, `load_pdf`, `set_page`, `set_candidates`, `highlight_candidate`, samt signalen `candidate_clicked`. Den exponerar `zoom_in()`, `zoom_out()`, `fit_to_width()`, `page_count` och `current_page_number`.
- PDFViewer vidarekopplar `load_pdf`, `set_candidates`, `set_page`, `highlight_candidate` till `_view` och emitterar `candidate_clicked` från `_view`.

## Verify

- `python -c "from src.ui.views.pdf_viewer import PDFViewer; from PySide6.QtWidgets import QApplication; import sys; app=QApplication(sys.argv); w=PDFViewer(); print('ok')"` → ok
- MainWindow med inbäddad PDFViewer startar och visar toolbar med Zoom in/ut, Fit bredd, Föregående, Nästa och sidindikator.
- Manuellt: öppna PDF via GUI, använd zoomanpassning, fit bredd, bläddra sidor och kontrollera att sidindikatorn stämmer.

## Files changed

- **src/ui/views/pdf_viewer.py** — Ny container-klass PDFViewer(QWidget) med QToolBar och knappar; inner view _PDFGraphicsView(QGraphicsView) med zoom_in/zoom_out/fit_to_width och befintlig logik; setObjectName på toolbar och knappar; inga nya beroenden.

## Success criteria (12-04-PLAN)

- PDF viewer has toolbar with Zoom in, Zoom out, Fit width, Prev page, Next page, page indicator/input — **ja**
- Viewer styled via theme (no new dependencies) — **ja**
- Changes only in src/ui/views/pdf_viewer.py — **ja**

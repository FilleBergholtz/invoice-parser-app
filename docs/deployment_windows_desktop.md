# Windows Desktop Deployment

Detta dokument beskriver hur man bygger och distribuerar Windows Desktop-versionen av EPG PDF Extraherare.

## Arkitektur

Applikationen består av två huvudkomponenter:

1.  **Invoice Engine (`invoice_engine.exe`)**:
    *   Fristående Windows executable (byggd med PyInstaller).
    *   Innehåller all Python-logik, dependencies (pdfplumber, pandas, etc) och pipeline.
    *   Körs som en CLI-process (tar input/output paths som argument).
    *   Inga Python-installationskrav på måldatorn.

2.  **UI (Kommer i Fas 5 U3)**:
    *   Grafiskt gränssnitt som anropar `invoice_engine.exe`.

## Bygga Invoice Engine

### Förutsättningar

*   Windows 10/11
*   Python 3.11+ installerat
*   Git bash eller PowerShell

### Byggsteg

1.  Öppna terminal i projektets rotkatalog.
2.  Installera dependencies:
    ```powershell
    pip install -e .[dev]
    ```
3.  Kör byggscriptet:
    ```powershell
    python build/windows/build_engine.py
    ```

### Resultat

*   Den färdiga filen hamnar i `dist/invoice_engine.exe`.
*   Build-artifacts (temp) hamnar i `build/work/`.

## Köra Invoice Engine (CLI)

Du kan testa den byggda filen direkt från terminalen:

```powershell
./dist/invoice_engine.exe --input "path/to/invoice.pdf" --output "output_dir"
```

Flaggor:
*   `--input`: Sökväg till PDF-fil eller mapp.
*   `--output`: Sökväg till output-mapp (skapas om den inte finns).
*   `--artifacts-dir`: (Valfri) Sökväg för detaljerad logg/artifacts.
*   `--fail-fast`: Avbryt vid första felet.
*   `--verbose`: Visa debug-utskrifter.
*   `--strict`: Returnera felkod (1) även vid REVIEW/PARTIAL status (strikt validering).

## Release & Distribution

För att distribuera till slutanvändare:

1.  Bygg `invoice_engine.exe` enligt ovan.
2.  (Senare) Bygg UI-applikationen.
3.  Paketera båda i en installer (t.ex. Inno Setup eller NSIS) eller zip-fil.
4.  Distribuera paketet.

### Code Signing (Placeholder)

För att undvika "Windows protected your PC" varningar bör .exe-filen signeras med ett certifikat.

```powershell
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a dist/invoice_engine.exe
```
*(Kräver ett köpt Code Signing-certifikat)*

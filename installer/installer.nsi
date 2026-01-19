; NSIS Installer Script for EPG PDF Extraherare
; Compile with: makensis installer.nsi

;--------------------------------
; Includes
!include "MUI2.nsh"

;--------------------------------
; General
Name "EPG PDF Extraherare"
OutFile "EPG_PDF_Extraherare_Setup.exe"
Unicode True

; Default installation folder
InstallDir "$PROGRAMFILES64\EPG PDF Extraherare"

; Get installation folder from registry if available
InstallDirRegKey HKCU "Software\EPG PDF Extraherare" ""

; Request application privileges for Windows Vista and later
RequestExecutionLevel admin

; Version information (update from pyproject.toml)
!define VERSION "0.1.0"
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "EPG PDF Extraherare"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "CompanyName" "EPG"
VIAddVersionKey "FileDescription" "EPG PDF Extraherare - PDF invoice parser"

;--------------------------------
; Interface Settings
!define MUI_ABORTWARNING

;--------------------------------
; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"  ; Om du har en LICENSE-fil, annars kommentera bort
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

;--------------------------------
; Languages
!insertmacro MUI_LANGUAGE "Swedish"
!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Installer Sections
Section "Main Application" SecMain
    SectionIn RO  ; Read-only, must be installed
    
    ; Set output path to the installation directory
    SetOutPath "$INSTDIR"
    
    ; Install executables
    File "..\dist\EPG_PDF_Extraherare.exe"  ; CLI version
    File "..\dist\EPG_PDF_Extraherare_GUI.exe"  ; GUI version
    
    ; Install README and other documentation (if needed)
    ; File "..\README.md"
    
    ; Store installation folder
    WriteRegStr HKCU "Software\EPG PDF Extraherare" "" $INSTDIR
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Add to Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EPG_PDF_Extraherare" \
                 "DisplayName" "EPG PDF Extraherare"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EPG_PDF_Extraherare" \
                 "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EPG_PDF_Extraherare" \
                 "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EPG_PDF_Extraherare" \
                 "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EPG_PDF_Extraherare" \
                 "Publisher" "EPG"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EPG_PDF_Extraherare" \
                 "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EPG_PDF_Extraherare" \
                 "NoRepair" 1
SectionEnd

Section "Start Menu Shortcut" SecStartMenu
    CreateDirectory "$SMPROGRAMS\EPG PDF Extraherare"
    CreateShortcut "$SMPROGRAMS\EPG PDF Extraherare\EPG PDF Extraherare (GUI).lnk" "$INSTDIR\EPG_PDF_Extraherare_GUI.exe"
    CreateShortcut "$SMPROGRAMS\EPG PDF Extraherare\EPG PDF Extraherare (CLI).lnk" "$INSTDIR\EPG_PDF_Extraherare.exe"
    CreateShortcut "$SMPROGRAMS\EPG PDF Extraherare\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Desktop Shortcut" SecDesktop
    CreateShortcut "$DESKTOP\EPG PDF Extraherare.lnk" "$INSTDIR\EPG_PDF_Extraherare_GUI.exe"
SectionEnd

;--------------------------------
; Section Descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "Main application files (required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Create Start Menu shortcuts"
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create Desktop shortcut"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; Uninstaller Section
Section "Uninstall"
    ; Remove files
    Delete "$INSTDIR\EPG_PDF_Extraherare.exe"
    Delete "$INSTDIR\EPG_PDF_Extraherare_GUI.exe"
    Delete "$INSTDIR\Uninstall.exe"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\EPG PDF Extraherare\EPG PDF Extraherare (GUI).lnk"
    Delete "$SMPROGRAMS\EPG PDF Extraherare\EPG PDF Extraherare (CLI).lnk"
    Delete "$SMPROGRAMS\EPG PDF Extraherare\Uninstall.lnk"
    RMDir "$SMPROGRAMS\EPG PDF Extraherare"
    Delete "$DESKTOP\EPG PDF Extraherare.lnk"
    
    ; Remove installation directory (if empty)
    RMDir "$INSTDIR"
    
    ; Remove registry keys
    DeleteRegKey /ifempty HKCU "Software\EPG PDF Extraherare"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EPG_PDF_Extraherare"
SectionEnd

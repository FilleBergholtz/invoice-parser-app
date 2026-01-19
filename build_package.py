"""Script för att skapa installationspaket med PowerShell-installer."""

import os
import shutil
import sys
import zipfile
from pathlib import Path


def create_powershell_installer(installer_path):
    """Skapa PowerShell-installer script."""
    installer_content = r"""# PowerShell Installer Script for EPG PDF Extraherare
# Detta script installerar applikationen till Program Files och skapar shortcuts

param(
    [switch]$Silent = $false
)

$ErrorActionPreference = "Stop"

# App information
$AppName = "EPG PDF Extraherare"
$AppVersion = "0.1.0"
$Publisher = "EPG"
$InstallDir = "$env:ProgramFiles\$AppName"
$StartMenuDir = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\$AppName"

# Kontrollera admin-rättigheter
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Detta script kräver administratörsrättigheter." -ForegroundColor Red
    Write-Host "Starta PowerShell som administratör och kör scriptet igen." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Tryck på valfri tangent för att avsluta..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Hitta scriptets plats (där executables finns)
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$CliExe = Join-Path $ScriptPath "EPG_PDF_Extraherare.exe"
$GuiExe = Join-Path $ScriptPath "EPG_PDF_Extraherare_GUI.exe"

# Kontrollera att executables finns
if (-not (Test-Path $CliExe)) {
    Write-Host "Fel: EPG_PDF_Extraherare.exe hittades inte!" -ForegroundColor Red
    Write-Host "Sökväg: $CliExe" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $GuiExe)) {
    Write-Host "Fel: EPG_PDF_Extraherare_GUI.exe hittades inte!" -ForegroundColor Red
    Write-Host "Sökväg: $GuiExe" -ForegroundColor Yellow
    exit 1
}

if (-not $Silent) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  $AppName Installer" -ForegroundColor Cyan
    Write-Host "  Version $AppVersion" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Detta kommer att installera $AppName till:" -ForegroundColor White
    Write-Host "  $InstallDir" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Fortsätt med installationen? (J/N)"
    if ($response -notmatch '^[JjYy]') {
        Write-Host "Installation avbruten." -ForegroundColor Yellow
        exit 0
    }
    Write-Host ""
}

try {
    # Skapa installationsmapp
    Write-Host "Skapar installationsmapp..." -ForegroundColor Green
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }

    # Kopiera executables
    Write-Host "Kopierar filer..." -ForegroundColor Green
    Copy-Item $CliExe -Destination $InstallDir -Force
    Copy-Item $GuiExe -Destination $InstallDir -Force

    # Skapa uninstaller script
    $UninstallScript = @"
# Uninstaller for $AppName
`$ErrorActionPreference = "Stop"

`$AppName = "$AppName"
`$InstallDir = "$InstallDir"
`$StartMenuDir = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\$AppName"

Write-Host "Avinstallerar `$AppName..." -ForegroundColor Yellow

# Ta bort filer
if (Test-Path "`$InstallDir\EPG_PDF_Extraherare.exe") {
    Remove-Item "`$InstallDir\EPG_PDF_Extraherare.exe" -Force
}
if (Test-Path "`$InstallDir\EPG_PDF_Extraherare_GUI.exe") {
    Remove-Item "`$InstallDir\EPG_PDF_Extraherare_GUI.exe" -Force
}

# Ta bort shortcuts
if (Test-Path "`$StartMenuDir") {
    Remove-Item "`$StartMenuDir" -Recurse -Force
}
if (Test-Path "`$env:Public\Desktop\EPG PDF Extraherare.lnk") {
    Remove-Item "`$env:Public\Desktop\EPG PDF Extraherare.lnk" -Force
}

# Ta bort installationsmapp om tom
if (Test-Path `$InstallDir) {
    `$items = Get-ChildItem `$InstallDir -ErrorAction SilentlyContinue
    if (`$items.Count -eq 0) {
        Remove-Item `$InstallDir -Force
    }
}

# Ta bort från Add/Remove Programs
`$uninstallKey = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
if (Test-Path `$uninstallKey) {
    Remove-Item `$uninstallKey -Recurse -Force
}

Write-Host "Avinstallation klar!" -ForegroundColor Green
"@
    $UninstallScript | Out-File -FilePath "$InstallDir\Uninstall.ps1" -Encoding UTF8

    # Skapa Start Menu shortcuts
    Write-Host "Skapar Start Menu-genvägar..." -ForegroundColor Green
    if (-not (Test-Path $StartMenuDir)) {
        New-Item -ItemType Directory -Path $StartMenuDir -Force | Out-Null
    }

    $WshShell = New-Object -ComObject WScript.Shell
    
    # GUI shortcut
    $GuiShortcut = $WshShell.CreateShortcut("$StartMenuDir\EPG PDF Extraherare (GUI).lnk")
    $GuiShortcut.TargetPath = "$InstallDir\EPG_PDF_Extraherare_GUI.exe"
    $GuiShortcut.WorkingDirectory = $InstallDir
    $GuiShortcut.Description = "EPG PDF Extraherare - GUI Version"
    $GuiShortcut.Save()

    # CLI shortcut
    $CliShortcut = $WshShell.CreateShortcut("$StartMenuDir\EPG PDF Extraherare (CLI).lnk")
    $CliShortcut.TargetPath = "$InstallDir\EPG_PDF_Extraherare.exe"
    $CliShortcut.WorkingDirectory = $InstallDir
    $CliShortcut.Description = "EPG PDF Extraherare - CLI Version"
    $CliShortcut.Save()

    # Uninstall shortcut
    $UninstallShortcut = $WshShell.CreateShortcut("$StartMenuDir\Avinstallera.lnk")
    $UninstallShortcut.TargetPath = "powershell.exe"
    $UninstallShortcut.Arguments = "-ExecutionPolicy Bypass -File `"$InstallDir\Uninstall.ps1`""
    $UninstallShortcut.WorkingDirectory = $InstallDir
    $UninstallShortcut.Description = "Avinstallera EPG PDF Extraherare"
    $UninstallShortcut.Save()

    # Desktop shortcut (fråga användaren)
    if (-not $Silent) {
        $desktopResponse = Read-Host "Skapa genväg på skrivbordet? (J/N)"
        if ($desktopResponse -match '^[JjYy]') {
            $DesktopShortcut = $WshShell.CreateShortcut("$env:Public\Desktop\EPG PDF Extraherare.lnk")
            $DesktopShortcut.TargetPath = "$InstallDir\EPG_PDF_Extraherare_GUI.exe"
            $DesktopShortcut.WorkingDirectory = $InstallDir
            $DesktopShortcut.Description = "EPG PDF Extraherare"
            $DesktopShortcut.Save()
            Write-Host "Skrivbordsgenväg skapad." -ForegroundColor Green
        }
    }

    # Registrera i Add/Remove Programs
    Write-Host "Registrerar i Windows..." -ForegroundColor Green
    $uninstallKey = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
    New-Item -Path $uninstallKey -Force | Out-Null
    Set-ItemProperty -Path $uninstallKey -Name "DisplayName" -Value $AppName
    Set-ItemProperty -Path $uninstallKey -Name "DisplayVersion" -Value $AppVersion
    Set-ItemProperty -Path $uninstallKey -Name "Publisher" -Value $Publisher
    Set-ItemProperty -Path $uninstallKey -Name "InstallLocation" -Value $InstallDir
    Set-ItemProperty -Path $uninstallKey -Name "UninstallString" -Value "powershell.exe -ExecutionPolicy Bypass -File `"$InstallDir\Uninstall.ps1`""
    Set-ItemProperty -Path $uninstallKey -Name "NoModify" -Value 1 -Type DWord
    Set-ItemProperty -Path $uninstallKey -Name "NoRepair" -Value 1 -Type DWord

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Installation klar!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Applikationen är installerad i:" -ForegroundColor White
    Write-Host "  $InstallDir" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Du kan nu starta applikationen från Start-menyn." -ForegroundColor White
    Write-Host ""

    if (-not $Silent) {
        Write-Host "Tryck på valfri tangent för att avsluta..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }

} catch {
    Write-Host ""
    Write-Host "Fel vid installation: $_" -ForegroundColor Red
    Write-Host ""
    if (-not $Silent) {
        Write-Host "Tryck på valfri tangent för att avsluta..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    exit 1
}
"""
    
    with open(installer_path, 'w', encoding='utf-8') as f:
        f.write(installer_content)
    print(f'✅ PowerShell-installer skapad: {installer_path}')


def main():
    """Skapa installationspaket (ZIP med installer)."""
    project_root = Path(__file__).parent
    
    # Kontrollera att båda executables finns
    dist_cli = project_root / "dist" / "EPG_PDF_Extraherare.exe"
    dist_gui = project_root / "dist" / "EPG_PDF_Extraherare_GUI.exe"
    
    if not dist_cli.exists() or not dist_gui.exists():
        print(f"\n❌ Executables hittades inte!")
        if not dist_cli.exists():
            print(f"  Saknas: {dist_cli}")
        if not dist_gui.exists():
            print(f"  Saknas: {dist_gui}")
        print("\nBygg executables först med: python build_windows.py")
        sys.exit(1)
    
    print(f"✅ CLI executable hittad: {dist_cli}")
    print(f"✅ GUI executable hittad: {dist_gui}")
    
    # Skapa paket-mapp
    package_dir = project_root / "package"
    if package_dir.exists():
        print(f"\nRensar gammal package-mapp: {package_dir}")
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    
    # Kopiera executables till package-mappen
    print(f"\nKopierar executables till package-mappen...")
    shutil.copy2(dist_cli, package_dir / "EPG_PDF_Extraherare.exe")
    shutil.copy2(dist_gui, package_dir / "EPG_PDF_Extraherare_GUI.exe")
    
    # Skapa PowerShell-installer
    installer_script = package_dir / "install.ps1"
    create_powershell_installer(installer_script)
    
    # Skapa README
    readme_content = """# EPG PDF Extraherare - Installation

## Installation

1. Extrahera ZIP-filen till en mapp (t.ex. på Skrivbordet)
2. Högerklicka på `install.ps1`
3. Välj "Kör med PowerShell"
4. Om Windows blockerar scriptet:
   - Högerklicka på `install.ps1`
   - Välj "Egenskaper"
   - Kryssa i "Avblockera" längst ner
   - Klicka OK
   - Kör scriptet igen

**Viktigt:** Du behöver administratörsrättigheter för att installera.

## Användning

Efter installation kan du starta applikationen från:
- Start-menyn → EPG PDF Extraherare → EPG PDF Extraherare (GUI)
- Eller dubbelklicka på skrivbordsgenvägen (om du valde att skapa en)

## Avinstallation

Du kan avinstallera via:
- Start-menyn → EPG PDF Extraherare → Avinstallera
- Eller: Inställningar → Appar → EPG PDF Extraherare → Avinstallera

## Filer i paketet

- `EPG_PDF_Extraherare.exe` - CLI-version (kommandorad)
- `EPG_PDF_Extraherare_GUI.exe` - GUI-version (rekommenderat)
- `install.ps1` - Installer-script
"""
    
    with open(package_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Skapa ZIP-fil
    zip_path = project_root / "EPG_PDF_Extraherare_Installer.zip"
    if zip_path.exists():
        print(f"\nRensar gammal ZIP-fil: {zip_path}")
        zip_path.unlink()
    
    print(f"\nSkapar ZIP-fil: {zip_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in package_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(package_dir)
                zipf.write(file, arcname)
                print(f"  Lade till: {arcname}")
    
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    
    print("\n" + "="*70)
    print("✅ Installationspaket skapat framgångsrikt!")
    print(f"\nPaket location: {zip_path}")
    print(f"Filstorlek: {zip_size_mb:.1f} MB")
    print(f"\nInnehåll:")
    print(f"  - EPG_PDF_Extraherare.exe (CLI)")
    print(f"  - EPG_PDF_Extraherare_GUI.exe (GUI)")
    print(f"  - install.ps1 (Installer-script)")
    print(f"  - README.txt (Instruktioner)")
    print("\n" + "="*70)
    print("\n📦 Distribuera denna ZIP-fil till slutanvändare.")
    print("   Användare extraherar ZIP-filen och kör install.ps1 för att installera.")
    print("="*70)


if __name__ == "__main__":
    main()
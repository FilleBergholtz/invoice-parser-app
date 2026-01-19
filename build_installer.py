"""Script för att bygga NSIS installer (efter att executable är byggd)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_nsis():
    """Hitta NSIS makensis executable."""
    # Vanliga NSIS installationssökvägar
    common_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
        r"C:\NSIS\makensis.exe",
    ]
    
    # Kontrollera om makensis är i PATH
    try:
        result = subprocess.run(
            ["makensis", "/VERSION"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ NSIS hittades i PATH")
            return "makensis"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Kontrollera vanliga installationssökvägar
    for path in common_paths:
        if Path(path).exists():
            print(f"✅ NSIS hittades: {path}")
            return path
    
    return None


def main():
    """Bygg NSIS installer."""
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
    
    # Hitta NSIS
    nsis_path = find_nsis()
    
    if not nsis_path:
        print("\n" + "="*70)
        print("❌ NSIS hittades inte!")
        print("\nFör att skapa installer behöver du installera NSIS:")
        print("\n1. Ladda ner NSIS från: https://nsis.sourceforge.io/Download")
        print("2. Installera NSIS (standard sökväg används)")
        print("3. Efter installation, kör detta script igen:")
        print("   python build_installer.py")
        print("\n" + "="*70)
        print("\nAlternativt kan du använda den färdiga .exe-filen i dist/ direkt.")
        print("Eller manuellt kompilera installer.nsi efter att ha installerat NSIS.\n")
        sys.exit(1)
    
    # Bygg installer
    installer_script = project_root / "installer" / "installer.nsi"
    installer_dir = project_root / "installer"
    installer_exe = installer_dir / "EPG_PDF_Extraherare_Setup.exe"
    dist_dir = project_root / "dist"
    
    # Verifiera att dist-filerna finns och är tillgängliga
    dist_cli_abs = dist_dir / "EPG_PDF_Extraherare.exe"
    dist_gui_abs = dist_dir / "EPG_PDF_Extraherare_GUI.exe"
    
    if not dist_cli_abs.exists() or not dist_gui_abs.exists():
        print(f"\n❌ Executables hittades inte i dist/!")
        sys.exit(1)
    
    # Rensa gamla installer-fil om den finns
    if installer_exe.exists():
        print(f"Rensar gammal installer-fil: {installer_exe}")
        installer_exe.unlink()
    
    # För stora filer kan NSIS ha problem med memory-mapping
    # Kopiera filerna till installer-mappen temporärt för att undvika problem
    temp_cli = installer_dir / "EPG_PDF_Extraherare.exe"
    temp_gui = installer_dir / "EPG_PDF_Extraherare_GUI.exe"
    
    print(f"\nKopierar executables till installer-mappen (för att undvika NSIS memory-mapping problem)...")
    try:
        if temp_cli.exists():
            temp_cli.unlink()
        if temp_gui.exists():
            temp_gui.unlink()
        
        print(f"  Kopierar CLI...")
        shutil.copy2(dist_cli_abs, temp_cli)
        print(f"  Kopierar GUI...")
        shutil.copy2(dist_gui_abs, temp_gui)
        print(f"  ✅ Kopiering klar\n")
    except Exception as e:
        print(f"  ⚠️  Kunde inte kopiera filer: {e}")
        print(f"  Försöker använda original sökvägar istället...\n")
        temp_cli = None
        temp_gui = None
    
    print(f"Bygger installer...")
    print(f"  NSIS: {nsis_path}")
    print(f"  Script: {installer_script}")
    print(f"  Output: {installer_dir}\n")
    
    try:
        # Kör NSIS från installer-mappen
        # installer.nsi använder nu filer i samma mapp om kopiering lyckades
        os.chdir(installer_dir)
        
        # Använd /NOCD för att NSIS inte ska ändra working directory
        # För stora filer kan vi behöva använda /D flaggan för att definiera variabler
        result = subprocess.run(
            [nsis_path, "/NOCD", str(installer_script)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ NSIS körde med felkod: {result.returncode}")
            if result.stdout:
                print("\nNSIS output:")
                print(result.stdout)
            if result.stderr:
                print("\nNSIS felmeddelande:")
                print(result.stderr)
            
            # Ge användbar information om problemet
            print("\n" + "="*70)
            print("⚠️  NSIS har kända problem med filer större än 2 GB")
            print("\nDina executables är ~2.8 GB vardera, vilket överskrider NSIS gränsen.")
            print("\nAlternativ:")
            print("1. Använd executables direkt från dist/ mappen (ingen installer behövs)")
            print("2. Använd en annan installer-teknik som Inno Setup")
            print("3. Minska storleken på executables (ta bort onödiga dependencies)")
            print("="*70)
            sys.exit(1)
        
        if installer_exe.exists():
            print("\n" + "="*70)
            print("✅ Installer skapad framgångsrikt!")
            print(f"\nInstaller location: {installer_exe}")
            print(f"Filstorlek: {installer_exe.stat().st_size / (1024*1024):.1f} MB")
            print("\n" + "="*70)
        else:
            print(f"\n⚠️  NSIS kördes men installer-filen hittades inte: {installer_exe}")
            print("Kontrollera NSIS output ovan för eventuella fel.")
            
    except Exception as e:
        print(f"\n❌ Fel vid byggning av installer: {e}")
        sys.exit(1)
    finally:
        # Rensa temporära kopior
        if temp_cli and temp_cli.exists():
            try:
                temp_cli.unlink()
                print(f"Rensade temporär CLI-fil")
            except:
                pass
        if temp_gui and temp_gui.exists():
            try:
                temp_gui.unlink()
                print(f"Rensade temporär GUI-fil")
            except:
                pass
        os.chdir(project_root)


if __name__ == "__main__":
    main()

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
    
    # Kontrollera att executable finns
    dist_exe = project_root / "dist" / "EPG_PDF_Extraherare.exe"
    if not dist_exe.exists():
        print(f"\n❌ Executable hittades inte: {dist_exe}")
        print("Bygg executable först med: python build_windows.py")
        sys.exit(1)
    
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
    
    # Rensa gamla installer-fil om den finns
    if installer_exe.exists():
        print(f"Rensar gammal installer-fil: {installer_exe}")
        installer_exe.unlink()
    
    print(f"\nBygger installer...")
    print(f"  NSIS: {nsis_path}")
    print(f"  Script: {installer_script}")
    print(f"  Output: {installer_dir}\n")
    
    try:
        os.chdir(installer_dir)
        
        result = subprocess.run(
            [nsis_path, str(installer_script)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ NSIS körde med felkod: {result.returncode}")
            if result.stderr:
                print("\nNSIS felmeddelande:")
                print(result.stderr)
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
        os.chdir(project_root)


if __name__ == "__main__":
    main()

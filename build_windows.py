"""Build script for Windows executable using PyInstaller and NSIS installer."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_nsis():
    """Find NSIS makensis executable."""
    # Common NSIS installation paths
    common_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
        r"C:\NSIS\makensis.exe",
    ]
    
    # Check if makensis is in PATH
    try:
        result = subprocess.run(
            ["makensis", "/VERSION"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return "makensis"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Check common installation paths
    for path in common_paths:
        if Path(path).exists():
            return path
    
    return None


def build_installer(project_root):
    """Build NSIS installer."""
    nsis_path = find_nsis()
    
    if not nsis_path:
        print("\n⚠️  NSIS hittades inte!")
        print("\nFör att skapa installer behöver du installera NSIS:")
        print("1. Ladda ner från: https://nsis.sourceforge.io/Download")
        print("2. Installera NSIS (standard installationssökväg används)")
        print("3. Kör detta script igen\n")
        print("Alternativt kan du använda den färdiga .exe-filen i dist/ direkt.\n")
        return False
    
    installer_script = project_root / "installer" / "installer.nsi"
    dist_exe = project_root / "dist" / "EPG_PDF_Extraherare.exe"
    
    if not dist_exe.exists():
        print(f"\n❌ Executable hittades inte: {dist_exe}")
        print("Bygg executable först med: python build_windows.py")
        return False
    
    print(f"\nBygger installer med NSIS från: {nsis_path}")
    print(f"Installer script: {installer_script}")
    
    try:
        installer_dir = project_root / "installer"
        os.chdir(installer_dir)
        
        subprocess.check_call([
            nsis_path,
            str(installer_script),
        ])
        
        installer_exe = installer_dir / "EPG_PDF_Extraherare_Setup.exe"
        if installer_exe.exists():
            print(f"\n✅ Installer skapad framgångsrikt!")
            print(f"Installer location: {installer_exe}")
            return True
        else:
            print("\n⚠️  NSIS kördes men installer-filen hittades inte.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Installer build misslyckades: {e}")
        return False
    finally:
        os.chdir(project_root)


def main():
    """Build Windows executable and optionally installer."""
    project_root = Path(__file__).parent
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller är inte installerat. Installerar...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Change to project root
    os.chdir(project_root)
    
    # Clean previous builds
    build_dir = project_root / "build"
    dist_dir = project_root / "dist"
    if build_dir.exists():
        print(f"Rensar build directory: {build_dir}")
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        print(f"Rensar dist directory: {dist_dir}")
        shutil.rmtree(dist_dir)
    
    # Run PyInstaller
    spec_file = project_root / "EPG_PDF_Extraherare.spec"
    print(f"Bygger executable med {spec_file}...")
    
    try:
        subprocess.check_call([
            sys.executable,
            "-m",
            "PyInstaller",
            str(spec_file),
            "--clean",
            "--noconfirm",
        ])
        print("\n✅ Executable byggd framgångsrikt!")
        print(f"Executable location: {dist_dir / 'EPG_PDF_Extraherare.exe'}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build misslyckades: {e}")
        sys.exit(1)
    
    # Ask if user wants to build installer
    print("\n" + "="*60)
    build_installer_prompt = input("\nVill du också skapa Windows installer? (j/n): ").strip().lower()
    
    if build_installer_prompt in ['j', 'ja', 'y', 'yes']:
        build_installer(project_root)
    else:
        print("\nHoppar över installer-build. Kör build_windows.py igen senare om du vill skapa installer.")


if __name__ == "__main__":
    main()

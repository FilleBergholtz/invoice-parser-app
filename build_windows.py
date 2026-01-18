"""Build script for Windows executable using PyInstaller."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    """Build Windows executable."""
    project_root = Path(__file__).parent
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Change to project root
    os.chdir(project_root)
    
    # Clean previous builds
    build_dir = project_root / "build"
    dist_dir = project_root / "dist"
    if build_dir.exists():
        print(f"Cleaning build directory: {build_dir}")
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        print(f"Cleaning dist directory: {dist_dir}")
        shutil.rmtree(dist_dir)
    
    # Run PyInstaller
    spec_file = project_root / "EPG_PDF_Extraherare.spec"
    print(f"Building executable using {spec_file}...")
    
    try:
        subprocess.check_call([
            sys.executable,
            "-m",
            "PyInstaller",
            str(spec_file),
            "--clean",
            "--noconfirm",
        ])
        print("\n✅ Build successful!")
        print(f"Executable location: {dist_dir / 'EPG_PDF_Extraherare.exe'}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

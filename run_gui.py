"""UI Entry point for PyInstaller."""
import sys
from pathlib import Path

# Ensure src is in path
root = Path(__file__).parent.resolve()
sys.path.insert(0, str(root))

from src.ui.app import main

if __name__ == "__main__":
    main()

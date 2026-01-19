"""Simple script to run Streamlit app."""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    # Get the path to the Streamlit app
    app_path = project_root / "src" / "web" / "app.py"
    
    # Set PYTHONPATH to include project root so relative imports work
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    if pythonpath:
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{pythonpath}"
    else:
        env["PYTHONPATH"] = str(project_root)
    
    # Run Streamlit via subprocess to avoid Runtime instance conflicts
    # This is safer than using stcli.main() directly
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.headless",
        "true"
    ]
    
    try:
        subprocess.run(cmd, check=True, env=env, cwd=str(project_root))
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

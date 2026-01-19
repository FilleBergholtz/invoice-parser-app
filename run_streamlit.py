"""Simple script to run Streamlit app."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run streamlit CLI
from streamlit.web import cli as stcli

if __name__ == "__main__":
    # Get the path to the Streamlit app
    app_path = project_root / "src" / "web" / "app.py"
    
    # Set up sys.argv as if we ran: streamlit run src/web/app.py
    sys.argv = ["streamlit", "run", str(app_path), "--server.headless", "true"]
    
    # Run Streamlit
    stcli.main()

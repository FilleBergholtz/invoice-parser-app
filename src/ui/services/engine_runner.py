"""Service to run the invoice engine executable."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional
from PySide6.QtCore import QObject, Signal, QThread

class EngineRunner(QObject):
    """Worker object to run the engine in a separate thread."""
    
    # Signals
    started = Signal()
    finished = Signal(int)  # exit code
    progress = Signal(str)  # log line
    error = Signal(str)     # error message
    result_ready = Signal(dict) # run_summary.json content
    
    def __init__(self, pdf_path: str, output_dir: str):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.process = None
        
    def run(self):
        """Run the engine process."""
        self.started.emit()
        
        # Determine engine path
        # In dev: run python run_engine.py
        # In prod: run invoice_engine.exe
        
        # Check for frozen executable (PyInstaller)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
            engine_exe = base_path / "invoice_engine.exe"
            # If we are the GUI exe, the engine exe should be next to us
            if not engine_exe.exists():
                # Fallback: maybe we ARE the engine (unlikely for GUI)
                pass
            cmd = [str(engine_exe)]
        else:
            # Development mode
            # Find project root
            current_file = Path(__file__).resolve()
            # src/ui/services/engine_runner.py -> src/ui/services -> src/ui -> src -> root
            project_root = current_file.parent.parent.parent.parent
            script_path = project_root / "run_engine.py"
            cmd = [sys.executable, str(script_path)]
            
        # Add arguments
        cmd.extend([
            "--input", self.pdf_path,
            "--output", self.output_dir,
            "--verbose",
            # "--fail-fast" # Optional
        ])
        
        self.progress.emit(f"Starting engine: {' '.join(cmd)}")
        
        try:
            # Run process
            # Use Popen to capture output in real-time
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
            else:
                creationflags = 0
                
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=creationflags
            )
            
            # Read stdout line by line
            while True:
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    self.progress.emit(line.strip())
            
            exit_code = self.process.poll()
            self.progress.emit(f"Engine finished with exit code {exit_code}")
            
            # Load result if successful
            if exit_code == 0 or exit_code == 1: # 1 might mean Partial/Review if not strict
                summary_path = Path(self.output_dir) / "run_summary.json"
                if summary_path.exists():
                    try:
                        with open(summary_path, 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                            self.result_ready.emit(summary)
                    except Exception as e:
                        self.error.emit(f"Failed to load summary: {e}")
                else:
                    if exit_code == 0:
                        self.error.emit("Engine reported success but run_summary.json not found.")
            
            self.finished.emit(exit_code)
            
        except Exception as e:
            self.error.emit(f"Failed to start engine: {e}")
            self.finished.emit(-1)

    def kill(self):
        """Kill the running process."""
        if self.process:
            self.process.kill()

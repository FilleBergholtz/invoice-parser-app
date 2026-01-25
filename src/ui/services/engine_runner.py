"""Service to run the invoice engine executable."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, Signal, QThread

# Engine states (12-03)
STATE_IDLE = "Idle"
STATE_RUNNING = "Running"
STATE_SUCCESS = "Success"
STATE_WARNING = "Warning"
STATE_ERROR = "Error"


class EngineRunner(QObject):
    """Worker object to run the engine in a separate thread."""

    # States: Idle, Running, Success, Warning, Error
    stateChanged = Signal(str)
    progressChanged = Signal(str)   # step or short message
    logLine = Signal(str)           # each stdout/stderr line
    # Legacy / compat
    started = Signal()
    progress = Signal(str)          # same as logLine for backward compat
    error = Signal(str)
    result_ready = Signal(dict)
    finished = Signal(bool, object)  # success, paths (dict or None)

    def __init__(self, pdf_path: str, output_dir: str):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.process: Optional[subprocess.Popen] = None

    def run(self) -> None:
        """Run the engine process. Emits stateChanged, logLine, finished(success, paths)."""
        self.started.emit()
        self.stateChanged.emit(STATE_RUNNING)
        self.progressChanged.emit("Startar motor…")
        
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
            
        # Standard flow: pdfplumber + OCR (compare, use best); AI fallback if confidence < 95%
        cmd.extend([
            "--input", self.pdf_path,
            "--output", self.output_dir,
            "--verbose",
        ])

        def emit_log(s: str) -> None:
            self.logLine.emit(s)
            self.progress.emit(s)

        emit_log(f"Kommando: {' '.join(cmd)}")
        paths: Optional[Dict[str, Any]] = None

        try:
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
            else:
                creationflags = 0

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )

            stdout = self.process.stdout
            if stdout is None:
                emit_log("Ingen stdout från process")
                self.stateChanged.emit(STATE_ERROR)
                self.finished.emit(False, None)
                return
            while True:
                line = stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    emit_log(line.rstrip("\n"))

            exit_code = self.process.poll() or -1
            emit_log(f"Motor avslutad med exit code {exit_code}")

            if exit_code == 0 or exit_code == 1:
                summary_path = Path(self.output_dir) / "run_summary.json"
                if summary_path.exists():
                    try:
                        with open(summary_path, "r", encoding="utf-8") as f:
                            summary = json.load(f)
                            self.result_ready.emit(summary)
                            paths = {
                                "output_dir": self.output_dir,
                                "excel_path": summary.get("excel_path"),
                            }
                    except Exception as e:
                        err = f"Kunde inte ladda run_summary: {e}"
                        self.error.emit(err)
                        self.stateChanged.emit(STATE_ERROR)
                        self.finished.emit(False, None)
                        return
                elif exit_code == 0:
                    self.error.emit("Engine rapporterade lyckat men run_summary.json saknas.")
                    self.stateChanged.emit(STATE_ERROR)
                    self.finished.emit(False, None)
                    return

            if exit_code == 0:
                self.stateChanged.emit(STATE_SUCCESS)
                self.finished.emit(True, paths or {"output_dir": self.output_dir})
            elif exit_code == 1:
                self.stateChanged.emit(STATE_WARNING)
                self.finished.emit(True, paths or {"output_dir": self.output_dir})
            else:
                self.stateChanged.emit(STATE_ERROR)
                self.finished.emit(False, None)

        except Exception as e:
            err = f"Kunde inte starta motor: {e}"
            self.error.emit(err)
            self.stateChanged.emit(STATE_ERROR)
            self.finished.emit(False, None)

    def kill(self):
        """Kill the running process."""
        if self.process:
            self.process.kill()

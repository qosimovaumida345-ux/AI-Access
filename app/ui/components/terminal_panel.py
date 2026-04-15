# ============================================================
# SHADOWFORGE OS — TERMINAL PANEL
# Bottom panel: live log output + interactive shell commands.
# ============================================================

import subprocess
import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton,
    QScrollBar,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

from core.logger import get_logger

logger = get_logger("UI.Terminal")

# Log level → color
LEVEL_COLORS = {
    "info":  "#9070c0",
    "ok":    "#00cc66",
    "warn":  "#ff9900",
    "error": "#ff0015",
    "cmd":   "#6600cc",
    "out":   "#708090",
}


class ShellWorker(QThread):
    """Runs a shell command and streams output."""
    output_line = pyqtSignal(str, str)   # text, level
    finished    = pyqtSignal(int)        # return code

    def __init__(self, command: str, cwd: str = None):
        super().__init__()
        self.command = command
        self.cwd     = cwd

    def run(self):
        try:
            proc = subprocess.Popen(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd,
            )
            for line in proc.stdout:
                self.output_line.emit(line.rstrip(), "out")
            proc.wait()
            self.finished.emit(proc.returncode)
        except Exception as e:
            self.output_line.emit(str(e), "error")
            self.finished.emit(-1)


class TerminalPanel(QWidget):
    """
    Terminal / log panel.
    - Shows timestamped color-coded log messages
    - Has an input bar to run shell commands
    - Keeps a scrollback buffer (max 2000 lines)
    """

    MAX_LINES = 2000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TerminalPanel")
        self._shell_worker: ShellWorker = None
        self._line_count = 0
        self._build_ui()
        self.log("◈ ShadowForge terminal ready.", "ok")

    # ── UI BUILD ─────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_row = QWidget()
        header_row.setObjectName("TermHeader")
        header_row.setFixedHeight(30)
        header_row.setStyleSheet("""
            QWidget#TermHeader {
                background: #040008;
                border-top: 1px solid rgba(102,0,204,0.2);
                border-bottom: 1px solid rgba(102,0,204,0.1);
            }
        """)
        h_layout = QHBoxLayout(header_row)
        h_layout.setContentsMargins(8, 0, 6, 0)

        title = QLabel("◈ TERMINAL")
        title.setFont(QFont("Share Tech Mono", 8))
        title.setStyleSheet("color: #5a4070; letter-spacing: 2px;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        clear_btn = QPushButton("CLR")
        clear_btn.setFixedSize(32, 20)
        clear_btn.setFont(QFont("Share Tech Mono", 7))
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #3a2550;
                border: 1px solid #2d0057;
                border-radius: 2px;
            }
            QPushButton:hover { color: #6600cc; border-color: #6600cc; }
        """)
        clear_btn.clicked.connect(self.clear_log)
        h_layout.addWidget(clear_btn)

        layout.addWidget(header_row)

        # Log output
        self._log = QTextEdit()
        self._log.setObjectName("TermLog")
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Share Tech Mono", 9))
        self._log.setStyleSheet("""
            QTextEdit {
                background: #020005;
                color: #9070c0;
                border: none;
                padding: 4px 8px;
                selection-background-color: rgba(102,0,204,0.3);
            }
            QScrollBar:vertical {
                width: 4px;
                background: #020005;
            }
            QScrollBar::handle:vertical {
                background: #2d0057;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self._log)

        # Command input bar
        input_row = QWidget()
        input_row.setObjectName("TermInputRow")
        input_row.setFixedHeight(34)
        input_row.setStyleSheet("""
            QWidget#TermInputRow {
                background: #040008;
                border-top: 1px solid rgba(102,0,204,0.15);
            }
        """)
        i_layout = QHBoxLayout(input_row)
        i_layout.setContentsMargins(6, 4, 6, 4)
        i_layout.setSpacing(6)

        prompt_lbl = QLabel("❯")
        prompt_lbl.setFont(QFont("Share Tech Mono", 10))
        prompt_lbl.setStyleSheet("color: #6600cc;")
        i_layout.addWidget(prompt_lbl)

        self._cmd_input = QLineEdit()
        self._cmd_input.setObjectName("TermInput")
        self._cmd_input.setPlaceholderText("Run shell command...")
        self._cmd_input.setFont(QFont("Share Tech Mono", 9))
        self._cmd_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: #c0a0f0;
                border: none;
                font-size: 9pt;
            }
            QLineEdit:focus { border: none; outline: none; }
        """)
        self._cmd_input.returnPressed.connect(self._on_run_cmd)
        i_layout.addWidget(self._cmd_input)

        run_btn = QPushButton("RUN")
        run_btn.setFixedSize(36, 22)
        run_btn.setFont(QFont("Share Tech Mono", 7))
        run_btn.setStyleSheet("""
            QPushButton {
                background: rgba(102,0,204,0.15);
                color: #6600cc;
                border: 1px solid #2d0057;
                border-radius: 2px;
            }
            QPushButton:hover { background: rgba(102,0,204,0.3); }
        """)
        run_btn.clicked.connect(self._on_run_cmd)
        i_layout.addWidget(run_btn)

        layout.addWidget(input_row)

    # ── PUBLIC API ───────────────────────────────────────────
    def log(self, text: str, level: str = "info"):
        """
        Append a colored log line.
        Levels: info | ok | warn | error | cmd | out
        """
        color  = LEVEL_COLORS.get(level, LEVEL_COLORS["info"])
        ts     = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "ok":    "✓",
            "error": "✗",
            "warn":  "⚠",
            "cmd":   "❯",
            "out":   " ",
        }.get(level, "◈")

        line = f'<span style="color:#3a2550;">[{ts}]</span> ' \
               f'<span style="color:{color};">{prefix} {self._esc(text)}</span>'

        cursor = self._log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._log.setTextCursor(cursor)
        self._log.insertHtml(line + "<br>")

        self._line_count += 1
        if self._line_count > self.MAX_LINES:
            self._trim_log()

        # Auto-scroll
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear_log(self):
        self._log.clear()
        self._line_count = 0
        self.log("◈ Log cleared.", "info")

    # ── SHELL COMMAND ────────────────────────────────────────
    def _on_run_cmd(self):
        cmd = self._cmd_input.text().strip()
        if not cmd:
            return
        self._cmd_input.clear()

        if self._shell_worker and self._shell_worker.isRunning():
            self.log("⚠ A command is already running.", "warn")
            return

        self.log(f"{cmd}", "cmd")

        self._shell_worker = ShellWorker(cmd)
        self._shell_worker.output_line.connect(
            lambda text, lvl: self.log(text, lvl)
        )
        self._shell_worker.finished.connect(self._on_cmd_done)
        self._shell_worker.start()

    def _on_cmd_done(self, code: int):
        if code == 0:
            self.log(f"Process exited OK (0)", "ok")
        else:
            self.log(f"Process exited with code {code}", "error")

    # ── HELPERS ──────────────────────────────────────────────
    def _trim_log(self):
        """Remove oldest lines to stay within MAX_LINES."""
        doc = self._log.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(200):
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self._line_count -= 200

    @staticmethod
    def _esc(text: str) -> str:
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
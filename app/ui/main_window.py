# ============================================================
# SHADOWFORGE OS — MAIN WINDOW (PyQt6)
# Central UI hub. Chat panel, file tree, terminal, model selector.
# ============================================================

import sys
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QLabel, QFrame,
    QMenuBar, QMenu, QMessageBox, QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QFont

from core.logger import get_logger
from core.constants import (
    APP_NAME, APP_VERSION,
    UI_WINDOW_MIN_WIDTH, UI_WINDOW_MIN_HEIGHT,
    UI_WINDOW_TITLE, WORKSPACE_DIR,
)

logger = get_logger("UI.MainWindow")


# ── AGENT WORKER THREAD ───────────────────────────────────────
class AgentWorker(QThread):
    """Runs agent.process() in background thread."""
    response_ready  = pyqtSignal(str, str, str)   # content, provider, model
    error_occurred  = pyqtSignal(str)
    file_written    = pyqtSignal(str)
    state_changed   = pyqtSignal(str)

    def __init__(self, agent, prompt: str, workspace: Path):
        super().__init__()
        self.agent     = agent
        self.prompt    = prompt
        self.workspace = workspace

    def run(self):
        try:
            def listener(event, data):
                if event == "state_change":
                    self.state_changed.emit(data.get("state", ""))
                elif event == "file_written":
                    self.file_written.emit(data.get("path", ""))

            self.agent.add_listener(listener)
            result = self.agent.process(
                user_input = self.prompt,
                workspace  = self.workspace,
            )
            self.agent.remove_listener(listener)

            if result.success:
                self.response_ready.emit(
                    result.content,
                    result.provider,
                    result.model,
                )
            else:
                self.error_occurred.emit(result.error or "Unknown error")
        except Exception as e:
            self.error_occurred.emit(str(e))


# ── MAIN WINDOW ────────────────────────────────────────────────
class MainWindow(QMainWindow):
    """
    ShadowForge OS — Main Application Window.

    Layout:
    ┌─────────────────────────────────────────────┐
    │  MenuBar                                    │
    ├──────────┬──────────────────┬───────────────┤
    │ FileTree │   Chat Panel     │ Model Selector│
    │          │                  │               │
    │          ├──────────────────┤               │
    │          │ Terminal Panel   │               │
    └──────────┴──────────────────┴───────────────┘
    │  StatusBar                                  │
    └─────────────────────────────────────────────┘
    """

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config    = config
        self._agent    = None
        self._worker:  Optional[AgentWorker] = None
        self._workspace = WORKSPACE_DIR

        self._setup_window()
        self._build_menu()
        self._build_ui()
        self._build_status_bar()
        self._init_agent()
        self._start_status_timer()

        logger.info("MainWindow initialized.")

    # ── WINDOW SETUP ──────────────────────────────────────────
    def _setup_window(self):
        self.setWindowTitle(UI_WINDOW_TITLE)
        self.setMinimumSize(UI_WINDOW_MIN_WIDTH, UI_WINDOW_MIN_HEIGHT)
        self.resize(1280, 800)
        self.setObjectName("MainWindow")

    # ── MENU BAR ──────────────────────────────────────────────
    def _build_menu(self):
        menubar = self.menuBar()
        menubar.setObjectName("MenuBar")

        # File menu
        file_menu = menubar.addMenu("&File")

        new_project = QAction("&New Project", self)
        new_project.setShortcut(QKeySequence("Ctrl+N"))
        new_project.triggered.connect(self._on_new_project)
        file_menu.addAction(new_project)

        open_workspace = QAction("&Open Workspace", self)
        open_workspace.setShortcut(QKeySequence("Ctrl+O"))
        open_workspace.triggered.connect(self._on_open_workspace)
        file_menu.addAction(open_workspace)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        clear_chat = QAction("Clear &Chat", self)
        clear_chat.setShortcut(QKeySequence("Ctrl+L"))
        clear_chat.triggered.connect(self._on_clear_chat)
        edit_menu.addAction(clear_chat)

        # View menu
        view_menu = menubar.addMenu("&View")

        toggle_tree = QAction("Toggle &File Tree", self)
        toggle_tree.setShortcut(QKeySequence("Ctrl+B"))
        toggle_tree.triggered.connect(self._toggle_file_tree)
        view_menu.addAction(toggle_tree)

        toggle_terminal = QAction("Toggle &Terminal", self)
        toggle_terminal.setShortcut(QKeySequence("Ctrl+`"))
        toggle_terminal.triggered.connect(self._toggle_terminal)
        view_menu.addAction(toggle_terminal)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about = QAction("&About", self)
        about.triggered.connect(self._on_about)
        help_menu.addAction(about)

    # ── MAIN UI ───────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Main horizontal splitter ──────────────────────────
        self._h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._h_splitter.setObjectName("HSplitter")
        self._h_splitter.setHandleWidth(2)
        main_layout.addWidget(self._h_splitter)

        # ── LEFT: File tree ───────────────────────────────────
        from ui.components.file_tree import FileTreePanel
        self._file_tree = FileTreePanel(workspace=self._workspace)
        self._file_tree.setObjectName("FileTreePanel")
        self._file_tree.file_opened.connect(self._on_file_opened)
        self._h_splitter.addWidget(self._file_tree)

        # ── CENTER: Chat + Terminal (vertical splitter) ───────
        center_widget = QWidget()
        center_widget.setObjectName("CenterWidget")
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self._v_splitter = QSplitter(Qt.Orientation.Vertical)
        self._v_splitter.setObjectName("VSplitter")
        self._v_splitter.setHandleWidth(2)
        center_layout.addWidget(self._v_splitter)

        # Chat panel
        from ui.components.chat_panel import ChatPanel
        self._chat_panel = ChatPanel()
        self._chat_panel.setObjectName("ChatPanel")
        self._chat_panel.message_submitted.connect(self._on_user_message)
        self._v_splitter.addWidget(self._chat_panel)

        # Terminal panel
        from ui.components.terminal_panel import TerminalPanel
        self._terminal = TerminalPanel()
        self._terminal.setObjectName("TerminalPanel")
        self._v_splitter.addWidget(self._terminal)

        # Splitter proportions: chat 70%, terminal 30%
        self._v_splitter.setSizes([560, 240])

        self._h_splitter.addWidget(center_widget)

        # ── RIGHT: Model selector ─────────────────────────────
        from ui.components.model_selector import ModelSelectorPanel
        self._model_selector = ModelSelectorPanel(config=self.config)
        self._model_selector.setObjectName("ModelSelectorPanel")
        self._model_selector.provider_changed.connect(self._on_provider_changed)
        self._h_splitter.addWidget(self._model_selector)

        # Splitter proportions: tree 220, center flex, right 240
        self._h_splitter.setSizes([220, 820, 240])

    # ── STATUS BAR ────────────────────────────────────────────
    def _build_status_bar(self):
        status = QStatusBar()
        status.setObjectName("StatusBar")
        self.setStatusBar(status)

        self._status_state = QLabel("◈ IDLE")
        self._status_state.setObjectName("StatusState")
        status.addWidget(self._status_state)

        status.addPermanentWidget(QLabel(" | "))

        self._status_provider = QLabel("Provider: —")
        self._status_provider.setObjectName("StatusProvider")
        status.addPermanentWidget(self._status_provider)

        status.addPermanentWidget(QLabel(" | "))

        self._status_workspace = QLabel(f"Workspace: {self._workspace}")
        self._status_workspace.setObjectName("StatusWorkspace")
        status.addPermanentWidget(self._status_workspace)

    # ── AGENT INIT ────────────────────────────────────────────
    def _init_agent(self):
        try:
            from agent.agent_core import AgentCore
            self._agent = AgentCore(config=self.config)
            self._agent.add_listener(self._on_agent_event)
            self._terminal.log("◈ Agent core initialized.", "info")
            logger.info("Agent initialized in UI.")
        except Exception as e:
            logger.error(f"Agent init failed: {e}")
            self._terminal.log(f"✗ Agent init failed: {e}", "error")

    # ── STATUS TIMER ──────────────────────────────────────────
    def _start_status_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_status)
        self._timer.start(5000)  # Every 5 seconds

    def _update_status(self):
        if self._agent:
            state = self._agent.state.value if self._agent else "idle"
            self._status_state.setText(f"◈ {state.upper()}")

    # ── EVENT HANDLERS ────────────────────────────────────────
    def _on_user_message(self, text: str):
        """User submitted a message in chat panel."""
        if not self._agent:
            self._chat_panel.add_message(
                "✗ Agent not initialized. Check your .env file.",
                role="error"
            )
            return

        if self._worker and self._worker.isRunning():
            self._chat_panel.add_message(
                "⚠ Agent is busy. Please wait...",
                role="system"
            )
            return

        self._chat_panel.add_message(text, role="user")
        self._status_state.setText("◈ THINKING...")
        self._terminal.log(f"→ Processing: {text[:60]}...", "info")

        # Run in background
        self._worker = AgentWorker(
            agent     = self._agent,
            prompt    = text,
            workspace = self._workspace,
        )
        self._worker.response_ready.connect(self._on_response)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.file_written.connect(self._on_file_written)
        self._worker.state_changed.connect(self._on_state_changed)
        self._worker.start()

    def _on_response(self, content: str, provider: str, model: str):
        self._chat_panel.add_message(content, role="assistant")
        self._status_provider.setText(f"Provider: {provider} / {model}")
        self._status_state.setText("◈ IDLE")
        self._terminal.log(f"✓ Response from {provider}/{model}", "ok")
        self._file_tree.refresh()

    def _on_error(self, error: str):
        self._chat_panel.add_message(f"✗ Error: {error}", role="error")
        self._status_state.setText("◈ ERROR")
        self._terminal.log(f"✗ {error}", "error")

    def _on_file_written(self, path: str):
        self._terminal.log(f"✓ File written: {path}", "ok")
        self._file_tree.refresh()

    def _on_state_changed(self, state: str):
        self._status_state.setText(f"◈ {state.upper()}")

    def _on_agent_event(self, event: str, data: dict):
        if event == "thinking_start":
            self._terminal.log("◈ Thinking...", "info")
        elif event == "build_complete":
            self._terminal.log("✓ Build complete!", "ok")

    def _on_file_opened(self, path: str):
        self._terminal.log(f"◈ Opened: {path}", "info")

    def _on_provider_changed(self, provider: str):
        self._terminal.log(f"◈ Provider switched: {provider}", "info")
        self._status_provider.setText(f"Provider: {provider}")

    # ── MENU ACTIONS ──────────────────────────────────────────
    def _on_new_project(self):
        self._chat_panel.add_message(
            "Tell me about your new project. What do you want to build?",
            role="system"
        )
        self._chat_panel.focus_input()

    def _on_open_workspace(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Workspace Directory",
            str(self._workspace)
        )
        if folder:
            self._workspace = Path(folder)
            self._file_tree.set_workspace(self._workspace)
            self._status_workspace.setText(f"Workspace: {self._workspace}")
            self._terminal.log(f"◈ Workspace: {folder}", "info")

    def _on_clear_chat(self):
        self._chat_panel.clear()
        if self._agent:
            self._agent.clear_history()
        self._terminal.log("◈ Chat history cleared.", "info")

    def _toggle_file_tree(self):
        visible = self._file_tree.isVisible()
        self._file_tree.setVisible(not visible)

    def _toggle_terminal(self):
        visible = self._terminal.isVisible()
        self._terminal.setVisible(not visible)

    def _on_about(self):
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>AI-powered project generator and development assistant.</p>"
            f"<p>Built with PyQt6 + Multiple AI Providers.</p>"
        )

    # ── CLOSE ─────────────────────────────────────────────────
    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        if self._timer:
            self._timer.stop()
        logger.info("MainWindow closed.")
        event.accept()
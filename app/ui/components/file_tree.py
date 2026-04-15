# ============================================================
# SHADOWFORGE OS — FILE TREE PANEL
# Left sidebar: workspace directory browser.
# Shows files, allows opening, refreshing.
# ============================================================

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTreeWidget, QTreeWidgetItem, QPushButton,
    QMenu, QMessageBox, QInputDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QAction

from core.logger import get_logger

logger = get_logger("UI.FileTree")

# File extension → icon mapping (text symbols)
EXT_ICONS = {
    ".py":    "🐍",
    ".js":    "📜",
    ".ts":    "📘",
    ".html":  "🌐",
    ".css":   "🎨",
    ".json":  "📋",
    ".md":    "📄",
    ".txt":   "📝",
    ".env":   "🔑",
    ".yaml":  "⚙️",
    ".yml":   "⚙️",
    ".toml":  "⚙️",
    ".sh":    "💻",
    ".bat":   "💻",
    ".exe":   "⚙️",
    ".zip":   "📦",
    ".png":   "🖼️",
    ".jpg":   "🖼️",
    ".svg":   "🖼️",
}

IGNORED_DIRS = {
    "__pycache__", ".git", "node_modules",
    ".venv", "venv", ".idea", ".vscode",
    "dist", "build", ".mypy_cache",
}


class FileTreePanel(QWidget):
    """
    Workspace file browser panel.

    Signals:
        file_opened(path: str)  — emitted when user double-clicks a file
    """

    file_opened = pyqtSignal(str)

    def __init__(self, workspace: Path, parent=None):
        super().__init__(parent)
        self._workspace = workspace
        self.setObjectName("FileTreePanel")
        self.setMinimumWidth(180)
        self.setMaximumWidth(320)
        self._build_ui()
        self.refresh()

    # ── UI BUILD ─────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_row = QWidget()
        header_row.setObjectName("FileTreeHeader")
        header_row.setFixedHeight(36)
        header_row.setStyleSheet("""
            QWidget#FileTreeHeader {
                background: #070010;
                border-bottom: 1px solid rgba(102,0,204,0.15);
            }
        """)
        h_layout = QHBoxLayout(header_row)
        h_layout.setContentsMargins(8, 0, 4, 0)

        title = QLabel("◈ FILES")
        title.setFont(QFont("Share Tech Mono", 9))
        title.setStyleSheet("color: #5a4070; letter-spacing: 2px;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        refresh_btn = QPushButton("↺")
        refresh_btn.setFixedSize(24, 24)
        refresh_btn.setToolTip("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #5a4070;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover { color: #6600cc; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        h_layout.addWidget(refresh_btn)

        layout.addWidget(header_row)

        # Workspace label
        self._ws_label = QLabel()
        self._ws_label.setObjectName("WSLabel")
        self._ws_label.setFont(QFont("Share Tech Mono", 7))
        self._ws_label.setStyleSheet("""
            QLabel {
                color: #3a2550;
                background: #05010a;
                padding: 4px 8px;
                border-bottom: 1px solid rgba(102,0,204,0.08);
            }
        """)
        self._ws_label.setWordWrap(True)
        layout.addWidget(self._ws_label)

        # Tree widget
        self._tree = QTreeWidget()
        self._tree.setObjectName("FileTree")
        self._tree.setHeaderHidden(True)
        self._tree.setAnimated(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(14)
        self._tree.setFont(QFont("Share Tech Mono", 9))
        self._tree.setStyleSheet("""
            QTreeWidget {
                background: #05010a;
                color: #9070c0;
                border: none;
                outline: none;
            }
            QTreeWidget::item {
                padding: 2px 0px;
                border-radius: 2px;
            }
            QTreeWidget::item:hover {
                background: rgba(102,0,204,0.1);
                color: #c0a0f0;
            }
            QTreeWidget::item:selected {
                background: rgba(102,0,204,0.2);
                color: #f0e8ff;
            }
            QTreeWidget::branch {
                background: #05010a;
            }
            QScrollBar:vertical {
                width: 4px;
                background: #05010a;
            }
            QScrollBar::handle:vertical {
                background: #2d0057;
                border-radius: 2px;
            }
        """)

        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)

        layout.addWidget(self._tree)

    # ── PUBLIC API ───────────────────────────────────────────
    def set_workspace(self, path: Path):
        """Change the workspace root directory."""
        self._workspace = path
        self.refresh()

    def refresh(self):
        """Reload the file tree from disk."""
        self._tree.clear()
        self._ws_label.setText(f"  {self._workspace.name}/")

        if not self._workspace.exists():
            item = QTreeWidgetItem(["(workspace not found)"])
            item.setForeground(0, QColor("#ff0015"))
            self._tree.addTopLevelItem(item)
            return

        try:
            self._populate(self._tree.invisibleRootItem(), self._workspace)
        except Exception as e:
            logger.error(f"FileTree refresh error: {e}")

    # ── TREE POPULATION ──────────────────────────────────────
    def _populate(self, parent_item, directory: Path, depth: int = 0):
        """Recursively populate tree items."""
        if depth > 8:
            return

        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except PermissionError:
            return

        for entry in entries:
            if entry.name.startswith(".") and entry.name not in (".env",):
                continue
            if entry.is_dir() and entry.name in IGNORED_DIRS:
                continue

            item = QTreeWidgetItem()
            item.setData(0, Qt.ItemDataRole.UserRole, str(entry))

            if entry.is_dir():
                item.setText(0, f"📁 {entry.name}/")
                item.setForeground(0, QColor("#7a50a0"))
                self._populate(item, entry, depth + 1)
            else:
                icon = EXT_ICONS.get(entry.suffix.lower(), "📄")
                size  = self._fmt_size(entry.stat().st_size)
                item.setText(0, f"{icon} {entry.name}")
                item.setToolTip(0, f"{entry} ({size})")
                item.setForeground(0, QColor("#9070c0"))

            if isinstance(parent_item, QTreeWidgetItem):
                parent_item.addChild(item)
            else:
                self._tree.addTopLevelItem(item)

        # Auto-expand first level
        if depth == 0:
            self._tree.expandToDepth(0)

    # ── EVENTS ───────────────────────────────────────────────
    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and Path(path).is_file():
            self.file_opened.emit(path)
            logger.debug(f"File opened: {path}")

    def _on_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #0d0018;
                color: #c0a0f0;
                border: 1px solid #2d0057;
                border-radius: 3px;
            }
            QMenu::item:selected { background: rgba(102,0,204,0.2); }
        """)

        refresh_act = QAction("↺ Refresh", self)
        refresh_act.triggered.connect(self.refresh)
        menu.addAction(refresh_act)

        if item:
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if path and Path(path).is_file():
                menu.addSeparator()
                copy_act = QAction("⎘ Copy Path", self)
                copy_act.triggered.connect(
                    lambda: self._copy_path(path)
                )
                menu.addAction(copy_act)

                delete_act = QAction("✕ Delete File", self)
                delete_act.triggered.connect(
                    lambda: self._delete_file(path)
                )
                menu.addAction(delete_act)

        menu.exec(self._tree.mapToGlobal(pos))

    def _copy_path(self, path: str):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(path)

    def _delete_file(self, path: str):
        reply = QMessageBox.question(
            self, "Delete File",
            f"Delete {Path(path).name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Path(path).unlink()
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    # ── HELPERS ──────────────────────────────────────────────
    @staticmethod
    def _fmt_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / 1024 ** 2:.1f} MB"
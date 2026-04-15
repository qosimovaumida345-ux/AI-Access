# ============================================================
# SHADOWFORGE OS — SPLASH SCREEN
# Cinematic loading screen shown on startup.
# ============================================================

from PyQt6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen

from core.constants import APP_NAME, APP_VERSION
from core.logger import get_logger

logger = get_logger("UI.SplashScreen")


class SplashScreen(QSplashScreen):
    """
    Dark splash screen with animated progress text.
    Shows while the main window initializes.
    """

    def __init__(self):
        # Create dark background pixmap
        pixmap = self._create_pixmap()
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlags(
            Qt.WindowType.SplashScreen |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )

        self._messages = [
            "Initializing kernel...",
            "Loading AI providers...",
            "Configuring sandbox...",
            "Preparing agent core...",
            "Building UI components...",
            "System ready.",
        ]
        self._msg_idx = 0

        # Status label
        self._status = "Starting ShadowForge OS..."
        self._counter = 0

        # Animate messages
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._cycle_message)
        self._timer.start(400)

        logger.info("SplashScreen displayed.")

    def _create_pixmap(self) -> QPixmap:
        """Create the splash screen background."""
        w, h = 480, 280
        pixmap = QPixmap(w, h)
        pixmap.fill(QColor("#03000a"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Border
        pen = QPen(QColor("#6600cc"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(0, 0, w - 1, h - 1)

        # Top accent line (red)
        pen.setColor(QColor("#ff0015"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(0, 0, w, 0)

        # App name
        font = QFont("Rajdhani", 28, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#f0e8ff"))
        painter.drawText(40, 90, APP_NAME)

        # Version
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#5a4070"))
        painter.drawText(40, 115, f"v{APP_VERSION} — OBSIDIAN KERNEL")

        # Triangle logo (simple)
        pen.setColor(QColor("#ff0015"))
        pen.setWidth(1)
        painter.setPen(pen)
        points = [
            (380, 60), (420, 130), (340, 130)
        ]
        from PyQt6.QtCore import QPoint
        from PyQt6.QtGui import QPolygon
        poly = QPolygon([QPoint(x, y) for x, y in points])
        painter.drawPolygon(poly)

        painter.end()
        return pixmap

    def _cycle_message(self):
        """Cycle through loading messages."""
        if self._msg_idx < len(self._messages):
            msg = self._messages[self._msg_idx]
            self.showMessage(
                f"  ◈ {msg}",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
                QColor("#6600cc"),
            )
            self._msg_idx += 1
        else:
            self._timer.stop()

    def set_status(self, text: str):
        """Update status message."""
        self.showMessage(
            f"  ◈ {text}",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            QColor("#6600cc"),
        )
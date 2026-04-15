# ============================================================
# SHADOWFORGE OS — CHAT PANEL COMPONENT
# Main conversation interface. Markdown rendering. 
# User/Assistant/System message bubbles.
# ============================================================

import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QScrollArea, QLabel, QFrame,
    QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QKeyEvent, QFont, QTextCursor, QColor

from core.logger import get_logger

logger = get_logger("UI.ChatPanel")


class MessageBubble(QFrame):
    """A single chat message bubble."""

    ROLES = {
        "user":      {"bg": "#1a0030", "border": "#6600cc", "label": "YOU"},
        "assistant": {"bg": "#0d0018", "border": "#2d0057", "label": "FORGE"},
        "system":    {"bg": "#0a0010", "border": "#330033", "label": "SYS"},
        "error":     {"bg": "#1a0003", "border": "#ff0015", "label": "ERR"},
    }

    def __init__(self, text: str, role: str = "user", parent=None):
        super().__init__(parent)
        self.role = role
        style = self.ROLES.get(role, self.ROLES["system"])

        self.setObjectName(f"Bubble_{role}")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Role label
        role_label = QLabel(style["label"])
        role_label.setObjectName("BubbleRole")
        role_label.setFont(QFont("Share Tech Mono", 8))
        layout.addWidget(role_label)

        # Content
        content = QLabel()
        content.setObjectName("BubbleContent")
        content.setWordWrap(True)
        content.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        content.setFont(QFont("Rajdhani", 10))

        # Basic markdown rendering
        html = self._to_html(text)
        content.setText(html)
        content.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(content)

        # Style
        self.setStyleSheet(f"""
            QFrame {{
                background: {style['bg']};
                border: 1px solid {style['border']};
                border-radius: 4px;
                margin: 2px 0px;
            }}
            QLabel#BubbleRole {{
                color: {style['border']};
                font-size: 8px;
                letter-spacing: 2px;
                text-transform: uppercase;
            }}
            QLabel#BubbleContent {{
                color: #c0a8e0;
                font-size: 10pt;
                line-height: 1.6;
            }}
        """)

    def _to_html(self, text: str) -> str:
        """Basic markdown → HTML conversion."""
        # Escape HTML
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Code blocks
        text = re.sub(
            r'```(\w*)\n(.*?)```',
            r'<pre style="background:#05010a;color:#8888bb;padding:8px;'
            r'border-radius:3px;font-family:monospace;font-size:9pt;">'
            r'\2</pre>',
            text, flags=re.DOTALL
        )

        # Inline code
        text = re.sub(
            r'`([^`]+)`',
            r'<code style="background:#0d0018;color:#6600cc;'
            r'padding:1px 4px;border-radius:2px;">\1</code>',
            text
        )

        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

        # Line breaks
        text = text.replace('\n', '<br>')

        return text


class TypingIndicator(QLabel):
    """Animated typing indicator."""

    def __init__(self, parent=None):
        super().__init__("◈ FORGE IS THINKING...", parent)
        self.setObjectName("TypingIndicator")
        self.setFont(QFont("Share Tech Mono", 9))
        self.setStyleSheet("""
            QLabel {
                color: #6600cc;
                padding: 8px 16px;
                background: rgba(102,0,204,0.08);
                border: 1px solid rgba(102,0,204,0.2);
                border-radius: 3px;
            }
        """)
        self.hide()

        self._dots = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def _animate(self):
        self._dots = (self._dots + 1) % 4
        self.setText("◈ FORGE IS THINKING" + "." * self._dots)

    def show_typing(self):
        self.show()
        self._timer.start(400)

    def hide_typing(self):
        self.hide()
        self._timer.stop()


class ChatInputBox(QTextEdit):
    """Multi-line input box. Ctrl+Enter or Enter to send."""

    submit_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatInput")
        self.setPlaceholderText(
            "Type your prompt... (Enter to send, Shift+Enter for new line)"
        )
        self.setMaximumHeight(120)
        self.setMinimumHeight(60)
        self.setFont(QFont("Rajdhani", 10))
        self.setStyleSheet("""
            QTextEdit {
                background: #0d0018;
                color: #f0e8ff;
                border: 1px solid rgba(102,0,204,0.3);
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 10pt;
            }
            QTextEdit:focus {
                border-color: rgba(102,0,204,0.7);
            }
        """)

    def keyPressEvent(self, event: QKeyEvent):
        # Enter (without Shift) → submit
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and
                not event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            text = self.toPlainText().strip()
            if text:
                self.submit_requested.emit(text)
                self.clear()
        else:
            super().keyPressEvent(event)


class ChatPanel(QWidget):
    """
    Main chat interface panel.
    Displays conversation history and input box.
    """

    message_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatPanel")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel(f"  ◈ CONVERSATION")
        header.setObjectName("ChatHeader")
        header.setFixedHeight(36)
        header.setFont(QFont("Share Tech Mono", 9))
        header.setStyleSheet("""
            QLabel {
                background: #070010;
                color: #5a4070;
                border-bottom: 1px solid rgba(102,0,204,0.15);
                padding-left: 8px;
                letter-spacing: 2px;
            }
        """)
        layout.addWidget(header)

        # Scroll area for messages
        scroll = QScrollArea()
        scroll.setObjectName("ChatScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: #05010a; }
            QScrollBar:vertical { width: 4px; background: #05010a; }
            QScrollBar::handle:vertical { background: #2d0057; border-radius: 2px; }
        """)

        self._messages_widget = QWidget()
        self._messages_widget.setObjectName("MessagesWidget")
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(8, 8, 8, 8)
        self._messages_layout.setSpacing(6)
        self._messages_layout.addStretch()

        scroll.setWidget(self._messages_widget)
        self._scroll = scroll
        layout.addWidget(scroll)

        # Typing indicator
        self._typing = TypingIndicator()
        layout.addWidget(self._typing)

        # Input area
        input_widget = QWidget()
        input_widget.setObjectName("InputWidget")
        input_widget.setStyleSheet("""
            QWidget#InputWidget {
                background: #070010;
                border-top: 1px solid rgba(102,0,204,0.15);
            }
        """)
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(8)

        self._input = ChatInputBox()
        self._input.submit_requested.connect(self._on_submit)
        input_layout.addWidget(self._input)

        send_btn = QPushButton("SEND")
        send_btn.setObjectName("SendButton")
        send_btn.setFixedSize(QSize(70, 60))
        send_btn.setFont(QFont("Share Tech Mono", 8))
        send_btn.clicked.connect(self._on_send_click)
        send_btn.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #ff0015, #6600cc);
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover { background: #ff0015; }
            QPushButton:pressed { background: #cc0010; }
        """)
        input_layout.addWidget(send_btn)

        layout.addWidget(input_widget)

    def _on_submit(self, text: str):
        self.message_submitted.emit(text)
        self._typing.show_typing()

    def _on_send_click(self):
        text = self._input.toPlainText().strip()
        if text:
            self._input.clear()
            self._on_submit(text)

    def add_message(self, text: str, role: str = "user"):
        """Add a message bubble to the chat."""
        self._typing.hide_typing()

        bubble = MessageBubble(text, role)
        # Insert before the stretch
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, bubble)

        # Scroll to bottom
        QTimer.singleShot(
            50,
            lambda: self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()
            )
        )

    def clear(self):
        """Clear all messages."""
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def focus_input(self):
        self._input.setFocus()
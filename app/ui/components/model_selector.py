# ============================================================
# SHADOWFORGE OS — MODEL SELECTOR PANEL
# Right sidebar: choose AI provider + model.
# Shows live provider status and usage stats.
# ============================================================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFrame, QScrollArea,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from core.logger import get_logger

logger = get_logger("UI.ModelSelector")

# Provider → available models
PROVIDER_MODELS = {
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    "openrouter": [
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mixtral-8x7b-instruct",
        "anthropic/claude-3-haiku",
        "google/gemma-2-9b-it:free",
        "deepseek/deepseek-r1:free",
    ],
    "google": [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash-exp",
    ],
    "mistral": [
        "mistral-small-latest",
        "mistral-medium-latest",
        "open-mistral-7b",
        "open-mixtral-8x7b",
    ],
    "together": [
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "togethercomputer/CodeLlama-34b-Instruct",
    ],
    "huggingface": [
        "meta-llama/Meta-Llama-3-8B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.2",
        "HuggingFaceH4/zephyr-7b-beta",
    ],
    "fallback": [
        "auto (best available)",
    ],
}

# Provider → status color
PROVIDER_STATUS_COLORS = {
    "active":   "#00cc66",
    "idle":     "#6600cc",
    "error":    "#ff0015",
    "unknown":  "#5a4070",
}


class ProviderCard(QFrame):
    """Small card showing one provider's status."""

    clicked = pyqtSignal(str)  # provider name

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name   = name
        self.status = "unknown"
        self.setObjectName("ProviderCard")
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._dot = QLabel("●")
        self._dot.setFont(QFont("Share Tech Mono", 8))
        self._dot.setFixedWidth(14)
        layout.addWidget(self._dot)

        self._name_lbl = QLabel(self.name.upper())
        self._name_lbl.setFont(QFont("Share Tech Mono", 8))
        layout.addWidget(self._name_lbl)
        layout.addStretch()

        self._status_lbl = QLabel("—")
        self._status_lbl.setFont(QFont("Share Tech Mono", 7))
        layout.addWidget(self._status_lbl)

        self._update_style()

    def set_status(self, status: str, detail: str = ""):
        self.status = status
        self._status_lbl.setText(detail or status)
        self._update_style()

    def _update_style(self):
        color = PROVIDER_STATUS_COLORS.get(self.status, "#5a4070")
        self.setStyleSheet(f"""
            QFrame#ProviderCard {{
                background: #0a0015;
                border: 1px solid rgba(102,0,204,0.15);
                border-radius: 3px;
                margin: 1px 0px;
            }}
            QFrame#ProviderCard:hover {{
                border-color: rgba(102,0,204,0.4);
                background: #0f0020;
            }}
        """)
        self._dot.setStyleSheet(f"color: {color};")
        self._name_lbl.setStyleSheet(f"color: {color};")
        self._status_lbl.setStyleSheet("color: #3a2550;")

    def mousePressEvent(self, event):
        self.clicked.emit(self.name)
        super().mousePressEvent(event)


class ModelSelectorPanel(QWidget):
    """
    Right sidebar for selecting AI provider and model.

    Signals:
        provider_changed(name: str)
    """

    provider_changed = pyqtSignal(str)

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.setObjectName("ModelSelectorPanel")
        self.setMinimumWidth(200)
        self.setMaximumWidth(280)
        self._provider_cards: dict[str, ProviderCard] = {}
        self._build_ui()
        self._start_status_poll()

    # ── UI BUILD ─────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("  ◈ MODEL")
        header.setObjectName("ModelHeader")
        header.setFixedHeight(36)
        header.setFont(QFont("Share Tech Mono", 9))
        header.setStyleSheet("""
            QLabel {
                background: #070010;
                color: #5a4070;
                border-bottom: 1px solid rgba(102,0,204,0.15);
                letter-spacing: 2px;
            }
        """)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: #05010a; }
            QScrollBar:vertical { width: 4px; background: #05010a; }
            QScrollBar::handle:vertical { background: #2d0057; border-radius: 2px; }
        """)

        inner = QWidget()
        inner.setStyleSheet("background: #05010a;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(8, 8, 8, 8)
        inner_layout.setSpacing(10)

        # ── Provider selector ─────────────────────────────
        prov_lbl = QLabel("PROVIDER")
        prov_lbl.setFont(QFont("Share Tech Mono", 7))
        prov_lbl.setStyleSheet("color: #3a2550; letter-spacing: 2px;")
        inner_layout.addWidget(prov_lbl)

        self._provider_combo = QComboBox()
        self._provider_combo.setObjectName("ProviderCombo")
        self._provider_combo.addItems(list(PROVIDER_MODELS.keys()))
        self._provider_combo.setFont(QFont("Share Tech Mono", 9))
        self._provider_combo.setStyleSheet("""
            QComboBox {
                background: #0d0018;
                color: #c0a0f0;
                border: 1px solid #2d0057;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #0d0018;
                color: #c0a0f0;
                border: 1px solid #2d0057;
                selection-background-color: rgba(102,0,204,0.2);
            }
        """)
        self._provider_combo.currentTextChanged.connect(self._on_provider_change)
        inner_layout.addWidget(self._provider_combo)

        # ── Model selector ────────────────────────────────
        model_lbl = QLabel("MODEL")
        model_lbl.setFont(QFont("Share Tech Mono", 7))
        model_lbl.setStyleSheet("color: #3a2550; letter-spacing: 2px; margin-top: 4px;")
        inner_layout.addWidget(model_lbl)

        self._model_combo = QComboBox()
        self._model_combo.setObjectName("ModelCombo")
        self._model_combo.setFont(QFont("Share Tech Mono", 8))
        self._model_combo.setStyleSheet("""
            QComboBox {
                background: #0d0018;
                color: #9070c0;
                border: 1px solid #2d0057;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #0d0018;
                color: #9070c0;
                border: 1px solid #2d0057;
                selection-background-color: rgba(102,0,204,0.2);
            }
        """)
        inner_layout.addWidget(self._model_combo)

        # Apply button
        apply_btn = QPushButton("◈  APPLY")
        apply_btn.setObjectName("ApplyBtn")
        apply_btn.setFont(QFont("Share Tech Mono", 8))
        apply_btn.setFixedHeight(32)
        apply_btn.setStyleSheet("""
            QPushButton {
                background: rgba(102,0,204,0.15);
                color: #6600cc;
                border: 1px solid #2d0057;
                border-radius: 3px;
                letter-spacing: 1px;
            }
            QPushButton:hover { background: rgba(102,0,204,0.3); color: #c0a0f0; }
            QPushButton:pressed { background: rgba(102,0,204,0.5); }
        """)
        apply_btn.clicked.connect(self._on_apply)
        inner_layout.addWidget(apply_btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(102,0,204,0.15); margin: 4px 0px;")
        inner_layout.addWidget(sep)

        # ── Provider status cards ─────────────────────────
        status_lbl = QLabel("PROVIDERS")
        status_lbl.setFont(QFont("Share Tech Mono", 7))
        status_lbl.setStyleSheet("color: #3a2550; letter-spacing: 2px;")
        inner_layout.addWidget(status_lbl)

        for name in PROVIDER_MODELS.keys():
            card = ProviderCard(name)
            card.clicked.connect(self._on_card_click)
            self._provider_cards[name] = card
            inner_layout.addWidget(card)

        inner_layout.addStretch()

        # ── Info box ──────────────────────────────────────
        self._info_box = QLabel("")
        self._info_box.setObjectName("InfoBox")
        self._info_box.setWordWrap(True)
        self._info_box.setFont(QFont("Share Tech Mono", 7))
        self._info_box.setStyleSheet("""
            QLabel {
                color: #5a4070;
                background: #040008;
                border: 1px solid rgba(102,0,204,0.1);
                border-radius: 3px;
                padding: 6px;
                line-height: 1.5;
            }
        """)
        inner_layout.addWidget(self._info_box)

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        # Initialize model list
        self._on_provider_change(self._provider_combo.currentText())

    # ── EVENTS ───────────────────────────────────────────────
    def _on_provider_change(self, provider: str):
        models = PROVIDER_MODELS.get(provider, [])
        self._model_combo.clear()
        self._model_combo.addItems(models)
        logger.debug(f"Provider selected: {provider}")

    def _on_apply(self):
        provider = self._provider_combo.currentText()
        model    = self._model_combo.currentText()

        # Update config if available
        if self.config:
            try:
                self.config.set("provider", provider)
                self.config.set("model", model)
            except Exception:
                pass

        self.provider_changed.emit(provider)
        self._info_box.setText(
            f"Active:\n{provider}\n\n{model}"
        )
        logger.info(f"Provider applied: {provider} / {model}")

    def _on_card_click(self, provider: str):
        idx = self._provider_combo.findText(provider)
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)

    # ── STATUS POLLING ───────────────────────────────────────
    def _start_status_poll(self):
        """Poll provider status every 30 seconds."""
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_providers)
        self._poll_timer.start(30_000)
        # Initial poll after 2 seconds
        QTimer.singleShot(2000, self._poll_providers)

    def _poll_providers(self):
        """Check which providers are reachable."""
        import threading

        def check(name):
            try:
                # Quick DNS/TCP check — just mark active
                import socket
                hosts = {
                    "groq":        "api.groq.com",
                    "openrouter":  "openrouter.ai",
                    "google":      "generativelanguage.googleapis.com",
                    "mistral":     "api.mistral.ai",
                    "together":    "api.together.xyz",
                    "huggingface": "api-inference.huggingface.co",
                    "fallback":    "api.groq.com",
                }
                host = hosts.get(name, "api.groq.com")
                socket.setdefaulttimeout(3)
                socket.getaddrinfo(host, 443)
                return "idle"
            except Exception:
                return "error"

        for name, card in self._provider_cards.items():
            def _update(n=name, c=card):
                status = check(n)
                c.set_status(status, "online" if status == "idle" else "offline")

            t = threading.Thread(target=_update, daemon=True)
            t.start()

    # ── PUBLIC ───────────────────────────────────────────────
    def get_selected(self) -> tuple[str, str]:
        """Return (provider, model) currently selected."""
        return (
            self._provider_combo.currentText(),
            self._model_combo.currentText(),
        )

    def set_active(self, provider: str, model: str = ""):
        """Programmatically set the active provider."""
        idx = self._provider_combo.findText(provider)
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        if model:
            midx = self._model_combo.findText(model)
            if midx >= 0:
                self._model_combo.setCurrentIndex(midx)
        if provider in self._provider_cards:
            self._provider_cards[provider].set_status("active", "active")
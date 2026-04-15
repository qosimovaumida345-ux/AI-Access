# ============================================================
# SHADOWFORGE OS — ADVANCED LOGGING SYSTEM
# Colored console output + rotating file logs + UI log bridge.
# Every module uses this. Never print() — always log.
# ============================================================

import logging
import logging.handlers
import sys
import os
import re
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from collections import deque

# ── ANSI COLOR CODES ──────────────────────────────────────
class Colors:
    RESET      = "\033[0m"
    BOLD       = "\033[1m"
    DIM        = "\033[2m"

    BLACK      = "\033[30m"
    RED        = "\033[31m"
    GREEN      = "\033[32m"
    YELLOW     = "\033[33m"
    BLUE       = "\033[34m"
    MAGENTA    = "\033[35m"
    CYAN       = "\033[36m"
    WHITE      = "\033[37m"

    BRIGHT_RED     = "\033[91m"
    BRIGHT_GREEN   = "\033[92m"
    BRIGHT_YELLOW  = "\033[93m"
    BRIGHT_BLUE    = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN    = "\033[96m"
    BRIGHT_WHITE   = "\033[97m"

    BG_RED     = "\033[41m"
    BG_GREEN   = "\033[42m"
    BG_YELLOW  = "\033[43m"
    BG_BLUE    = "\033[44m"
    BG_MAGENTA = "\033[45m"


# ── LEVEL COLOR MAP ───────────────────────────────────────
LEVEL_COLORS = {
    logging.DEBUG:    Colors.DIM + Colors.CYAN,
    logging.INFO:     Colors.BRIGHT_WHITE,
    logging.WARNING:  Colors.BRIGHT_YELLOW,
    logging.ERROR:    Colors.BRIGHT_RED,
    logging.CRITICAL: Colors.BG_RED + Colors.BRIGHT_WHITE + Colors.BOLD,
}

LEVEL_ICONS = {
    logging.DEBUG:    "◦",
    logging.INFO:     "◈",
    logging.WARNING:  "⚠",
    logging.ERROR:    "✗",
    logging.CRITICAL: "☠",
}


# ── COLORED CONSOLE FORMATTER ─────────────────────────────
class ShadowConsoleFormatter(logging.Formatter):
    """
    Beautiful colored console formatter.
    Format: [TIME] ICON LEVEL | module | message
    """

    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color and self._supports_color()

    @staticmethod
    def _supports_color() -> bool:
        """Check if terminal supports ANSI colors."""
        if os.name == "nt":
            # Windows: check if ANSI is supported (Win10+)
            return os.environ.get("ANSICON") is not None or \
                   "TERM" in os.environ or \
                   "WT_SESSION" in os.environ  # Windows Terminal
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        # Time
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        # Level components
        level_color = LEVEL_COLORS.get(record.levelno, Colors.RESET)
        level_icon  = LEVEL_ICONS.get(record.levelno, "•")
        level_name  = record.levelname.ljust(8)

        # Module name (shorten)
        module = record.name
        if module.startswith("ShadowForge."):
            module = module[len("ShadowForge."):]
        module = module[:20].ljust(20)

        # Message
        message = record.getMessage()

        # Exception info
        exc_text = ""
        if record.exc_info:
            exc_text = "\n" + self.formatException(record.exc_info)

        if self.use_color:
            time_part  = f"{Colors.DIM}{time_str}{Colors.RESET}"
            icon_part  = f"{level_color}{level_icon}{Colors.RESET}"
            level_part = f"{level_color}{level_name}{Colors.RESET}"
            mod_part   = f"{Colors.BRIGHT_MAGENTA}{module}{Colors.RESET}"
            msg_part   = f"{level_color if record.levelno >= logging.WARNING else Colors.WHITE}{message}{Colors.RESET}"
        else:
            time_part  = time_str
            icon_part  = level_icon
            level_part = level_name
            mod_part   = module
            msg_part   = message

        return f"[{time_part}] {icon_part} {level_part} | {mod_part} | {msg_part}{exc_text}"


# ── CLEAN FILE FORMATTER ──────────────────────────────────
class ShadowFileFormatter(logging.Formatter):
    """
    Clean formatter for log files.
    No ANSI codes. JSON-structured entries.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Strip ANSI codes from message
        message = re.sub(r'\033\[[0-9;]*m', '', record.getMessage())

        entry = {
            "ts":      datetime.fromtimestamp(record.created).isoformat(),
            "level":   record.levelname,
            "module":  record.name,
            "func":    record.funcName,
            "line":    record.lineno,
            "msg":     message,
        }

        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False)


# ── IN-MEMORY LOG RING BUFFER ─────────────────────────────
class LogRingBuffer:
    """
    Thread-safe circular buffer that stores recent log entries.
    Used to display logs in the UI log panel without file I/O.
    """

    def __init__(self, maxlen: int = 500):
        self._buffer: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []

    def append(self, entry: Dict[str, Any]) -> None:
        with self._lock:
            self._buffer.append(entry)
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception:
                pass

    def get_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._buffer)

    def get_recent(self, n: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._buffer)[-n:]

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def add_listener(self, callback: Callable) -> None:
        """Register a callback that fires on every new log entry."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)


# ── UI BRIDGE HANDLER ─────────────────────────────────────
class UIBridgeHandler(logging.Handler):
    """
    Logging handler that pushes records into the LogRingBuffer.
    The UI log panel subscribes to the buffer for real-time updates.
    """

    def __init__(self, ring_buffer: LogRingBuffer):
        super().__init__()
        self._buffer = ring_buffer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Strip ANSI from message
            message = re.sub(r'\033\[[0-9;]*m', '', record.getMessage())

            entry = {
                "ts":      datetime.fromtimestamp(record.created).isoformat(),
                "level":   record.levelname,
                "module":  record.name,
                "func":    record.funcName,
                "line":    record.lineno,
                "msg":     message,
                "levelno": record.levelno,
            }

            if record.exc_info:
                entry["exception"] = self.formatException(record.exc_info)

            self._buffer.append(entry)
        except Exception:
            self.handleError(record)


# ── GLOBAL RING BUFFER INSTANCE ───────────────────────────
_global_ring_buffer = LogRingBuffer(maxlen=1000)


def get_log_buffer() -> LogRingBuffer:
    """Get the global log ring buffer (for UI panel)."""
    return _global_ring_buffer


# ── MAIN SETUP FUNCTION ───────────────────────────────────
def setup_logger(
    name:           str            = "ShadowForge",
    log_dir:        Optional[Path] = None,
    console_level:  int            = logging.DEBUG,
    file_level:     int            = logging.DEBUG,
    max_bytes:      int            = 1024 * 1024 * 5,   # 5MB
    backup_count:   int            = 3,
    use_color:      bool           = True,
) -> logging.Logger:
    """
    Configure and return the root ShadowForge logger.

    Call this ONCE at startup from main.py.
    All other modules get their logger via:
        logger = logging.getLogger("ShadowForge.ModuleName")
    """

    # Root logger
    root_logger = logging.getLogger(name)
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers (avoid duplicate output on re-init)
    if root_logger.handlers:
        root_logger.handlers.clear()

    # ── CONSOLE HANDLER ──────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ShadowConsoleFormatter(use_color=use_color))
    root_logger.addHandler(console_handler)

    # ── FILE HANDLER ─────────────────────────────────────
    if log_dir is None:
        from core.constants import LOGS_DIR
        log_dir = LOGS_DIR

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"shadowforge_{datetime.now().strftime('%Y%m%d')}.log"

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            filename     = log_file,
            maxBytes     = max_bytes,
            backupCount  = backup_count,
            encoding     = "utf-8",
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(ShadowFileFormatter())
        root_logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        root_logger.warning(f"Could not create log file at {log_file}: {e}")

    # ── UI BRIDGE HANDLER ─────────────────────────────────
    ui_handler = UIBridgeHandler(_global_ring_buffer)
    ui_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(ui_handler)

    # ── SUPPRESS NOISY THIRD-PARTY LOGGERS ───────────────
    for noisy in [
        "urllib3", "requests", "httpx", "httpcore",
        "asyncio", "websockets", "aiohttp",
        "PyQt6", "PIL", "matplotlib",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # ── STARTUP MESSAGE ───────────────────────────────────
    root_logger.info(f"Logger initialized — file: {log_file}")
    root_logger.info(f"Console level: {logging.getLevelName(console_level)}")
    root_logger.info(f"File level: {logging.getLevelName(file_level)}")

    return root_logger


# ── CONVENIENCE FUNCTION ──────────────────────────────────
def get_logger(module_name: str) -> logging.Logger:
    """
    Get a named logger for a specific module.

    Usage in any module:
        from core.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Hello")
    """
    return logging.getLogger(f"ShadowForge.{module_name}")


# ── LOG FILTER: HIDE SECRETS ──────────────────────────────
class SecretFilter(logging.Filter):
    """
    Filters out accidental secret logging.
    Masks API keys, tokens, passwords in log output.
    """

    SECRET_PATTERNS = [
        (re.compile(r'(sk-[a-zA-Z0-9]{20,})', re.I),      "sk-***MASKED***"),
        (re.compile(r'(gsk_[a-zA-Z0-9]{20,})', re.I),     "gsk_***MASKED***"),
        (re.compile(r'(gh[ps]_[a-zA-Z0-9]{20,})', re.I),  "ghp_***MASKED***"),
        (re.compile(r'(api[_\-]?key[=:\s]+)(\S+)', re.I), r"\1***MASKED***"),
        (re.compile(r'(token[=:\s]+)(\S+)', re.I),        r"\1***MASKED***"),
        (re.compile(r'(password[=:\s]+)(\S+)', re.I),     r"\1***MASKED***"),
        (re.compile(r'(secret[=:\s]+)(\S+)', re.I),       r"\1***MASKED***"),
        (re.compile(r'(Authorization:\s*Bearer\s+)(\S+)', re.I), r"\1***MASKED***"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.SECRET_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def add_secret_filter() -> None:
    """Add secret masking filter to all ShadowForge handlers."""
    logger = logging.getLogger("ShadowForge")
    secret_filter = SecretFilter()
    for handler in logger.handlers:
        handler.addFilter(secret_filter)


# ── PERFORMANCE TIMER ─────────────────────────────────────
class Timer:
    """
    Context manager for timing code blocks and logging duration.

    Usage:
        with Timer("Generate project", logger):
            do_heavy_work()
    """

    def __init__(self, label: str, logger: Optional[logging.Logger] = None):
        self.label = label
        self.logger = logger or logging.getLogger("ShadowForge.Timer")
        self._start: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self):
        import time
        self._start = time.perf_counter()
        self.logger.debug(f"⏱ START: {self.label}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        self.elapsed = time.perf_counter() - self._start
        level = logging.WARNING if self.elapsed > 5.0 else logging.INFO
        self.logger.log(
            level,
            f"⏱ DONE: {self.label} — {self.elapsed:.3f}s"
        )
        return False  # Don't suppress exceptions


# ── LOG EXPORT ────────────────────────────────────────────
def export_logs_to_file(output_path: Path, format: str = "jsonl") -> bool:
    """
    Export all buffered logs to a file.
    format: 'jsonl' or 'txt'
    """
    entries = _global_ring_buffer.get_all()
    if not entries:
        return False

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            if format == "jsonl":
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")
            else:
                for entry in entries:
                    f.write(
                        f"[{entry['ts']}] {entry['level']:8s} | "
                        f"{entry['module']} | {entry['msg']}\n"
                    )
        return True
    except Exception as e:
        logging.getLogger("ShadowForge.Logger").error(f"Log export failed: {e}")
        return False


# ── LOG STATS ─────────────────────────────────────────────
def get_log_stats() -> Dict[str, int]:
    """Return count of log entries by level."""
    entries = _global_ring_buffer.get_all()
    stats: Dict[str, int] = {
        "DEBUG": 0, "INFO": 0, "WARNING": 0,
        "ERROR": 0, "CRITICAL": 0,
    }
    for entry in entries:
        level = entry.get("level", "INFO")
        if level in stats:
            stats[level] += 1
    return stats
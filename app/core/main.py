# ============================================================
# SHADOWFORGE OS — MAIN APPLICATION ENTRY POINT
# Initializes all systems, starts GUI, handles shutdown.
# ============================================================

import sys
import os
import signal
import atexit
import logging
from pathlib import Path

# Ensure project root is in Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.config import Config
from core.logger import setup_logger
from core.constants import APP_NAME, APP_VERSION


def check_python_version():
    """Ensure Python 3.10+ is being used."""
    if sys.version_info < (3, 10):
        print(
            f"[ERROR] {APP_NAME} requires Python 3.10+. "
            f"You have {sys.version}. Aborting."
        )
        sys.exit(1)


def check_dependencies():
    """
    Auto-install missing dependencies.
    Uses the auto_installer module which handles pip safely.
    """
    try:
        from agent.auto_installer import AutoInstaller
        installer = AutoInstaller()
        installer.ensure_all()
    except ImportError:
        # auto_installer itself isn't available yet — bootstrap
        _bootstrap_auto_installer()


def _bootstrap_auto_installer():
    """Minimal bootstrap: install pip requirements if missing."""
    import subprocess
    requirements = ROOT_DIR / "requirements.txt"
    if requirements.exists():
        print("[ShadowForge] Bootstrapping dependencies...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-r", str(requirements),
                "--quiet", "--disable-pip-version-check",
            ])
            print("[ShadowForge] Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to install dependencies: {e}")
            sys.exit(1)


def setup_environment():
    """Load .env file and validate required keys."""
    config = Config()
    config.load()
    return config


def start_gui(config):
    """Launch the main PyQt6 application window."""
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import MainWindow
        from ui.splash_screen import SplashScreen
    except ImportError as e:
        logging.critical(f"PyQt6 not available: {e}")
        _fallback_cli_mode(config)
        return

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("ShadowForge")

    # Apply dark stylesheet
    _apply_stylesheet(app)

    # Show splash screen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # Initialize main window
    window = MainWindow(config=config)

    # Close splash and show main window
    import time
    time.sleep(2.5)
    splash.finish(window)
    window.show()

    # Run event loop
    exit_code = app.exec()
    sys.exit(exit_code)


def _apply_stylesheet(app):
    """Load and apply the dark QSS stylesheet."""
    try:
        qss_path = ROOT_DIR / "ui" / "styles" / "dark_theme.qss"
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
    except Exception as e:
        logging.warning(f"Could not load stylesheet: {e}")


def _fallback_cli_mode(config):
    """
    Fallback: run in CLI mode if GUI is unavailable.
    Useful for headless servers.
    """
    print(f"\n[{APP_NAME}] Running in CLI mode (no GUI available)\n")
    print("Type your prompt (or 'exit' to quit):\n")

    try:
        from agent.agent_core import AgentCore
        agent = AgentCore(config=config)

        while True:
            try:
                user_input = input("forge> ").strip()
                if user_input.lower() in ("exit", "quit", "q"):
                    break
                if not user_input:
                    continue
                response = agent.process(user_input)
                print(f"\n{response}\n")
            except KeyboardInterrupt:
                break

    except Exception as e:
        print(f"[ERROR] Agent failed to start: {e}")


def handle_shutdown(signum, frame):
    """Graceful shutdown handler."""
    logger = logging.getLogger(APP_NAME)
    logger.info("Received shutdown signal. Cleaning up...")
    sys.exit(0)


def cleanup():
    """Atexit cleanup function."""
    logger = logging.getLogger(APP_NAME)
    logger.info(f"{APP_NAME} shutdown complete.")


def main():
    """Main entry point."""
    # 1. Python version check
    check_python_version()

    # 2. Setup logger first
    logger = setup_logger()
    logger.info(f"{'='*50}")
    logger.info(f" {APP_NAME} v{APP_VERSION} — STARTING")
    logger.info(f"{'='*50}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Root: {ROOT_DIR}")

    # 3. Register shutdown handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    atexit.register(cleanup)

    # 4. Check & install dependencies
    logger.info("Checking dependencies...")
    check_dependencies()

    # 5. Load config & .env
    logger.info("Loading configuration...")
    config = setup_environment()

    # 6. Launch GUI (or CLI fallback)
    logger.info("Launching application...")
    start_gui(config)


if __name__ == "__main__":
    main()
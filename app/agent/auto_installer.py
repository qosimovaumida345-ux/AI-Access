# ============================================================
# SHADOWFORGE OS — AUTO LIBRARY INSTALLER
# Detects missing Python packages and installs them safely.
# Shows progress in UI. Never installs without user knowledge.
# Only installs from PyPI. No arbitrary code execution.
# ============================================================

import sys
import json
import subprocess
import threading
import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
import time

from core.logger import get_logger
from core.constants import REQUIRED_PACKAGES, OPTIONAL_PACKAGES

logger = get_logger("Agent.AutoInstaller")


# ── PACKAGE INFO ──────────────────────────────────────────
@dataclass
class PackageInfo:
    name:          str
    import_name:   str       # What to import (may differ from package name)
    version_min:   str  = ""
    required:      bool = True
    installed:     bool = False
    version:       str  = ""
    install_error: str  = ""
    skipped:       bool = False   # ← FIX: skipped field qo'shildi

    @property
    def display_name(self) -> str:
        return f"{self.name}" + (f">={self.version_min}" if self.version_min else "")


# ── PACKAGE MAP (install name -> import name) ─────────────
PACKAGE_IMPORT_MAP: Dict[str, str] = {
    "PyQt6":               "PyQt6",
    "requests":            "requests",
    "python-dotenv":       "dotenv",
    "openai":              "openai",
    "groq":                "groq",
    "PyGithub":            "github",
    "gitpython":           "git",
    "pyinstaller":         "PyInstaller",
    "speechrecognition":   "speech_recognition",
    "pyttsx3":             "pyttsx3",
    "pyaudio":             "pyaudio",
    "watchdog":            "watchdog",
    "rich":                "rich",
    "click":               "click",
    "httpx":               "httpx",
    "aiohttp":             "aiohttp",
    "websockets":          "websockets",
    "Pillow":              "PIL",
    "psutil":              "psutil",
    "playwright":          "playwright",
    "buildozer":           "buildozer",
    "briefcase":           "briefcase",
    "black":               "black",
    "pytest":              "pytest",
    "mypy":                "mypy",
    "together":            "together",
    "mistralai":           "mistralai",
    "cohere":              "cohere",
    "huggingface-hub":     "huggingface_hub",
    "google-generativeai": "google.generativeai",
    "anthropic":           "anthropic",
}

# Packages that need special handling (no simple import check)
SPECIAL_PACKAGES: Set[str] = {
    "pyinstaller",  # Imports as PyInstaller but used as CLI
    "buildozer",    # CLI tool
    "briefcase",    # CLI tool
}

# Packages known to be problematic on certain platforms
PLATFORM_ISSUES: Dict[str, List[str]] = {
    "pyaudio":   ["linux"],    # Needs portaudio-dev on Linux
    "buildozer": ["windows"],  # Not supported on Windows
}


# ── INSTALL RESULT ────────────────────────────────────────
@dataclass
class InstallResult:
    package:  str
    success:  bool
    version:  str   = ""
    error:    str   = ""
    duration: float = 0.0
    skipped:  bool  = False
    reason:   str   = ""


# ── AUTO INSTALLER CLASS ──────────────────────────────────
class AutoInstaller:
    """
    Safely detects and installs missing Python packages.

    Safety rules:
    1. Only installs from PyPI official index
    2. Never runs arbitrary shell commands
    3. Shows progress to user
    4. Allows user to deny installation
    5. Logs all install attempts
    6. Platform-aware (skips unsupported packages)
    """

    def __init__(
        self,
        progress_callback: Optional[Callable] = None,
        confirm_callback:  Optional[Callable] = None,
    ):
        """
        progress_callback(package_name, status, percent) -> None
        confirm_callback(packages_list) -> bool (user confirmed?)
        """
        self._progress_cb = progress_callback
        self._confirm_cb  = confirm_callback
        self._lock        = threading.Lock()
        self._install_log: List[InstallResult] = []
        self._platform    = sys.platform

        logger.info(f"AutoInstaller initialized. Platform: {self._platform}")

    # ── CHECK IF PACKAGE IS INSTALLED ─────────────────────
    def is_installed(self, package_name: str) -> Tuple[bool, str]:
        """
        Check if a package is installed and return (installed, version).
        """
        import_name = PACKAGE_IMPORT_MAP.get(package_name, package_name)

        # Special packages — check via importlib.util
        if package_name in SPECIAL_PACKAGES:
            spec = importlib.util.find_spec(import_name.split(".")[0])
            if spec is not None:
                return True, self._get_version(package_name)
            return False, ""

        # Standard import check
        try:
            parts = import_name.split(".")
            mod = importlib.import_module(parts[0])

            # Handle sub-module checks (e.g., google.generativeai)
            if len(parts) > 1:
                for part in parts[1:]:
                    mod = getattr(mod, part)

            version = self._get_version(package_name)
            return True, version

        except (ImportError, ModuleNotFoundError, AttributeError):
            return False, ""

    def _get_version(self, package_name: str) -> str:
        """Get installed version of a package."""
        try:
            from importlib.metadata import version
            return version(package_name)
        except Exception:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "show", package_name],
                    capture_output=True, text=True, timeout=10,
                )
                for line in result.stdout.splitlines():
                    if line.startswith("Version:"):
                        return line.split(":", 1)[1].strip()
            except Exception:
                pass
            return "unknown"

    # ── SCAN ALL PACKAGES ─────────────────────────────────
    def scan(self, packages: Optional[List[str]] = None) -> List[PackageInfo]:
        """
        Scan for installed/missing packages.
        Returns list of PackageInfo objects.
        """
        if packages is None:
            packages = REQUIRED_PACKAGES + OPTIONAL_PACKAGES

        results: List[PackageInfo] = []

        logger.info(f"Scanning {len(packages)} packages...")

        for pkg_name in packages:
            installed, version = self.is_installed(pkg_name)
            required = pkg_name in REQUIRED_PACKAGES

            # Platform-unsupported packages — mark as skipped
            is_skipped = self._is_platform_unsupported(pkg_name)

            info = PackageInfo(
                name        = pkg_name,
                import_name = PACKAGE_IMPORT_MAP.get(pkg_name, pkg_name),
                required    = required,
                installed   = installed,
                version     = version,
                skipped     = is_skipped,   # ← FIX: to'g'ri set qilinadi
            )
            results.append(info)

            if is_skipped:
                logger.debug(f"  {pkg_name.ljust(30)} ⊘ SKIPPED (platform)")
            else:
                status = f"✓ {version}" if installed else "✗ MISSING"
                level  = logging.DEBUG if installed else (
                    logging.WARNING if required else logging.DEBUG
                )
                logger.log(level, f"  {pkg_name.ljust(30)} {status}")

        missing_required = [
            p for p in results if not p.installed and p.required and not p.skipped
        ]
        missing_optional = [
            p for p in results if not p.installed and not p.required and not p.skipped
        ]

        logger.info(
            f"Scan complete: "
            f"{sum(1 for p in results if p.installed)} installed, "
            f"{len(missing_required)} missing required, "
            f"{len(missing_optional)} missing optional"
        )

        return results

    # ── INSTALL ONE PACKAGE ───────────────────────────────
    def install_one(
        self,
        package_name: str,
        version_spec: str  = "",
        upgrade:      bool = False,
    ) -> InstallResult:
        """
        Install a single package via pip.
        Returns InstallResult.
        """
        # Platform compatibility check
        if self._is_platform_unsupported(package_name):
            reason = f"Not supported on {self._platform}"
            logger.info(f"Skipping {package_name}: {reason}")
            return InstallResult(
                package = package_name,
                success = False,
                skipped = True,
                reason  = reason,
            )

        # Build pip command
        install_spec = package_name
        if version_spec:
            install_spec += version_spec

        cmd = [
            sys.executable, "-m", "pip", "install",
            install_spec,
            "--quiet",
            "--disable-pip-version-check",
            "--no-warn-script-location",
        ]

        if upgrade:
            cmd.append("--upgrade")

        logger.info(f"Installing: {install_spec}")
        self._notify_progress(package_name, "installing", 0)

        start_time = time.perf_counter()

        try:
            result = subprocess.run(
                cmd,
                capture_output = True,
                text           = True,
                timeout        = 120,  # 2 minute timeout per package
            )

            duration = time.perf_counter() - start_time

            if result.returncode == 0:
                # Verify installation
                installed, version = self.is_installed(package_name)
                if installed:
                    self._notify_progress(package_name, "done", 100)
                    logger.info(
                        f"Installed: {package_name} v{version} "
                        f"({duration:.1f}s)"
                    )
                    return InstallResult(
                        package  = package_name,
                        success  = True,
                        version  = version,
                        duration = duration,
                    )
                else:
                    error = "Install succeeded but package not importable"
                    self._notify_progress(package_name, "error", 0)
                    return InstallResult(
                        package  = package_name,
                        success  = False,
                        error    = error,
                        duration = duration,
                    )
            else:
                error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
                self._notify_progress(package_name, "error", 0)
                logger.error(f"Install failed for {package_name}: {error_msg}")
                return InstallResult(
                    package  = package_name,
                    success  = False,
                    error    = error_msg,
                    duration = duration,
                )

        except subprocess.TimeoutExpired:
            return InstallResult(
                package = package_name,
                success = False,
                error   = "Installation timed out (120s)",
            )
        except Exception as e:
            return InstallResult(
                package = package_name,
                success = False,
                error   = str(e),
            )

    # ── INSTALL MISSING ───────────────────────────────────
    def install_missing(
        self,
        packages:      Optional[List[str]] = None,
        required_only: bool = True,
    ) -> Dict[str, InstallResult]:
        """
        Scan and install all missing packages.
        Returns {package_name: InstallResult}.
        """
        scan_results = self.scan(packages)

        missing = [
            p for p in scan_results
            if not p.installed          # o'rnatilmagan
            and not p.skipped           # ← FIX: skipped endi PackageInfo'da bor
            and (not required_only or p.required)
        ]

        if not missing:
            logger.info("All required packages are installed.")
            return {}

        missing_names = [p.name for p in missing]
        logger.info(f"Installing {len(missing_names)} missing packages...")

        # Ask user if confirm callback is set
        if self._confirm_cb is not None:
            confirmed = self._confirm_cb(missing_names)
            if not confirmed:
                logger.info("User declined package installation.")
                return {
                    name: InstallResult(
                        package = name,
                        success = False,
                        skipped = True,
                        reason  = "user_declined",
                    )
                    for name in missing_names
                }

        results: Dict[str, InstallResult] = {}
        total = len(missing)

        for i, pkg_info in enumerate(missing):
            self._notify_progress(
                pkg_info.name, "installing",
                int((i / total) * 100),
            )
            result = self.install_one(pkg_info.name)
            results[pkg_info.name] = result

            with self._lock:
                self._install_log.append(result)

        # Summary
        success = sum(1 for r in results.values() if r.success)
        failed  = sum(1 for r in results.values() if not r.success and not r.skipped)
        skipped = sum(1 for r in results.values() if r.skipped)

        logger.info(
            f"Installation complete: {success} succeeded, "
            f"{failed} failed, "
            f"{skipped} skipped"
        )

        return results

    # ── ENSURE ALL ────────────────────────────────────────
    def ensure_all(self) -> bool:
        """
        Ensure all required packages are installed.
        Called at startup. Returns True if all OK.
        """
        logger.info("Ensuring all required packages are installed...")
        results = self.install_missing(required_only=True)

        if not results:
            logger.info("All packages OK.")
            return True

        failed = [
            name for name, r in results.items()
            if not r.success and not r.skipped
        ]

        if failed:
            logger.error(f"Failed to install: {', '.join(failed)}")
            return False

        return True

    # ── INSTALL FROM REQUIREMENTS.TXT ─────────────────────
    def install_requirements_file(self, req_path: Path) -> bool:
        """Install packages from a requirements.txt file."""
        if not req_path.exists():
            logger.warning(f"Requirements file not found: {req_path}")
            return False

        logger.info(f"Installing from: {req_path}")

        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pip", "install",
                    "-r", str(req_path),
                    "--quiet",
                    "--disable-pip-version-check",
                ],
                capture_output = True,
                text           = True,
                timeout        = 300,  # 5 minutes for full requirements
            )

            if result.returncode == 0:
                logger.info("Requirements installed successfully.")
                return True
            else:
                logger.error(f"Requirements install failed: {result.stderr[-500:]}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Requirements installation timed out.")
            return False
        except Exception as e:
            logger.error(f"Requirements install error: {e}")
            return False

    # ── PLATFORM CHECK ────────────────────────────────────
    def _is_platform_unsupported(self, package_name: str) -> bool:
        """Check if package is unsupported on current platform."""
        issues = PLATFORM_ISSUES.get(package_name, [])
        for platform_key in issues:
            if platform_key in self._platform:
                return True
        return False

    # ── PROGRESS NOTIFICATION ─────────────────────────────
    def _notify_progress(
        self, package: str, status: str, percent: int
    ) -> None:
        if self._progress_cb:
            try:
                self._progress_cb(package, status, percent)
            except Exception:
                pass

    # ── GET REPORT ────────────────────────────────────────
    def get_install_report(self) -> Dict[str, Any]:   # ← FIX: Any endi import qilingan
        """Get a summary report of all install operations."""
        with self._lock:
            return {
                "timestamp": datetime.now().isoformat(),
                "total":     len(self._install_log),
                "success":   sum(1 for r in self._install_log if r.success),
                "failed":    sum(
                    1 for r in self._install_log
                    if not r.success and not r.skipped
                ),
                "skipped":   sum(1 for r in self._install_log if r.skipped),
                "entries": [
                    {
                        "package":  r.package,
                        "success":  r.success,
                        "version":  r.version,
                        "error":    r.error,
                        "duration": round(r.duration, 2),
                        "skipped":  r.skipped,
                    }
                    for r in self._install_log
                ],
            }

    def save_report(self, path: Path) -> bool:
        """Save install report to JSON file."""
        try:
            report = self.get_install_report()
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Save report failed: {e}")
            return False

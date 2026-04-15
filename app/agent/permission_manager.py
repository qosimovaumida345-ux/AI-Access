# ============================================================
# SHADOWFORGE OS — PERMISSION MANAGER
# Fine-grained permission system for agent operations.
# Controls what the agent can and cannot do at runtime.
# ============================================================

import json
import logging
import threading
from pathlib import Path
from typing import Dict, Set, List, Optional, Any
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import get_logger
from core.constants import CONFIG_DIR

logger = get_logger("Agent.PermissionManager")


# ── PERMISSION TYPES ──────────────────────────────────────
class Permission(str, Enum):
    # File system
    READ_WORKSPACE      = "read_workspace"
    WRITE_WORKSPACE     = "write_workspace"
    DELETE_WORKSPACE    = "delete_workspace"
    READ_EXTERNAL       = "read_external"      # Read files outside workspace

    # Network
    NETWORK_API_CALLS   = "network_api_calls"
    NETWORK_DOWNLOAD    = "network_download"
    NETWORK_BROWSER     = "network_browser"    # Playwright/Selenium

    # System
    RUN_SUBPROCESS      = "run_subprocess"
    INSTALL_PACKAGES    = "install_packages"
    ACCESS_ENV_VARS     = "access_env_vars"
    MODIFY_SYSTEM       = "modify_system"      # ALWAYS DENIED

    # GitHub
    GITHUB_READ         = "github_read"
    GITHUB_WRITE        = "github_write"
    GITHUB_RELEASE      = "github_release"

    # Build
    BUILD_PACKAGE       = "build_package"
    DEPLOY_REMOTE       = "deploy_remote"

    # AI
    SUDO_MODE           = "sudo_mode"
    UNRESTRICTED_OUTPUT = "unrestricted_output"


class PermissionLevel(str, Enum):
    DENIED    = "denied"     # Never allowed
    PROMPT    = "prompt"     # Ask user before allowing
    ALLOWED   = "allowed"    # Always allowed
    SUDO_ONLY = "sudo_only"  # Only in sudo mode


@dataclass
class PermissionRule:
    permission: Permission
    level:      PermissionLevel
    reason:     str = ""
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None


# ── DEFAULT PERMISSION TABLE ──────────────────────────────
DEFAULT_PERMISSIONS: Dict[Permission, PermissionLevel] = {
    # File system
    Permission.READ_WORKSPACE:      PermissionLevel.ALLOWED,
    Permission.WRITE_WORKSPACE:     PermissionLevel.ALLOWED,
    Permission.DELETE_WORKSPACE:    PermissionLevel.PROMPT,
    Permission.READ_EXTERNAL:       PermissionLevel.PROMPT,

    # Network
    Permission.NETWORK_API_CALLS:   PermissionLevel.ALLOWED,
    Permission.NETWORK_DOWNLOAD:    PermissionLevel.ALLOWED,
    Permission.NETWORK_BROWSER:     PermissionLevel.PROMPT,

    # System
    Permission.RUN_SUBPROCESS:      PermissionLevel.PROMPT,
    Permission.INSTALL_PACKAGES:    PermissionLevel.ALLOWED,
    Permission.ACCESS_ENV_VARS:     PermissionLevel.ALLOWED,
    Permission.MODIFY_SYSTEM:       PermissionLevel.SUDO_ONLY,

    # GitHub
    Permission.GITHUB_READ:         PermissionLevel.ALLOWED,
    Permission.GITHUB_WRITE:        PermissionLevel.PROMPT,
    Permission.GITHUB_RELEASE:      PermissionLevel.PROMPT,

    # Build
    Permission.BUILD_PACKAGE:       PermissionLevel.ALLOWED,
    Permission.DEPLOY_REMOTE:       PermissionLevel.PROMPT,

    # AI modes
    Permission.SUDO_MODE:           PermissionLevel.ALLOWED,
    Permission.UNRESTRICTED_OUTPUT: PermissionLevel.SUDO_ONLY,
}

# Permissions that are ALWAYS denied, regardless of sudo
ALWAYS_DENIED: Set[Permission] = set()

# Permissions that require sudo
SUDO_REQUIRED: Set[Permission] = {
    Permission.UNRESTRICTED_OUTPUT,
    Permission.MODIFY_SYSTEM,
}


# ── PERMISSION REQUEST ────────────────────────────────────
@dataclass
class PermissionRequest:
    permission:  Permission
    operation:   str
    context:     str
    is_sudo:     bool = False
    request_id:  str = ""
    timestamp:   str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PermissionResult:
    granted:    bool
    permission: Permission
    level:      PermissionLevel
    reason:     str
    request_id: str = ""


# ── PERMISSION MANAGER ────────────────────────────────────
class PermissionManager:
    """
    Manages runtime permissions for the AI agent.

    All agent operations check permissions here first.
    Provides an audit trail and runtime override capability.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self._rules: Dict[Permission, PermissionRule] = {}
        self._session_grants: Dict[Permission, bool] = {}
        self._lock = threading.RLock()
        self._audit: List[Dict[str, Any]] = []
        self._prompt_callback = None  # UI prompt callback

        # Load config
        if config_path:
            self._config_path = config_path
        else:
            self._config_path = CONFIG_DIR / "permissions.json"

        self._load_defaults()
        self._load_from_file()

        logger.info(f"PermissionManager initialized. Rules: {len(self._rules)}")

    # ── LOAD DEFAULTS ─────────────────────────────────────
    def _load_defaults(self) -> None:
        with self._lock:
            for perm, level in DEFAULT_PERMISSIONS.items():
                self._rules[perm] = PermissionRule(
                    permission = perm,
                    level      = level,
                    reason     = "default",
                )

    # ── LOAD FROM FILE ────────────────────────────────────
    def _load_from_file(self) -> None:
        if not self._config_path.exists():
            logger.debug(f"No permissions config at: {self._config_path}")
            return

        try:
            with open(self._config_path, "r") as f:
                data = json.load(f)

            overrides = data.get("overrides", {})
            for perm_name, level_str in overrides.items():
                try:
                    perm  = Permission(perm_name)
                    level = PermissionLevel(level_str)

                    # Never override ALWAYS_DENIED
                    if perm in ALWAYS_DENIED:
                        logger.warning(
                            f"Cannot override ALWAYS_DENIED permission: {perm_name}"
                        )
                        continue

                    with self._lock:
                        self._rules[perm] = PermissionRule(
                            permission = perm,
                            level      = level,
                            reason     = "config_file",
                        )
                except ValueError:
                    logger.warning(f"Unknown permission in config: {perm_name}")

            logger.info(f"Loaded permission overrides from: {self._config_path}")

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not parse permissions config: {e}")
        except Exception as e:
            logger.error(f"Permission config load error: {e}")

    # ── CORE CHECK METHOD ─────────────────────────────────
    def check(
        self,
        permission: Permission,
        operation:  str    = "",
        context:    str    = "",
        is_sudo:    bool   = False,
    ) -> PermissionResult:
        """
        Check if a permission is granted.
        Returns PermissionResult with granted=True/False and reason.
        """
        # ALWAYS_DENIED — no exceptions
        if permission in ALWAYS_DENIED:
            result = PermissionResult(
                granted    = False,
                permission = permission,
                level      = PermissionLevel.DENIED,
                reason     = "This operation is permanently disabled for safety.",
            )
            self._record_audit(permission, False, operation, context, is_sudo)
            return result

        # Sudo-only permissions
        if permission in SUDO_REQUIRED and not is_sudo:
            result = PermissionResult(
                granted    = False,
                permission = permission,
                level      = PermissionLevel.SUDO_ONLY,
                reason     = "This operation requires sudo mode. Prefix with 'sudo'.",
            )
            self._record_audit(permission, False, operation, context, is_sudo)
            return result

        # Get rule
        with self._lock:
            rule = self._rules.get(
                permission,
                PermissionRule(
                    permission = permission,
                    level      = PermissionLevel.PROMPT,
                    reason     = "no_rule",
                )
            )

        # Check session grants (user already said yes this session)
        with self._lock:
            if self._session_grants.get(permission) is True:
                result = PermissionResult(
                    granted    = True,
                    permission = permission,
                    level      = rule.level,
                    reason     = "session_grant",
                )
                self._record_audit(permission, True, operation, context, is_sudo)
                return result

        # Apply level logic
        if rule.level == PermissionLevel.ALLOWED:
            granted = True
            reason  = "allowed_by_default"

        elif rule.level == PermissionLevel.DENIED:
            granted = False
            reason  = rule.reason or "denied_by_config"

        elif rule.level == PermissionLevel.SUDO_ONLY:
            granted = is_sudo
            reason  = "sudo_mode" if is_sudo else "requires_sudo"

        elif rule.level == PermissionLevel.PROMPT:
            # Ask user via callback if registered
            if self._prompt_callback is not None:
                user_answer = self._prompt_callback(permission, operation, context)
                granted = bool(user_answer)
                if granted:
                    with self._lock:
                        self._session_grants[permission] = True
                reason = "user_granted" if granted else "user_denied"
            else:
                # No UI callback — auto-allow in non-interactive mode
                granted = True
                reason  = "auto_allowed_no_ui"
        else:
            granted = False
            reason  = "unknown_level"

        result = PermissionResult(
            granted    = granted,
            permission = permission,
            level      = rule.level,
            reason     = reason,
        )

        self._record_audit(permission, granted, operation, context, is_sudo)

        if not granted:
            logger.warning(
                f"Permission DENIED: {permission.value} "
                f"for operation '{operation}' — {reason}"
            )
        else:
            logger.debug(f"Permission GRANTED: {permission.value} ({reason})")

        return result

    # ── CONVENIENCE METHODS ───────────────────────────────
    def can_write(self, is_sudo: bool = False) -> bool:
        return self.check(Permission.WRITE_WORKSPACE, is_sudo=is_sudo).granted

    def can_read_external(self, is_sudo: bool = False) -> bool:
        return self.check(Permission.READ_EXTERNAL, is_sudo=is_sudo).granted

    def can_run_subprocess(self, cmd: str = "", is_sudo: bool = False) -> bool:
        return self.check(
            Permission.RUN_SUBPROCESS,
            operation="subprocess",
            context=cmd[:100],
            is_sudo=is_sudo,
        ).granted

    def can_install_packages(self) -> bool:
        return self.check(Permission.INSTALL_PACKAGES).granted

    def can_use_github(self, write: bool = False) -> bool:
        perm = Permission.GITHUB_WRITE if write else Permission.GITHUB_READ
        return self.check(perm).granted

    def can_deploy(self) -> bool:
        return self.check(Permission.DEPLOY_REMOTE).granted

    def can_use_browser(self) -> bool:
        return self.check(Permission.NETWORK_BROWSER).granted

    def can_sudo_output(self, is_sudo: bool) -> bool:
        return self.check(Permission.UNRESTRICTED_OUTPUT, is_sudo=is_sudo).granted

    # ── RUNTIME OVERRIDES ─────────────────────────────────
    def grant(self, permission: Permission, session_only: bool = True) -> bool:
        """Manually grant a permission (for UI override)."""
        if permission in ALWAYS_DENIED:
            logger.warning(f"Cannot grant ALWAYS_DENIED: {permission.value}")
            return False

        with self._lock:
            if session_only:
                self._session_grants[permission] = True
            else:
                self._rules[permission] = PermissionRule(
                    permission = permission,
                    level      = PermissionLevel.ALLOWED,
                    reason     = "manually_granted",
                    granted_at = datetime.now().isoformat(),
                )

        logger.info(f"Permission GRANTED manually: {permission.value}")
        return True

    def revoke(self, permission: Permission) -> None:
        """Revoke a previously granted permission."""
        with self._lock:
            self._session_grants.pop(permission, None)
            if permission in self._rules:
                if permission not in ALWAYS_DENIED:
                    self._rules[permission] = PermissionRule(
                        permission = permission,
                        level      = DEFAULT_PERMISSIONS.get(
                            permission, PermissionLevel.PROMPT
                        ),
                        reason     = "revoked",
                    )
        logger.info(f"Permission REVOKED: {permission.value}")

    def reset_session_grants(self) -> None:
        """Clear all session-level grants (e.g., on new project)."""
        with self._lock:
            self._session_grants.clear()
        logger.info("Session permission grants cleared.")

    # ── UI CALLBACK ───────────────────────────────────────
    def set_prompt_callback(self, callback) -> None:
        """
        Set a callback function for PROMPT-level permissions.
        callback(permission, operation, context) -> bool
        """
        self._prompt_callback = callback
        logger.info("Permission prompt callback registered.")

    # ── AUDIT ─────────────────────────────────────────────
    def _record_audit(
        self,
        permission: Permission,
        granted:    bool,
        operation:  str,
        context:    str,
        is_sudo:    bool,
    ) -> None:
        entry = {
            "ts":         datetime.now().isoformat(),
            "permission": permission.value,
            "granted":    granted,
            "operation":  operation,
            "context":    context[:200],
            "is_sudo":    is_sudo,
        }
        with self._lock:
            self._audit.append(entry)
            if len(self._audit) > 2000:
                self._audit = self._audit[-1000:]

    def get_audit(self, last_n: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._audit[-last_n:])

    def get_summary(self) -> Dict[str, Any]:
        """Get permission summary for UI display."""
        with self._lock:
            return {
                "total_rules":     len(self._rules),
                "session_grants":  list(self._session_grants.keys()),
                "always_denied":   [p.value for p in ALWAYS_DENIED],
                "sudo_required":   [p.value for p in SUDO_REQUIRED],
                "audit_count":     len(self._audit),
                "rules": {
                    p.value: r.level.value
                    for p, r in self._rules.items()
                },
            }

    def save_config(self) -> bool:
        """Save current permission overrides to config file."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            overrides = {}
            with self._lock:
                for perm, rule in self._rules.items():
                    default = DEFAULT_PERMISSIONS.get(perm)
                    if rule.level != default:
                        overrides[perm.value] = rule.level.value

            data = {
                "version":   "2.5",
                "updated_at": datetime.now().isoformat(),
                "overrides":  overrides,
            }
            with open(self._config_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Permissions saved to: {self._config_path}")
            return True
        except Exception as e:
            logger.error(f"Save permissions failed: {e}")
            return False
# ============================================================
# SHADOWFORGE OS — SECURITY SANDBOX
# Controls ALL file system operations performed by the AI.
# The agent can ONLY write to the workspace directory.
# System files are NEVER touched.
# ============================================================

import os
import re
import shutil
import hashlib
import logging
import threading
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from core.constants import (
    SANDBOX_ALLOWED_WRITE_DIRS,
    SANDBOX_FORBIDDEN_PATHS,
    WORKSPACE_DIR,
    BUILDER_MAX_FILE_SIZE,
)
from core.logger import get_logger

logger = get_logger("Agent.Sandbox")


# ── AUDIT LOG ENTRY ───────────────────────────────────────
@dataclass
class AuditEntry:
    timestamp:  str
    operation:  str
    path:       str
    allowed:    bool
    reason:     str
    size_bytes: int = 0
    checksum:   str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts":        self.timestamp,
            "op":        self.operation,
            "path":      self.path,
            "allowed":   self.allowed,
            "reason":    self.reason,
            "size":      self.size_bytes,
            "checksum":  self.checksum,
        }


# ── SANDBOX VIOLATION ─────────────────────────────────────
class SandboxViolation(Exception):
    """Raised when an operation violates sandbox rules."""
    def __init__(self, operation: str, path: str, reason: str):
        self.operation = operation
        self.path      = path
        self.reason    = reason
        super().__init__(
            f"SANDBOX VIOLATION: {operation} on '{path}' blocked. Reason: {reason}"
        )


# ── MAIN SANDBOX CLASS ────────────────────────────────────
class Sandbox:
    """
    Enforces strict file system access controls for the AI agent.

    Rules:
    1. Write operations only allowed in WORKSPACE_DIR
    2. Read operations allowed anywhere EXCEPT forbidden paths
    3. System files are completely protected
    4. All operations are audited
    5. File size limits enforced
    6. Dangerous file extensions blocked
    """

    # File extensions the AI is never allowed to write
    BLOCKED_WRITE_EXTENSIONS = {
        ".exe", ".dll", ".so", ".dylib",
        ".bat", ".cmd", ".ps1",
        ".sh",   # Only in workspace
        ".sys", ".drv", ".inf",
        ".reg",
        ".plist",
    }

    # Max path depth to prevent deeply nested attacks
    MAX_PATH_DEPTH = 15

    def __init__(self, workspace: Optional[Path] = None):
        self._workspace = Path(workspace or WORKSPACE_DIR).resolve()
        self._workspace.mkdir(parents=True, exist_ok=True)

        self._audit_log: List[AuditEntry] = []
        self._lock = threading.RLock()
        self._operation_count: Dict[str, int] = {}

        logger.info(f"Sandbox initialized. Workspace: {self._workspace}")
        logger.info(f"Forbidden paths: {len(SANDBOX_FORBIDDEN_PATHS)}")

    # ── PATH VALIDATION ───────────────────────────────────
    def _resolve_safe(self, path: Path) -> Tuple[Path, str]:
        """
        Resolve a path safely without following symlinks blindly.
        Returns (resolved_path, error_message_or_empty).
        """
        try:
            # Don't use resolve() with strict=True as path may not exist yet
            resolved = Path(os.path.normpath(str(path))).absolute()
            return resolved, ""
        except Exception as e:
            return path, str(e)

    def _is_forbidden(self, path: Path) -> Tuple[bool, str]:
        """Check if a path is in the forbidden list."""
        path_str = str(path).lower()

        for forbidden in SANDBOX_FORBIDDEN_PATHS:
            try:
                forbidden_str = str(forbidden).lower()
                if path_str.startswith(forbidden_str):
                    return True, f"Path is in forbidden zone: {forbidden}"
            except Exception:
                continue

        return False, ""

    def _is_in_workspace(self, path: Path) -> bool:
        """Check if path is inside the sandbox workspace."""
        try:
            path.relative_to(self._workspace)
            return True
        except ValueError:
            return False

    def _check_path_depth(self, path: Path) -> bool:
        """Ensure path isn't too deeply nested."""
        try:
            rel = path.relative_to(self._workspace)
            return len(rel.parts) <= self.MAX_PATH_DEPTH
        except ValueError:
            return True  # Not in workspace, depth doesn't apply

    def _is_blocked_extension(self, path: Path) -> bool:
        """Check if file extension is on the blocked write list."""
        suffix = path.suffix.lower()
        return suffix in self.BLOCKED_WRITE_EXTENSIONS

    def _validate_write_path(self, path: Path) -> Tuple[bool, str]:
        """
        Full validation for write operations.
        Returns (allowed, reason).
        """
        resolved, err = self._resolve_safe(path)
        if err:
            return False, f"Path resolution error: {err}"

        # Must be inside workspace
        if not self._is_in_workspace(resolved):
            return False, (
                f"Write outside workspace blocked. "
                f"Path: {resolved} | Workspace: {self._workspace}"
            )

        # Must not be forbidden
        is_forbidden, reason = self._is_forbidden(resolved)
        if is_forbidden:
            return False, reason

        # Check depth
        if not self._check_path_depth(resolved):
            return False, f"Path too deeply nested (max {self.MAX_PATH_DEPTH} levels)"

        # Check extension (except .sh files inside workspace are OK)
        if self._is_blocked_extension(resolved):
            if resolved.suffix.lower() != ".sh":
                return False, f"Blocked file extension: {resolved.suffix}"

        return True, ""

    def _validate_read_path(self, path: Path) -> Tuple[bool, str]:
        """
        Validation for read operations.
        More permissive than writes, but still blocks system areas.
        """
        resolved, err = self._resolve_safe(path)
        if err:
            return False, f"Path resolution error: {err}"

        is_forbidden, reason = self._is_forbidden(resolved)
        if is_forbidden:
            return False, reason

        return True, ""

    # ── AUDIT ─────────────────────────────────────────────
    def _audit(
        self,
        operation:  str,
        path:       Path,
        allowed:    bool,
        reason:     str,
        size_bytes: int = 0,
        content:    str = "",
    ) -> None:
        """Record an operation in the audit log."""
        checksum = ""
        if content and allowed:
            checksum = hashlib.sha256(content.encode()).hexdigest()[:12]

        entry = AuditEntry(
            timestamp  = datetime.now().isoformat(),
            operation  = operation,
            path       = str(path),
            allowed    = allowed,
            reason     = reason,
            size_bytes = size_bytes,
            checksum   = checksum,
        )

        with self._lock:
            self._audit_log.append(entry)
            op_key = f"{operation}_{allowed}"
            self._operation_count[op_key] = self._operation_count.get(op_key, 0) + 1

        if not allowed:
            logger.warning(f"SANDBOX BLOCKED: {operation} on {path} — {reason}")
        else:
            logger.debug(f"SANDBOX ALLOWED: {operation} on {path}")

    # ── WRITE FILE ────────────────────────────────────────
    def write_file(
        self,
        path:     Path,
        content:  str,
        encoding: str = "utf-8",
    ) -> bool:
        """
        Write a file to the workspace.
        Returns True on success, False if blocked.
        """
        path = Path(path)

        # Validate
        allowed, reason = self._validate_write_path(path)

        if not allowed:
            self._audit("WRITE", path, False, reason)
            logger.error(f"Write blocked: {path} — {reason}")
            return False

        # Size check
        content_bytes = content.encode(encoding)
        if len(content_bytes) > BUILDER_MAX_FILE_SIZE:
            reason = f"File too large: {len(content_bytes)} bytes > {BUILDER_MAX_FILE_SIZE}"
            self._audit("WRITE", path, False, reason, len(content_bytes))
            return False

        # Perform write
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding=encoding, newline="\n") as f:
                f.write(content)

            self._audit("WRITE", path, True, "OK",
                       len(content_bytes), content[:500])
            logger.info(f"File written: {path} ({len(content_bytes)} bytes)")
            return True

        except PermissionError as e:
            reason = f"Permission denied: {e}"
            self._audit("WRITE", path, False, reason)
            logger.error(f"Write permission error: {path} — {e}")
            return False
        except OSError as e:
            reason = f"OS error: {e}"
            self._audit("WRITE", path, False, reason)
            logger.error(f"Write OS error: {path} — {e}")
            return False

    # ── READ FILE ─────────────────────────────────────────
    def read_file(
        self,
        path:     Path,
        encoding: str = "utf-8",
    ) -> Optional[str]:
        """
        Read a file. Returns content or None if blocked/not found.
        """
        path = Path(path)
        allowed, reason = self._validate_read_path(path)

        if not allowed:
            self._audit("READ", path, False, reason)
            return None

        try:
            with open(path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()

            size = path.stat().st_size
            self._audit("READ", path, True, "OK", size)
            return content

        except FileNotFoundError:
            self._audit("READ", path, False, "File not found")
            return None
        except PermissionError as e:
            self._audit("READ", path, False, f"Permission denied: {e}")
            logger.warning(f"Read permission denied: {path}")
            return None
        except Exception as e:
            self._audit("READ", path, False, str(e))
            return None

    # ── DELETE FILE ───────────────────────────────────────
    def delete_file(self, path: Path) -> bool:
        """
        Delete a file. Only allowed inside workspace.
        """
        path = Path(path)
        allowed, reason = self._validate_write_path(path)

        if not allowed:
            self._audit("DELETE", path, False, reason)
            return False

        try:
            if path.is_file():
                path.unlink()
                self._audit("DELETE", path, True, "OK")
                return True
            else:
                self._audit("DELETE", path, False, "Not a file")
                return False
        except Exception as e:
            self._audit("DELETE", path, False, str(e))
            return False

    # ── CREATE DIRECTORY ──────────────────────────────────
    def create_dir(self, path: Path) -> bool:
        """Create a directory inside workspace."""
        path = Path(path)
        allowed, reason = self._validate_write_path(path / ".keep")  # Fake file for validation

        if not allowed:
            self._audit("MKDIR", path, False, reason)
            return False

        try:
            path.mkdir(parents=True, exist_ok=True)
            self._audit("MKDIR", path, True, "OK")
            return True
        except Exception as e:
            self._audit("MKDIR", path, False, str(e))
            return False

    # ── LIST DIRECTORY ────────────────────────────────────
    def list_dir(self, path: Path) -> Optional[List[Path]]:
        """List directory contents. Allowed for workspace."""
        path = Path(path)
        allowed, reason = self._validate_read_path(path)

        if not allowed:
            self._audit("LIST", path, False, reason)
            return None

        try:
            items = sorted(path.iterdir())
            self._audit("LIST", path, True, f"{len(items)} items")
            return items
        except Exception as e:
            self._audit("LIST", path, False, str(e))
            return None

    # ── COPY FILE ─────────────────────────────────────────
    def copy_file(self, src: Path, dst: Path) -> bool:
        """Copy a file. Destination must be in workspace."""
        src = Path(src)
        dst = Path(dst)

        # Source must be readable
        src_ok, src_reason = self._validate_read_path(src)
        if not src_ok:
            self._audit("COPY", dst, False, f"Source blocked: {src_reason}")
            return False

        # Destination must be in workspace
        dst_ok, dst_reason = self._validate_write_path(dst)
        if not dst_ok:
            self._audit("COPY", dst, False, dst_reason)
            return False

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            self._audit("COPY", dst, True, f"from {src}")
            return True
        except Exception as e:
            self._audit("COPY", dst, False, str(e))
            return False

    # ── WRITE MULTIPLE FILES ──────────────────────────────
    def write_project_files(
        self,
        files: Dict[str, str],
        base_path: Optional[Path] = None,
    ) -> Tuple[int, int]:
        """
        Write multiple files at once.
        files: {relative_path_str: content}
        Returns (success_count, fail_count).
        """
        base = Path(base_path or self._workspace)
        success = 0
        fail    = 0

        for rel_path, content in files.items():
            target = base / rel_path
            if self.write_file(target, content):
                success += 1
            else:
                fail += 1

        logger.info(f"Project files written: {success} OK, {fail} failed")
        return success, fail

    # ── WORKSPACE MANAGEMENT ──────────────────────────────
    def create_project_workspace(self, project_name: str) -> Path:
        """Create a new project directory in the workspace."""
        safe_name = re.sub(r'[^\w\-_]', '_', project_name.strip())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = self._workspace / f"{safe_name}_{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Project workspace created: {project_dir}")
        return project_dir

    def get_workspace_size(self) -> int:
        """Get total size of workspace in bytes."""
        total = 0
        try:
            for f in self._workspace.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        except Exception:
            pass
        return total

    def cleanup_old_projects(self, max_age_days: int = 30) -> int:
        """Remove project dirs older than max_age_days. Returns count removed."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0

        for item in self._workspace.iterdir():
            if item.is_dir():
                try:
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    if mtime < cutoff:
                        shutil.rmtree(item, ignore_errors=True)
                        removed += 1
                        logger.info(f"Cleaned up old project: {item.name}")
                except Exception as e:
                    logger.warning(f"Cleanup error for {item}: {e}")

        return removed

    # ── AUDIT REPORTS ─────────────────────────────────────
    def get_audit_log(self, last_n: int = 100) -> List[AuditEntry]:
        """Get recent audit log entries."""
        with self._lock:
            return list(self._audit_log[-last_n:])

    def get_audit_stats(self) -> Dict[str, Any]:
        """Get sandbox operation statistics."""
        with self._lock:
            total      = len(self._audit_log)
            blocked    = sum(1 for e in self._audit_log if not e.allowed)
            allowed    = total - blocked
            by_op: Dict[str, int] = {}
            for entry in self._audit_log:
                op = entry.operation
                by_op[op] = by_op.get(op, 0) + 1

        return {
            "total_operations": total,
            "allowed":          allowed,
            "blocked":          blocked,
            "by_operation":     by_op,
            "workspace":        str(self._workspace),
            "workspace_size_mb": round(self.get_workspace_size() / 1024 / 1024, 2),
        }

    def export_audit_log(self, output_path: Path) -> bool:
        """Export full audit log to JSON file."""
        import json
        try:
            data = {
                "exported_at": datetime.now().isoformat(),
                "stats":       self.get_audit_stats(),
                "entries":     [e.to_dict() for e in self._audit_log],
            }
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Audit export failed: {e}")
            return False

    @property
    def workspace(self) -> Path:
        return self._workspace

    def __repr__(self) -> str:
        stats = self.get_audit_stats()
        return (
            f"Sandbox(workspace={self._workspace}, "
            f"ops={stats['total_operations']}, "
            f"blocked={stats['blocked']})"
        )
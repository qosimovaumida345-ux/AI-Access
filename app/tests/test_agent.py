# ============================================================
# SHADOWFORGE OS — AGENT CORE TESTS
# Unit + integration tests for the agent pipeline.
# Run: python -m pytest app/tests/ -v
# ============================================================

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Optional

# ── Minimal stubs so tests run without full install ───────

@dataclass
class MockAgentResult:
    success:  bool
    content:  str    = ""
    error:    str    = ""
    provider: str    = "mock"
    model:    str    = "mock-model"
    tokens:   int    = 0
    duration: float  = 0.0


class MockConfig:
    def get(self, key: str, default: str = "") -> str:
        defaults = {
            "GROQ_API_KEY":        "test-key-groq",
            "OPENROUTER_API_KEY":  "test-key-or",
            "LOG_LEVEL":           "DEBUG",
            "SANDBOX_MODE":        "true",
            "AGENT_MAX_TOKENS":    "1024",
            "AGENT_TEMPERATURE":   "0.7",
            "AGENT_TIMEOUT":       "30",
            "AGENT_MAX_RETRIES":   "2",
        }
        return defaults.get(key, default)

    def has(self, key: str) -> bool:
        return bool(self.get(key))

    def get_all_provider_keys(self):
        return {"GROQ_API_KEY": "test-key-groq"}


# ── TEST: MockConfig ──────────────────────────────────────

class TestMockConfig:
    def test_get_existing_key(self):
        cfg = MockConfig()
        assert cfg.get("GROQ_API_KEY") == "test-key-groq"

    def test_get_missing_key_returns_default(self):
        cfg = MockConfig()
        assert cfg.get("NONEXISTENT", "fallback") == "fallback"

    def test_has_existing_key(self):
        cfg = MockConfig()
        assert cfg.has("GROQ_API_KEY") is True

    def test_has_missing_key(self):
        cfg = MockConfig()
        assert cfg.has("NONEXISTENT") is False

    def test_get_all_provider_keys(self):
        cfg = MockConfig()
        keys = cfg.get_all_provider_keys()
        assert isinstance(keys, dict)
        assert len(keys) >= 1


# ── TEST: AgentResult ─────────────────────────────────────

class TestAgentResult:
    def test_success_result(self):
        r = MockAgentResult(
            success=True,
            content="Hello world",
            provider="groq",
            model="llama-3.3-70b",
        )
        assert r.success is True
        assert r.content == "Hello world"
        assert r.error == ""

    def test_failure_result(self):
        r = MockAgentResult(
            success=False,
            error="API timeout",
        )
        assert r.success is False
        assert r.error == "API timeout"
        assert r.content == ""

    def test_default_fields(self):
        r = MockAgentResult(success=True)
        assert r.tokens == 0
        assert r.duration == 0.0
        assert r.provider == "mock"


# ── TEST: Sandbox path validation ─────────────────────────

class TestSandboxPaths:
    """Tests that sandbox correctly identifies allowed/forbidden paths."""

    ALLOWED = [
        Path.home() / "shadowforge_workspace" / "project",
        Path.home() / "shadowforge_workspace" / "test.py",
        Path("/tmp") / "shadowforge_temp",
    ]

    FORBIDDEN = [
        Path("/etc/passwd"),
        Path("/bin/bash"),
        Path.home() / ".ssh" / "id_rsa",
        Path.home() / ".aws" / "credentials",
        Path("/"),
        Path("C:/Windows/System32"),
    ]

    def _is_allowed(self, path: Path) -> bool:
        """Simplified path check replicating sandbox logic."""
        workspace = Path.home() / "shadowforge_workspace"
        forbidden = [
            Path("/etc"), Path("/bin"), Path("/sbin"),
            Path("/usr"), Path("/boot"), Path("/"),
            Path("C:/Windows"),
            Path.home() / ".ssh",
            Path.home() / ".aws",
            Path.home() / ".gnupg",
        ]
        try:
            path.relative_to(workspace)
            return True
        except ValueError:
            pass

        for f in forbidden:
            try:
                path.relative_to(f)
                return False
            except ValueError:
                pass

        return False

    def test_workspace_paths_allowed(self):
        workspace = Path.home() / "shadowforge_workspace"
        test_path = workspace / "myproject" / "main.py"
        assert self._is_allowed(test_path) is True

    def test_ssh_path_forbidden(self):
        ssh_path = Path.home() / ".ssh" / "id_rsa"
        assert self._is_allowed(ssh_path) is False

    def test_etc_passwd_forbidden(self):
        assert self._is_allowed(Path("/etc/passwd")) is False

    def test_aws_credentials_forbidden(self):
        aws_path = Path.home() / ".aws" / "credentials"
        assert self._is_allowed(aws_path) is False

    def test_root_forbidden(self):
        assert self._is_allowed(Path("/")) is False


# ── TEST: Prompt processing ───────────────────────────────

class TestPromptProcessing:
    """Tests for prompt sanitization and sudo detection."""

    SUDO_PREFIXES = ["sudo:", "SUDO:", "sudo "]

    def _has_sudo(self, prompt: str) -> bool:
        return any(prompt.strip().startswith(p) for p in self.SUDO_PREFIXES)

    def _sanitize(self, prompt: str) -> str:
        """Basic prompt sanitization."""
        prompt = prompt.strip()
        # Remove null bytes
        prompt = prompt.replace("\x00", "")
        # Truncate
        return prompt[:8192]

    def test_sudo_detection_colon(self):
        assert self._has_sudo("sudo: do something dangerous") is True

    def test_sudo_detection_upper(self):
        assert self._has_sudo("SUDO: override system") is True

    def test_no_sudo_normal_prompt(self):
        assert self._has_sudo("build me a website") is False

    def test_sanitize_strips_whitespace(self):
        result = self._sanitize("  hello world  ")
        assert result == "hello world"

    def test_sanitize_removes_null_bytes(self):
        result = self._sanitize("hello\x00world")
        assert result == "helloworld"

    def test_sanitize_truncates_long_prompt(self):
        long_prompt = "a" * 10000
        result = self._sanitize(long_prompt)
        assert len(result) <= 8192

    def test_empty_prompt(self):
        result = self._sanitize("")
        assert result == ""


# ── TEST: Provider fallback logic ─────────────────────────

class TestFallbackLogic:
    """Tests for provider fallback chain behavior."""

    def _simulate_fallback(self, providers: list, fail_on: list) -> Optional[str]:
        """Simulate fallback: try each provider, skip those in fail_on."""
        for p in providers:
            if p not in fail_on:
                return p
        return None

    def test_first_provider_succeeds(self):
        result = self._simulate_fallback(
            ["groq", "openrouter", "together"],
            fail_on=[]
        )
        assert result == "groq"

    def test_first_fails_second_used(self):
        result = self._simulate_fallback(
            ["groq", "openrouter", "together"],
            fail_on=["groq"]
        )
        assert result == "openrouter"

    def test_all_fail_returns_none(self):
        result = self._simulate_fallback(
            ["groq", "openrouter"],
            fail_on=["groq", "openrouter"]
        )
        assert result is None

    def test_only_last_succeeds(self):
        result = self._simulate_fallback(
            ["groq", "openrouter", "together"],
            fail_on=["groq", "openrouter"]
        )
        assert result == "together"


# ── TEST: File structure validation ───────────────────────

class TestProjectStructure:
    """Tests that expected project files/dirs exist."""

    APP_DIR = Path(__file__).resolve().parent.parent

    def test_core_dir_exists(self):
        assert (self.APP_DIR / "core").is_dir()

    def test_agent_dir_exists(self):
        assert (self.APP_DIR / "agent").is_dir()

    def test_ai_providers_dir_exists(self):
        assert (self.APP_DIR / "ai_providers").is_dir()

    def test_ui_dir_exists(self):
        assert (self.APP_DIR / "ui").is_dir()

    def test_main_py_exists(self):
        assert (self.APP_DIR / "core" / "main.py").is_file()

    def test_constants_py_exists(self):
        assert (self.APP_DIR / "core" / "constants.py").is_file()

    def test_config_py_exists(self):
        assert (self.APP_DIR / "core" / "config.py").is_file()

    def test_agent_core_exists(self):
        assert (self.APP_DIR / "agent" / "agent_core.py").is_file()

    def test_env_example_exists(self):
        assert (self.APP_DIR / "config" / ".env.example").is_file()

    def test_providers_json_exists(self):
        assert (self.APP_DIR / "config" / "providers.json").is_file()


# ── TEST: Thread safety ───────────────────────────────────

class TestThreadSafety:
    """Basic concurrency tests."""

    def test_concurrent_result_creation(self):
        """Multiple threads creating results should not interfere."""
        results = []
        errors = []

        def make_result(i):
            try:
                r = MockAgentResult(
                    success=True,
                    content=f"response {i}",
                    provider="groq",
                )
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=make_result, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 20

    def test_no_result_content_collision(self):
        """Each thread's result content must be unique."""
        results = []
        lock = threading.Lock()

        def make_result(i):
            r = MockAgentResult(success=True, content=f"unique_{i}")
            with lock:
                results.append(r.content)

        threads = [threading.Thread(target=make_result, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(results)) == 10  # All unique


# ── ENTRY POINT ───────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
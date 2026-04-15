# ============================================================
# SHADOWFORGE OS — CONFIGURATION MANAGER
# Loads .env file, validates keys, provides typed access.
# Never logs secret values. Never writes keys to source.
# ============================================================

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("ShadowForge.Config")


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class Config:
    """
    Central configuration object for ShadowForge OS.

    Usage:
        config = Config()
        config.load()
        key = config.get("OPENROUTER_API_KEY")
    """

    # Keys that are optional (app works without them)
    OPTIONAL_KEYS = {
        "TOGETHER_API_KEY",
        "MISTRAL_API_KEY",
        "COHERE_API_KEY",
        "HUGGINGFACE_API_KEY",
        "GOOGLE_AI_API_KEY",
    }

    # Keys that are truly required
    # At least ONE provider key must exist
    PROVIDER_KEYS = [
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
        "TOGETHER_API_KEY",
        "MISTRAL_API_KEY",
        "COHERE_API_KEY",
        "HUGGINGFACE_API_KEY",
        "GOOGLE_AI_API_KEY",
    ]

    def __init__(self):
        self._data: Dict[str, str] = {}
        self._env_path: Optional[Path] = None
        self._loaded = False

    def load(self, env_path: Optional[Path] = None) -> None:
        """Load configuration from .env file and environment variables."""
        # Find .env file
        if env_path:
            self._env_path = Path(env_path)
        else:
            self._env_path = self._find_env_file()

        # Load .env file
        if self._env_path and self._env_path.exists():
            self._parse_env_file(self._env_path)
            logger.info(f"Loaded .env from: {self._env_path}")
        else:
            logger.warning(
                ".env file not found. Using environment variables only. "
                f"Expected at: {self._env_path}"
            )

        # Override with actual environment variables (they take priority)
        for key, value in os.environ.items():
            if key.isupper():
                self._data[key] = value

        # Validate
        self._validate()
        self._loaded = True
        logger.info("Configuration loaded successfully.")

    def _find_env_file(self) -> Path:
        """Search for .env file starting from app directory upward."""
        search_dirs = [
            Path(__file__).resolve().parent.parent,  # app/
            Path(__file__).resolve().parent.parent.parent,  # project root
            Path.cwd(),
        ]
        for directory in search_dirs:
            candidate = directory / ".env"
            if candidate.exists():
                return candidate

        # Return default location even if it doesn't exist
        return Path(__file__).resolve().parent.parent / ".env"

    def _parse_env_file(self, path: Path) -> None:
        """Parse a .env file into self._data."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue

                    # Skip lines without =
                    if "=" not in line:
                        logger.debug(f".env line {line_num}: no '=' found, skipping")
                        continue

                    key, _, value = line.partition("=")
                    key   = key.strip()
                    value = value.strip()

                    # Remove surrounding quotes
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    if key:
                        self._data[key] = value

        except PermissionError:
            logger.error(f"Permission denied reading .env at: {path}")
        except Exception as e:
            logger.error(f"Error parsing .env file: {e}")

    def _validate(self) -> None:
        """Validate that at least one AI provider key exists."""
        available_providers = [
            key for key in self.PROVIDER_KEYS
            if self._data.get(key, "").strip()
        ]

        if not available_providers:
            logger.warning(
                "No AI provider API keys found. "
                "Add at least one to .env file. "
                "See .env.example for reference."
            )
        else:
            # Don't log values, just count
            logger.info(
                f"Available AI providers: {len(available_providers)} keys found."
            )

        # Check GitHub token (needed for auto-push)
        if not self._data.get("GITHUB_TOKEN", "").strip():
            logger.warning(
                "GITHUB_TOKEN not set. Auto GitHub push will be disabled."
            )

    def get(self, key: str, default: str = "") -> str:
        """Get a configuration value. Returns default if not set."""
        if not self._loaded:
            logger.warning("Config.get() called before Config.load()")
        return self._data.get(key, default)

    def require(self, key: str) -> str:
        """Get a required configuration value. Raises if missing."""
        value = self._data.get(key, "").strip()
        if not value:
            raise ConfigError(
                f"Required configuration key '{key}' is missing. "
                f"Add it to your .env file."
            )
        return value

    def has(self, key: str) -> bool:
        """Check if a key is set and non-empty."""
        return bool(self._data.get(key, "").strip())

    def get_all_provider_keys(self) -> Dict[str, str]:
        """Return all available provider keys (without values in logs)."""
        return {
            key: self._data.get(key, "")
            for key in self.PROVIDER_KEYS
            if self._data.get(key, "").strip()
        }

    def get_app_settings(self) -> Dict[str, Any]:
        """Return non-secret app settings."""
        return {
            "debug":          self.get("DEBUG", "false").lower() == "true",
            "log_level":      self.get("LOG_LEVEL", "INFO"),
            "theme":          self.get("THEME", "dark"),
            "voice_enabled":  self.get("VOICE_ENABLED", "true").lower() == "true",
            "sandbox_mode":   self.get("SANDBOX_MODE", "true").lower() == "true",
            "max_file_size":  int(self.get("MAX_FILE_SIZE_MB", "50")),
            "workspace_dir":  self.get("WORKSPACE_DIR", str(Path.home() / "shadowforge")),
        }

    def get_github_config(self) -> Dict[str, str]:
        """Return GitHub-related config."""
        return {
            "token":    self.get("GITHUB_TOKEN"),
            "username": self.get("GITHUB_USERNAME"),
        }

    def __repr__(self) -> str:
        loaded_keys = [k for k, v in self._data.items() if v]
        return (
            f"Config(loaded={self._loaded}, "
            f"keys={len(loaded_keys)}, "
            f"env_file={self._env_path})"
        )
# ============================================================
# SHADOWFORGE OS — VOICE COMMAND PARSER
# Parses spoken phrases into structured agent commands.
# Handles natural language → action mapping.
# ============================================================

import re
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from core.logger import get_logger
from core.constants import VOICE_COMMANDS

logger = get_logger("Voice.CommandParser")


class CommandType(str, Enum):
    BUILD       = "build"
    FIX         = "fix"
    EXPLAIN     = "explain"
    TEST        = "test"
    DEPLOY      = "deploy"
    GITHUB      = "github"
    FILE        = "file"
    NAVIGATE    = "navigate"
    SETTINGS    = "settings"
    CHAT        = "chat"
    STOP        = "stop"
    UNKNOWN     = "unknown"


@dataclass
class ParsedCommand:
    raw_text:    str
    command_type: CommandType
    action:      str
    target:      str   = ""
    parameters:  Dict[str, Any] = field(default_factory=dict)
    confidence:  float = 0.0
    is_sudo:     bool  = False
    prompt:      str   = ""   # Cleaned prompt to send to agent


class CommandParser:
    """
    Parses natural language voice commands into structured actions.

    Supports:
    - Project building commands
    - Code fixing commands
    - GitHub commands
    - Navigation commands
    - Settings commands
    - Free-form prompts
    """

    COMMAND_PATTERNS: List[Tuple[re.Pattern, CommandType, str]] = [
        # Build
        (re.compile(r'\b(create|build|make|generate|new)\b.*(project|app|site|api|bot)', re.I),
         CommandType.BUILD, "create_project"),

        # Fix
        (re.compile(r'\b(fix|repair|debug|solve|patch)\b.*(error|bug|issue|code)', re.I),
         CommandType.FIX, "fix_code"),
        (re.compile(r'\b(fix it|repair it|solve this)\b', re.I),
         CommandType.FIX, "fix_code"),

        # Test
        (re.compile(r'\b(write|add|generate|run)\b.*(test|tests|spec)', re.I),
         CommandType.TEST, "generate_tests"),

        # Deploy
        (re.compile(r'\b(deploy|publish|launch|release|push to)\b', re.I),
         CommandType.DEPLOY, "deploy_project"),
        (re.compile(r'\b(push to github|push to render|go live)\b', re.I),
         CommandType.GITHUB, "push_github"),

        # GitHub
        (re.compile(r'\b(github|commit|push|pull request)\b', re.I),
         CommandType.GITHUB, "github_action"),

        # Explain
        (re.compile(r'\b(explain|what is|how does|describe|tell me about)\b', re.I),
         CommandType.EXPLAIN, "explain_code"),

        # File operations
        (re.compile(r'\b(open|close|save|delete|create)\b.*(file|folder|directory)', re.I),
         CommandType.FILE, "file_operation"),

        # Navigation
        (re.compile(r'\b(go to|navigate|switch to|show me)\b.*(section|tab|panel|page)', re.I),
         CommandType.NAVIGATE, "navigate_ui"),

        # Settings
        (re.compile(r'\b(settings|preferences|configure|setup)\b', re.I),
         CommandType.SETTINGS, "open_settings"),

        # Stop
        (re.compile(r'\b(stop|cancel|abort|quit|exit|halt)\b', re.I),
         CommandType.STOP, "stop_action"),
    ]

    # Navigation targets
    NAV_TARGETS = {
        "chat":     ["chat", "conversation", "messages"],
        "files":    ["files", "file tree", "explorer", "project"],
        "terminal": ["terminal", "console", "output", "logs"],
        "build":    ["build", "compiler", "packager"],
        "settings": ["settings", "preferences", "config"],
        "deploy":   ["deploy", "deployment", "release"],
    }

    def __init__(self):
        logger.info("CommandParser initialized.")

    def parse(self, text: str) -> ParsedCommand:
        """
        Parse a voice input text into a structured command.
        Returns ParsedCommand.
        """
        if not text or not text.strip():
            return ParsedCommand(
                raw_text     = text,
                command_type = CommandType.UNKNOWN,
                action       = "",
                confidence   = 0.0,
            )

        text = text.strip()

        # Check sudo
        is_sudo = text.lower().startswith("sudo ")
        clean   = re.sub(r'^sudo\s+', '', text, flags=re.I) if is_sudo else text

        # Try pattern matching
        best_match:    Optional[Tuple[CommandType, str]] = None
        best_confidence = 0.0

        for pattern, cmd_type, action in self.COMMAND_PATTERNS:
            match = pattern.search(clean)
            if match:
                # Score based on how much of the text matched
                matched_len = len(match.group())
                confidence  = matched_len / max(1, len(clean))
                confidence  = min(1.0, confidence * 2)  # Scale up

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match      = (cmd_type, action)

        if best_match:
            cmd_type, action = best_match
            target = self._extract_target(clean, cmd_type)
            prompt = self._build_agent_prompt(clean, cmd_type, target)

            return ParsedCommand(
                raw_text     = text,
                command_type = cmd_type,
                action       = action,
                target       = target,
                confidence   = best_confidence,
                is_sudo      = is_sudo,
                prompt       = ("sudo " if is_sudo else "") + prompt,
                parameters   = self._extract_parameters(clean, cmd_type),
            )

        # No pattern matched — treat as free-form chat prompt
        return ParsedCommand(
            raw_text     = text,
            command_type = CommandType.CHAT,
            action       = "chat",
            confidence   = 1.0,
            is_sudo      = is_sudo,
            prompt       = ("sudo " if is_sudo else "") + clean,
        )

    def _extract_target(self, text: str, cmd_type: CommandType) -> str:
        """Extract the target of a command (filename, platform, etc.)."""
        if cmd_type == CommandType.NAVIGATE:
            text_lower = text.lower()
            for panel, keywords in self.NAV_TARGETS.items():
                if any(kw in text_lower for kw in keywords):
                    return panel

        if cmd_type == CommandType.DEPLOY:
            platforms = ["render", "vercel", "railway", "github", "fly"]
            for p in platforms:
                if p in text.lower():
                    return p

        if cmd_type in (CommandType.BUILD, CommandType.FIX):
            # Extract quoted text as target
            match = re.search(r'["\']([^"\']+)["\']', text)
            if match:
                return match.group(1)

        return ""

    def _extract_parameters(
        self, text: str, cmd_type: CommandType
    ) -> Dict[str, Any]:
        """Extract additional parameters from command text."""
        params: Dict[str, Any] = {}

        # Extract technology stack mentions
        stacks = {
            "react":   ["react", "reactjs"],
            "vue":     ["vue", "vuejs"],
            "angular": ["angular"],
            "django":  ["django"],
            "fastapi": ["fastapi", "fast api"],
            "flask":   ["flask"],
            "nextjs":  ["next.js", "nextjs", "next js"],
            "python":  ["python"],
            "node":    ["node", "nodejs", "node.js"],
        }

        text_lower = text.lower()
        for stack, keywords in stacks.items():
            if any(kw in text_lower for kw in keywords):
                params["stack"] = stack
                break

        # Platform mentions
        platforms = ["windows", "macos", "linux", "android", "web"]
        for p in platforms:
            if p in text_lower:
                params.setdefault("platforms", []).append(p)

        return params

    def _build_agent_prompt(
        self,
        text:     str,
        cmd_type: CommandType,
        target:   str,
    ) -> str:
        """Build a clean prompt to send to the agent."""
        if cmd_type == CommandType.CHAT:
            return text

        if cmd_type == CommandType.BUILD:
            prefix = "Create a project: "
            return prefix + text

        if cmd_type == CommandType.FIX:
            return f"Fix this issue: {text}"

        if cmd_type == CommandType.TEST:
            return f"Write tests for: {text}"

        if cmd_type == CommandType.DEPLOY:
            target_str = f" to {target}" if target else ""
            return f"Deploy the project{target_str}: {text}"

        if cmd_type == CommandType.EXPLAIN:
            return f"Explain: {text}"

        return text

    def get_command_suggestions(self) -> List[str]:
        """Return list of example voice commands for UI display."""
        return [
            "Create a new web app",
            "Build a REST API with FastAPI",
            "Fix the error in the code",
            "Write tests for the project",
            "Deploy to Render",
            "Push to GitHub",
            "Explain this code",
            "sudo Create a cookie stealer for my own site",
            "Stop",
        ]
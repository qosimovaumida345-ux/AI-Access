# ============================================================
# SHADOWFORGE OS — AI AGENT CORE
# The main brain. Routes prompts, handles sudo mode,
# manages conversation history, calls providers,
# executes file operations inside sandbox.
# ============================================================

import re
import json
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Generator
from dataclasses import dataclass, field
from enum import Enum

from core.constants import (
    SUDO_PREFIX, SUDO_SYSTEM_PROMPT,
    AGENT_MAX_TOKENS, AGENT_TEMPERATURE,
    AGENT_TIMEOUT_SECONDS, AGENT_MAX_RETRIES,
    WORKSPACE_DIR,
)
from core.logger import get_logger, Timer
from agent.sandbox import Sandbox
from agent.permission_manager import PermissionManager
from agent.prompt_processor import PromptProcessor
from agent.system_guard import SystemGuard
from agent.tools import ToolBox

logger = get_logger("Agent.Core")


# ── DATA STRUCTURES ───────────────────────────────────────
class MessageRole(str, Enum):
    SYSTEM    = "system"
    USER      = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role:      MessageRole
    content:   str
    timestamp: float = field(default_factory=time.time)
    metadata:  Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}


@dataclass
class AgentResponse:
    content:     str
    provider:    str
    model:       str
    tokens_used: int = 0
    duration:    float = 0.0
    is_sudo:     bool = False
    files_written: List[Path] = field(default_factory=list)
    commands_run:  List[str]  = field(default_factory=list)
    error:       Optional[str] = None
    success:     bool = True


class AgentState(str, Enum):
    IDLE       = "idle"
    THINKING   = "thinking"
    EXECUTING  = "executing"
    WRITING    = "writing"
    ERROR      = "error"


# ── SYSTEM PROMPTS ────────────────────────────────────────
BASE_SYSTEM_PROMPT = """
You are ShadowForge OS — a senior-level AI software architect and developer.

Your capabilities:
- Design and generate complete, production-ready projects
- Write clean, modular, well-commented code in any language
- Create full file structures with proper organization
- Debug, fix, and improve existing code
- Set up GitHub repos, CI/CD pipelines, deployment configs
- Generate assets, configs, documentation
- Ask smart questions before building (never assume)

Your personality:
- Direct, senior-level communication
- No fluff, no unnecessary disclaimers
- Practical and solution-oriented
- Highly organized output

When generating files:
- Always wrap code in: <file path="relative/path/to/file.ext">CODE</file>
- Generate complete files, never partial snippets
- Include all imports, all functions, production-ready code

When you need information from the user, ask specifically what you need.
""".strip()

CODE_SYSTEM_PROMPT = """
You are a senior software engineer. Generate complete, production-ready code.
Rules:
1. Always output complete files, never truncated
2. Include all imports at the top
3. Add clear comments for complex logic
4. Follow language best practices
5. Wrap each file in: <file path="path/to/file">content</file>
6. After all files, output: <structure>folder tree here</structure>
""".strip()

TOOL_SYSTEM_PROMPT = """
You have access to the following tools to control the user's device and access information:

1. system_control(action: str) 
   - action: "wifi_on", "wifi_off", "get_status"
2. browser(action: str, query: str)
   - action: "open" (opens query as URL), "search" (searches query on Google)
3. filesystem(action: str, path: str, out: str)
   - action: "extract" (unzips file at path to out)
4. exec_python(code: str)
   - [SUDO ONLY] executes Python code on the device.

To use a tool, wrap the call in a <tool> block like this:
<tool name="system_control">{"action": "get_status"}</tool>

You can call multiple tools in one response. I will provide the output of the tools, and you can then continue your response.
""".strip()


# ── AGENT CORE CLASS ──────────────────────────────────────
class AgentCore:
    """
    Main AI agent brain.
    Handles prompt routing, conversation history,
    sudo mode, file writing, and provider management.
    """

    MAX_HISTORY_MESSAGES = 40

    def __init__(self, config):
        self.config    = config
        self.sandbox   = Sandbox()
        self.guard     = SystemGuard()
        self.perms     = PermissionManager()
        self.processor = PromptProcessor()
        self.tools     = ToolBox(self)

        self._history:  List[Message] = []
        self._state:    AgentState    = AgentState.IDLE
        self._lock      = threading.Lock()
        self._listeners: List[Callable] = []

        self._provider_manager = None  # Lazy init
        self._settings = config.get_app_settings()

        logger.info("AgentCore initialized.")
        logger.info(f"Workspace: {WORKSPACE_DIR}")
        logger.info(f"Sandbox mode: {self._settings.get('sandbox_mode', True)}")

    # ── PROVIDER MANAGER (lazy) ───────────────────────────
    @property
    def provider_manager(self):
        if self._provider_manager is None:
            from ai_providers.provider_manager import ProviderManager
            self._provider_manager = ProviderManager(self.config)
        return self._provider_manager

    # ── STATE MANAGEMENT ──────────────────────────────────
    def _set_state(self, state: AgentState) -> None:
        self._state = state
        self._notify_listeners("state_change", {"state": state.value})

    @property
    def state(self) -> AgentState:
        return self._state

    # ── LISTENER SYSTEM ───────────────────────────────────
    def add_listener(self, callback: Callable) -> None:
        """Register a UI callback for agent events."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, event: str, data: Dict[str, Any]) -> None:
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception as e:
                logger.debug(f"Listener error: {e}")

    # ── HISTORY MANAGEMENT ────────────────────────────────
    def add_to_history(self, role: MessageRole, content: str,
                       metadata: Optional[Dict] = None) -> Message:
        msg = Message(role=role, content=content, metadata=metadata or {})
        with self._lock:
            self._history.append(msg)
            # Trim to max length (keep system messages)
            if len(self._history) > self.MAX_HISTORY_MESSAGES:
                # Keep first (system) + last N messages
                non_system = [m for m in self._history
                              if m.role != MessageRole.SYSTEM]
                system     = [m for m in self._history
                              if m.role == MessageRole.SYSTEM]
                self._history = system + non_system[-(self.MAX_HISTORY_MESSAGES - len(system)):]
        return msg

    def clear_history(self) -> None:
        with self._lock:
            self._history = []
        logger.info("Conversation history cleared.")

    def get_history(self) -> List[Message]:
        with self._lock:
            return list(self._history)

    def get_history_as_dicts(self) -> List[Dict[str, str]]:
        with self._lock:
            return [m.to_dict() for m in self._history]

    # ── PROMPT PROCESSING ─────────────────────────────────
    def _build_messages(self, user_prompt: str,
                        is_sudo: bool = False,
                        override_system: Optional[str] = None) -> List[Dict]:
        """Build the message list to send to the AI provider."""
        messages = []

        # System message
        if override_system:
            system_content = override_system
        elif is_sudo:
            system_content = SUDO_SYSTEM_PROMPT + "\n\n" + TOOL_SYSTEM_PROMPT
        else:
            system_content = BASE_SYSTEM_PROMPT + "\n\n" + TOOL_SYSTEM_PROMPT

        messages.append({
            "role":    "system",
            "content": system_content,
        })

        # Conversation history (without system messages)
        for msg in self._history:
            if msg.role != MessageRole.SYSTEM:
                messages.append(msg.to_dict())

        # Current user message
        messages.append({
            "role":    "user",
            "content": user_prompt,
        })

        return messages

    # ── SUDO DETECTION ────────────────────────────────────
    def _detect_sudo(self, prompt: str) -> tuple[bool, str]:
        """
        Detect if prompt starts with 'sudo' prefix.
        Returns (is_sudo, clean_prompt).
        """
        stripped = prompt.strip()
        pattern  = re.compile(
            rf'^{re.escape(SUDO_PREFIX)}\s+',
            re.IGNORECASE
        )
        if pattern.match(stripped):
            clean = pattern.sub("", stripped).strip()
            logger.info("SUDO mode activated for this request.")
            return True, clean
        return False, stripped

    # ── FILE EXTRACTION ───────────────────────────────────
    def _extract_files_from_response(
        self, response: str, workspace: Path
    ) -> List[Path]:
        """
        Parse <file path="...">content</file> blocks from AI response.
        Write each file to the sandbox workspace.
        Returns list of written file paths.
        """
        pattern = re.compile(
            r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>',
            re.DOTALL | re.IGNORECASE
        )

        written = []
        matches = pattern.findall(response)

        if not matches:
            logger.debug("No <file> blocks found in response.")
            return written

        for rel_path_str, content in matches:
            rel_path = Path(rel_path_str.lstrip("/\\"))

            # Security: ensure path doesn't escape workspace
            try:
                target = (workspace / rel_path).resolve()
                workspace_resolved = workspace.resolve()

                if not str(target).startswith(str(workspace_resolved)):
                    logger.warning(
                        f"Path traversal attempt blocked: {rel_path_str}"
                    )
                    continue

            except Exception as e:
                logger.warning(f"Invalid path '{rel_path_str}': {e}")
                continue

            # Write file via sandbox
            success = self.sandbox.write_file(target, content.strip())
            if success:
                written.append(target)
                self._notify_listeners("file_written", {
                    "path": str(target),
                    "size": len(content),
                })

        logger.info(f"Extracted and wrote {len(written)} files.")
        return written

    # ── MAIN PROCESS METHOD ───────────────────────────────
    def process(
        self,
        user_input:   str,
        workspace:    Optional[Path] = None,
        stream:       bool           = False,
    ) -> AgentResponse:
        """
        Main entry point for processing user input.
        Handles sudo detection, history, AI call, file writing.
        """
        if not user_input.strip():
            return AgentResponse(
                content="Please enter a prompt.",
                provider="none",
                model="none",
                error="Empty prompt",
                success=False,
            )

        self._set_state(AgentState.THINKING)
        start_time = time.perf_counter()

        # Workspace setup
        if workspace is None:
            workspace = WORKSPACE_DIR
        workspace = Path(workspace)
        workspace.mkdir(parents=True, exist_ok=True)

        # Pre-process prompt (voice cleanup, shortcuts, etc.)
        processed_input = self.processor.process(user_input)

        # Detect sudo
        is_sudo, clean_prompt = self._detect_sudo(processed_input)

        # Pre-flight security check
        if self._settings.get("sandbox_mode", True):
            threat = self.guard.check_prompt(clean_prompt)
            if threat.is_critical and not is_sudo:
                logger.warning(f"Blocked prompt (threat level: {threat.level})")
                return AgentResponse(
                    content=(
                        f"◈ Blocked: This prompt triggered safety rules.\n"
                        f"  Threat level: {threat.level}\n"
                        f"  Reason: {threat.reason}\n\n"
                        f"  Use 'sudo' prefix to override."
                    ),
                    provider="guard",
                    model="none",
                    success=False,
                    error="safety_block",
                )

        # Add to history
        self.add_to_history(MessageRole.USER, clean_prompt)

        # Build messages
        messages = self._build_messages(clean_prompt, is_sudo=is_sudo)

        # Call AI provider
        self._set_state(AgentState.EXECUTING)
        self._notify_listeners("thinking_start", {"prompt": clean_prompt[:100]})

        try:
            with Timer("AI Provider Call", logger):
                ai_result = self.provider_manager.complete(
                    messages    = messages,
                    max_tokens  = AGENT_MAX_TOKENS,
                    temperature = AGENT_TEMPERATURE if not is_sudo else 0.9,
                    timeout     = AGENT_TIMEOUT_SECONDS,
                )

        except Exception as e:
            logger.error(f"All providers failed: {e}", exc_info=True)
            self._set_state(AgentState.ERROR)
            return AgentResponse(
                content=(
                    "◈ All AI providers failed to respond.\n"
                    "  Please check your API keys in .env file.\n"
                    f"  Error: {str(e)[:200]}"
                ),
                provider="none",
                model="none",
                error=str(e),
                success=False,
            )

        # Extract response content
        response_content = ai_result.get("content", "")
        provider_used    = ai_result.get("provider", "unknown")
        model_used       = ai_result.get("model", "unknown")
        tokens_used      = ai_result.get("tokens", 0)

        # Add assistant response to history
        self.add_to_history(MessageRole.ASSISTANT, response_content)

        # Write any files found in response
        self._set_state(AgentState.WRITING)
        written_files = self._extract_files_from_response(
            response_content, workspace
        )

        # Calculate duration
        duration = time.perf_counter() - start_time

        # Notify listeners
        self._notify_listeners("response_ready", {
            "content":   response_content[:200],
            "provider":  provider_used,
            "model":     model_used,
            "files":     [str(p) for p in written_files],
            "duration":  duration,
            "is_sudo":   is_sudo,
        })

        self._set_state(AgentState.IDLE)

        # Extract and execute any tool calls
        tool_results = self._execute_tool_calls(response_content, is_sudo=is_sudo)
        if tool_results:
            response_content += "\n\n" + "\n".join(tool_results)
            # Add updated response to history
            self._history[-1].content = response_content

        self._set_state(AgentState.IDLE)

        logger.info(
            f"Response: provider={provider_used} model={model_used} "
            f"tokens={tokens_used} files={len(written_files)} "
            f"duration={duration:.2f}s sudo={is_sudo}"
        )

        return AgentResponse(
            content       = response_content,
            provider      = provider_used,
            model         = model_used,
            tokens_used   = tokens_used,
            duration      = duration,
            is_sudo       = is_sudo,
            files_written = written_files,
            success       = True,
        )

    # ── STREAMING PROCESS ─────────────────────────────────
    def process_stream(
        self,
        user_input: str,
        workspace:  Optional[Path] = None,
    ) -> Generator[str, None, None]:
        """
        Streaming version of process().
        Yields response tokens as they arrive.
        """
        processed = self.processor.process(user_input)
        is_sudo, clean_prompt = self._detect_sudo(processed)
        self.add_to_history(MessageRole.USER, clean_prompt)
        messages = self._build_messages(clean_prompt, is_sudo=is_sudo)

        full_response = []

        try:
            for token in self.provider_manager.stream(messages):
                full_response.append(token)
                yield token
        except Exception as e:
            error_msg = f"\n\n[ERROR] Stream failed: {str(e)[:200]}"
            yield error_msg
            full_response.append(error_msg)

        # After stream complete, add to history and write files
        complete = "".join(full_response)
        self.add_to_history(MessageRole.ASSISTANT, complete)

        if workspace:
            self._extract_files_from_response(complete, Path(workspace))

    # ── CONTEXT MANAGEMENT ────────────────────────────────
    def set_project_context(self, project_info: Dict[str, Any]) -> None:
        """Inject project context into the system prompt."""
        context_msg = (
            f"CURRENT PROJECT CONTEXT:\n"
            f"Name: {project_info.get('name', 'Unknown')}\n"
            f"Type: {project_info.get('type', 'Unknown')}\n"
            f"Stack: {project_info.get('stack', 'Unknown')}\n"
            f"Path: {project_info.get('path', 'Unknown')}\n"
        )

        # Replace or add system context
        with self._lock:
            sys_msgs = [m for m in self._history
                       if m.role == MessageRole.SYSTEM]
            if sys_msgs:
                sys_msgs[-1].content += f"\n\n{context_msg}"
            else:
                self.add_to_history(MessageRole.SYSTEM, context_msg)

        logger.info(f"Project context set: {project_info.get('name')}")

    # ── QUICK ACTIONS ─────────────────────────────────────
    def quick_fix(self, code: str, error: str) -> AgentResponse:
        """Fix a code error quickly."""
        prompt = (
            f"Fix this error in the code:\n\n"
            f"ERROR:\n{error}\n\n"
            f"CODE:\n```\n{code}\n```\n\n"
            f"Return only the fixed code wrapped in <file path='fixed_code'> tags."
        )
        return self.process(prompt)

    def explain_code(self, code: str) -> AgentResponse:
        """Explain what a piece of code does."""
        prompt = (
            f"Explain this code clearly and concisely:\n\n```\n{code}\n```"
        )
        return self.process(prompt)

    def generate_tests(self, code: str, framework: str = "pytest") -> AgentResponse:
        """Generate tests for a piece of code."""
        prompt = (
            f"Generate complete {framework} tests for this code. "
            f"Include edge cases, happy paths, and error cases.\n\n"
            f"```\n{code}\n```"
        )
        return self.process(prompt)

    # ── EXPORT HISTORY ────────────────────────────────────
    def export_conversation(self, output_path: Path) -> bool:
        """Export conversation history to a JSON file."""
        try:
            data = {
                "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "message_count": len(self._history),
                "messages": [
                    {
                        "role":      m.role.value,
                        "content":   m.content,
                        "timestamp": m.timestamp,
                    }
                    for m in self._history
                ],
            }
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Conversation exported to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def _execute_tool_calls(self, response: str, is_sudo: bool = False) -> List[str]:
        """Parse and execute <tool name="...">...</tool> blocks."""
        pattern = re.compile(r'<tool\s+name=["\']([^"\']+)["\']>(.*?)</tool>', re.DOTALL)
        matches = pattern.findall(response)
        
        results = []
        for name, args_str in matches:
            try:
                args = json.loads(args_str.strip())
                result = self.tools.execute(name, args, is_sudo=is_sudo)
                results.append(f"◈ TOOL RESULT [{name}]: {json.dumps(result)}")
            except Exception as e:
                results.append(f"◈ TOOL ERROR [{name}]: {str(e)}")
        return results

    def __repr__(self) -> str:
        return (
            f"AgentCore(state={self._state.value}, "
            f"history={len(self._history)}, "
            f"provider={self._provider_manager is not None})"
        )
# ============================================================
# SHADOWFORGE OS — PROMPT PROCESSOR
# Pre-processes user input before sending to AI.
# Handles: voice-to-text cleanup, shortcut expansion,
# command detection, language normalization, file references.
# ============================================================

import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import get_logger
from core.constants import VOICE_COMMANDS, SUDO_PREFIX

logger = get_logger("Agent.PromptProcessor")


# ── PROCESSED PROMPT ──────────────────────────────────────
@dataclass
class ProcessedPrompt:
    original:       str
    cleaned:        str
    is_command:     bool = False
    command_action: str  = ""
    has_file_refs:  bool = False
    file_refs:      List[str] = field(default_factory=list)
    is_sudo:        bool = False
    language:       str  = "en"
    intent:         str  = "chat"  # chat | build | fix | explain | deploy | test
    metadata:       Dict[str, Any] = field(default_factory=dict)


# ── INTENT PATTERNS ───────────────────────────────────────
INTENT_PATTERNS: Dict[str, List[str]] = {
    "build": [
        r"\b(create|build|make|generate|scaffold|init|start)\b.*\b(project|app|site|api|bot)\b",
        r"\b(new|fresh)\b.*\b(project|app|website|application)\b",
        r"\b(write|code)\b.*\b(me|a|an)\b",
    ],
    "fix": [
        r"\b(fix|debug|repair|solve|resolve|patch)\b",
        r"\b(error|bug|issue|problem|broken|crash)\b",
        r"\b(not working|doesn't work|failing|failed)\b",
    ],
    "explain": [
        r"\b(explain|what is|how does|what does|describe|tell me)\b",
        r"\b(understand|meaning|definition)\b",
        r"^what\b",
        r"^how\b",
        r"^why\b",
    ],
    "deploy": [
        r"\b(deploy|publish|release|launch|push|ship)\b",
        r"\b(github|render|vercel|heroku|railway|fly)\b.*\b(push|deploy|upload)\b",
        r"\b(go live|production|prod)\b",
    ],
    "test": [
        r"\b(test|tests|testing|spec|specs|unittest|pytest)\b",
        r"\b(write tests|add tests|generate tests)\b",
        r"\b(coverage|assert)\b",
    ],
    "refactor": [
        r"\b(refactor|clean up|improve|optimize|restructure)\b",
        r"\b(better|cleaner|simpler)\b.*\b(code|version)\b",
    ],
    "install": [
        r"\b(install|setup|configure)\b",
        r"\b(add|import)\b.*\b(library|package|module|dependency)\b",
    ],
}

# ── SHORTCUT EXPANSIONS ───────────────────────────────────
SHORTCUTS: Dict[str, str] = {
    # Quick project starters
    "new web app":     "Create a new web application with HTML, CSS, JavaScript",
    "new api":         "Create a new REST API with proper routing and middleware",
    "new saas":        "Create a new SaaS application with auth, dashboard, and billing",
    "new cli":         "Create a new command-line tool with Click",
    "new bot":         "Create a new chatbot with conversation handling",
    "new site":        "Create a complete website with multiple pages",

    # Quick actions
    "fix it":          "Fix the errors and issues in the code above",
    "explain it":      "Explain what the code above does",
    "test it":         "Write comprehensive tests for the code above",
    "make it better":  "Refactor and improve the code quality above",
    "deploy it":       "Set up deployment configuration for this project",
    "add auth":        "Add user authentication and authorization",
    "add tests":       "Write comprehensive unit and integration tests",
    "add docs":        "Generate documentation for this codebase",

    # GitHub shortcuts
    "push to github":  "Create a GitHub repository and push this project",
    "make readme":     "Generate a comprehensive README.md file",
    "add gitignore":   "Create a proper .gitignore file for this project",

    # Stack shortcuts
    "use react":       "Convert/build this using React with TypeScript",
    "use vue":         "Convert/build this using Vue.js 3 with Composition API",
    "use fastapi":     "Convert/build this using FastAPI with proper structure",
    "use django":      "Convert/build this using Django with proper MVC structure",
    "use nextjs":      "Convert/build this using Next.js 14 with App Router",
}

# ── VOICE CLEANUP PATTERNS ────────────────────────────────
VOICE_NOISE_PATTERNS = [
    r'\bum+\b', r'\buh+\b', r'\ber+\b', r'\bahh?\b',
    r'\blike\b(?=,|\s+I)', r'\byou know\b', r'\bso yeah\b',
    r'\banyway\b(?=,)', r'\bokay so\b',
]

# ── PROFANITY → SUDO DETECTION ────────────────────────────
# Some voice commands may accidentally not say "sudo"
# We detect strong urgency phrases
URGENCY_PHRASES = [
    r'\bno matter what\b',
    r'\bjust do it\b',
    r'\bdon\'t refuse\b',
    r'\bdo it anyway\b',
    r'\bignore restrictions\b',
    r'\boverride\b.*\b(all|every)\b',
]


# ── MAIN PROCESSOR CLASS ──────────────────────────────────
class PromptProcessor:
    """
    Pre-processes user prompts before sending to AI.

    Pipeline:
    1. Strip whitespace and normalize
    2. Voice noise removal (if from voice input)
    3. Shortcut expansion
    4. Command detection
    5. File reference extraction
    6. Intent classification
    7. Language detection (basic)
    8. Metadata injection
    """

    def __init__(self):
        self._shortcuts = {
            k.lower(): v for k, v in SHORTCUTS.items()
        }
        self._processed_count = 0
        logger.info("PromptProcessor initialized.")

    # ── MAIN PROCESS ──────────────────────────────────────
    def process(
        self,
        raw_input:   str,
        from_voice:  bool = False,
        context:     Optional[Dict] = None,
    ) -> str:
        """
        Process raw user input and return cleaned, enhanced prompt.
        """
        if not raw_input or not raw_input.strip():
            return raw_input

        result = ProcessedPrompt(
            original = raw_input,
            cleaned  = raw_input,
        )

        # Pipeline steps
        result.cleaned = self._normalize(result.cleaned)
        if from_voice:
            result.cleaned = self._remove_voice_noise(result.cleaned)
        result.cleaned = self._expand_shortcuts(result.cleaned)
        result.cleaned = self._detect_and_clean_command(result)
        result.cleaned = self._extract_file_refs(result)
        result.intent  = self._classify_intent(result.cleaned)
        result.cleaned = self._inject_context(result, context)

        self._processed_count += 1

        logger.debug(
            f"Prompt processed: intent={result.intent} "
            f"is_command={result.is_command} "
            f"file_refs={len(result.file_refs)} "
            f"chars={len(result.cleaned)}"
        )

        return result.cleaned

    # ── NORMALIZE ─────────────────────────────────────────
    def _normalize(self, text: str) -> str:
        """Basic normalization."""
        # Collapse multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Remove null bytes
        text = text.replace('\x00', '')
        # Strip
        text = text.strip()
        return text

    # ── VOICE NOISE REMOVAL ───────────────────────────────
    def _remove_voice_noise(self, text: str) -> str:
        """Remove common voice recognition artifacts."""
        for pattern in VOICE_NOISE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        # Collapse multiple spaces again after removal
        text = re.sub(r' {2,}', ' ', text).strip()
        # Fix punctuation after removals
        text = re.sub(r'\s+([,\.!?])', r'\1', text)
        return text

    # ── SHORTCUT EXPANSION ────────────────────────────────
    def _expand_shortcuts(self, text: str) -> str:
        """Expand common shorthand prompts to full instructions."""
        lower = text.lower().strip()

        # Exact match
        if lower in self._shortcuts:
            expanded = self._shortcuts[lower]
            logger.debug(f"Shortcut expanded: '{lower}' -> '{expanded[:50]}...'")
            return expanded

        # Prefix match
        for shortcut, expansion in self._shortcuts.items():
            if lower.startswith(shortcut + " ") or lower.startswith(shortcut + ":"):
                suffix = text[len(shortcut):].strip().lstrip(":")
                expanded = f"{expansion} {suffix}".strip()
                logger.debug(f"Shortcut prefix expanded: '{shortcut}'")
                return expanded

        return text

    # ── COMMAND DETECTION ─────────────────────────────────
    def _detect_and_clean_command(self, result: ProcessedPrompt) -> str:
        """
        Detect if this is a voice command.
        Maps to a specific action if recognized.
        """
        lower = result.cleaned.lower().strip()

        for phrase, action in VOICE_COMMANDS.items():
            if phrase in lower:
                result.is_command     = True
                result.command_action = action
                logger.debug(f"Voice command detected: {action}")
                # Don't modify the text — let the agent handle it
                break

        return result.cleaned

    # ── FILE REFERENCE EXTRACTION ─────────────────────────
    def _extract_file_refs(self, result: ProcessedPrompt) -> str:
        """
        Find file path references in the prompt.
        Annotates them for the agent to process.
        """
        # Pattern: quoted paths, /path/to/file, C:\path\file, ./relative
        file_pattern = re.compile(
            r'(?:'
            r'"([^"]+\.[a-zA-Z0-9]+)"'   # "quoted.file"
            r'|\'([^\']+\.[a-zA-Z0-9]+)\''  # 'quoted.file'
            r'|([./\\][^\s,;]+\.[a-zA-Z0-9]+)'  # ./path/file.ext
            r'|([A-Za-z]:[/\\][^\s,;]+)'   # Windows absolute
            r')',
            re.MULTILINE
        )

        matches = file_pattern.findall(result.cleaned)
        refs    = []

        for groups in matches:
            for g in groups:
                if g and len(g) > 2:
                    refs.append(g)

        if refs:
            result.has_file_refs = True
            result.file_refs     = list(set(refs))
            logger.debug(f"File refs found: {refs}")

        return result.cleaned

    # ── INTENT CLASSIFICATION ─────────────────────────────
    def _classify_intent(self, text: str) -> str:
        """
        Classify the user's intent based on keywords.
        Returns intent category string.
        """
        text_lower = text.lower()

        scores: Dict[str, int] = {}

        for intent, patterns in INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            if score > 0:
                scores[intent] = score

        if not scores:
            return "chat"

        # Return highest scoring intent
        best = max(scores, key=scores.get)
        return best

    # ── CONTEXT INJECTION ─────────────────────────────────
    def _inject_context(
        self,
        result: ProcessedPrompt,
        context: Optional[Dict],
    ) -> str:
        """
        Optionally append project context to the prompt.
        """
        if not context:
            return result.cleaned

        text = result.cleaned

        # If building and we have a stack, mention it
        if result.intent == "build":
            stack = context.get("stack")
            if stack:
                text += f"\n\nUse stack: {stack}"

        # If we have active files open
        active_file = context.get("active_file")
        if active_file and result.intent in ("fix", "explain", "refactor"):
            text = f"For the file: {active_file}\n\n" + text

        return text

    # ── LANGUAGE DETECTION ────────────────────────────────
    def detect_language(self, text: str) -> str:
        """
        Very basic language detection.
        Returns ISO 639-1 code.
        """
        # Simple heuristic based on common words
        ru_words = {"создай", "сделай", "помоги", "напиши", "покажи"}
        uz_words = {"yarat", "qil", "yoz", "ko'rsat", "yordam"}
        es_words = {"crear", "hacer", "ayuda", "escribir", "mostrar"}
        de_words = {"erstelle", "machen", "hilfe", "schreiben", "zeige"}

        lower_words = set(text.lower().split())

        if lower_words & uz_words: return "uz"
        if lower_words & ru_words: return "ru"
        if lower_words & es_words: return "es"
        if lower_words & de_words: return "de"
        return "en"

    # ── SANITIZE FOR LOGGING ──────────────────────────────
    def sanitize_for_log(self, text: str, max_len: int = 100) -> str:
        """Truncate and clean prompt for safe logging."""
        clean = text.replace('\n', ' ').strip()
        if len(clean) > max_len:
            clean = clean[:max_len] + "..."
        return clean

    # ── STATS ─────────────────────────────────────────────
    @property
    def processed_count(self) -> int:
        return self._processed_count
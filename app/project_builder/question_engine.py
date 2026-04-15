# ============================================================
# SHADOWFORGE OS — SMART QUESTION ENGINE
# Before building any project, asks the user exactly what
# is needed. No assumptions. Smart defaults. Fast flow.
# Collects: name, type, stack, style, platform, assets, deploy.
# ============================================================

import re
import json
import time
import logging
import threading
from pathlib import Path
from typing import (
    Optional, Dict, List, Any, Callable,
    Tuple, Set
)
from dataclasses import dataclass, field
from enum import Enum

from core.logger import get_logger
from core.constants import (
    BUILDER_SUPPORTED_TYPES,
    REQUIRED_QUESTIONS,
    OPTIONAL_QUESTIONS,
    DEPLOY_TARGETS,
)

logger = get_logger("Builder.QuestionEngine")


# ── ENUMS ─────────────────────────────────────────────────
class ProjectType(str, Enum):
    WEB        = "web"
    API        = "api"
    SAAS       = "saas"
    DESKTOP    = "desktop"
    MOBILE     = "mobile"
    CLI        = "cli"
    BOT        = "bot"
    GAME       = "game"
    DATA       = "data"
    ML         = "ml"
    FULLSTACK  = "fullstack"
    ECOMMERCE  = "ecommerce"
    PORTFOLIO  = "portfolio"
    DASHBOARD  = "dashboard"
    BLOG       = "blog"


class Platform(str, Enum):
    WEB        = "web"
    WINDOWS    = "windows"
    MACOS      = "macos"
    LINUX      = "linux"
    ANDROID    = "android"
    IOS        = "ios"
    ALL        = "all"


class StylePreference(str, Enum):
    DARK       = "dark"
    LIGHT      = "light"
    MINIMAL    = "minimal"
    COLORFUL   = "colorful"
    CORPORATE  = "corporate"
    HORROR     = "horror"
    CYBERPUNK  = "cyberpunk"
    GLASSMORPHISM = "glassmorphism"


class DatabaseType(str, Enum):
    NONE       = "none"
    SQLITE     = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL      = "mysql"
    MONGODB    = "mongodb"
    REDIS      = "redis"
    SUPABASE   = "supabase"
    FIREBASE   = "firebase"


# ── DATA CLASSES ──────────────────────────────────────────
@dataclass
class Question:
    key:           str
    text:          str
    hint:          str          = ""
    required:      bool         = True
    default:       Any          = None
    choices:       List[str]    = field(default_factory=list)
    multi_select:  bool         = False
    validator:     Optional[Callable] = None
    depends_on:    Optional[Dict[str, Any]] = None  # {key: value} condition
    follow_ups:    List[str]    = field(default_factory=list)


@dataclass
class ProjectSpec:
    """Complete project specification collected from user."""
    # Identity
    name:           str  = ""
    description:    str  = ""
    project_type:   str  = "web"

    # Technical
    stack:          str  = ""          # e.g., "React + FastAPI"
    frontend:       str  = ""
    backend:        str  = ""
    database:       str  = "none"
    auth_required:  bool = False
    api_required:   bool = False

    # Platform
    platforms:      List[str] = field(default_factory=lambda: ["web"])
    mobile_first:   bool = False

    # Design
    style:          str  = "dark"
    color_scheme:   str  = "purple-black"
    animations:     bool = True
    responsive:     bool = True

    # Assets
    logo_needed:    bool = True
    background_type:str  = "animated"  # animated | image | video | none
    custom_fonts:   bool = False

    # Features
    features:       List[str] = field(default_factory=list)
    pages:          List[str] = field(default_factory=list)

    # Deploy
    deploy_target:  str  = "render"
    github_auto:    bool = True
    docker_needed:  bool = False
    env_vars:       List[str] = field(default_factory=list)

    # Meta
    license_type:   str  = "MIT"
    is_private:     bool = False
    ai_model_hint:  str  = ""

    def is_complete(self) -> bool:
        """Check if minimum required fields are filled."""
        return bool(
            self.name and
            self.description and
            self.project_type
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":           self.name,
            "description":    self.description,
            "project_type":   self.project_type,
            "stack":          self.stack,
            "frontend":       self.frontend,
            "backend":        self.backend,
            "database":       self.database,
            "auth_required":  self.auth_required,
            "api_required":   self.api_required,
            "platforms":      self.platforms,
            "mobile_first":   self.mobile_first,
            "style":          self.style,
            "color_scheme":   self.color_scheme,
            "animations":     self.animations,
            "responsive":     self.responsive,
            "logo_needed":    self.logo_needed,
            "background_type":self.background_type,
            "features":       self.features,
            "pages":          self.pages,
            "deploy_target":  self.deploy_target,
            "github_auto":    self.github_auto,
            "docker_needed":  self.docker_needed,
            "env_vars":       self.env_vars,
            "license_type":   self.license_type,
            "is_private":     self.is_private,
        }

    def to_build_prompt(self) -> str:
        """Convert spec to a detailed AI build prompt."""
        platforms_str = ", ".join(self.platforms) if self.platforms else "web"
        features_str  = "\n".join(f"- {f}" for f in self.features) if self.features else "- Standard features"
        pages_str     = "\n".join(f"- {p}" for p in self.pages) if self.pages else "- Auto-determine pages"

        return f"""Build a complete, production-ready project with these specifications:

PROJECT IDENTITY:
- Name: {self.name}
- Description: {self.description}
- Type: {self.project_type}

TECHNICAL STACK:
- Stack: {self.stack or "Choose best stack for this project type"}
- Frontend: {self.frontend or "Auto-select"}
- Backend: {self.backend or "Auto-select"}
- Database: {self.database}
- Auth required: {self.auth_required}
- API required: {self.api_required}

TARGET PLATFORMS:
- Platforms: {platforms_str}
- Mobile first: {self.mobile_first}
- Responsive: {self.responsive}

DESIGN & STYLE:
- Visual style: {self.style}
- Color scheme: {self.color_scheme}
- Animations: {self.animations}
- Background type: {self.background_type}
- Logo needed: {self.logo_needed}

REQUIRED FEATURES:
{features_str}

PAGES/SECTIONS:
{pages_str}

DEPLOYMENT:
- Deploy target: {self.deploy_target}
- GitHub auto-push: {self.github_auto}
- Docker: {self.docker_needed}
- Environment variables needed: {', '.join(self.env_vars) if self.env_vars else 'Standard'}

REQUIREMENTS:
- Generate ALL files completely (no stubs, no placeholders)
- Include proper error handling
- Add comprehensive comments
- Follow best practices for the chosen stack
- Include README.md with setup instructions
- Include .env.example
- Include .gitignore
- Wrap each file in: <file path="relative/path/file.ext">content</file>
- After all files, output: <structure>full folder tree</structure>
"""


# ── QUESTION DEFINITIONS ──────────────────────────────────
QUESTION_BANK: Dict[str, Question] = {

    "project_name": Question(
        key      = "project_name",
        text     = "What is the name of your project?",
        hint     = "e.g., 'my-app', 'CyberStore', 'TaskFlow'",
        required = True,
        validator = lambda v: (
            len(v.strip()) >= 2,
            "Name must be at least 2 characters"
        ),
    ),

    "description": Question(
        key      = "description",
        text     = "Briefly describe what this project does.",
        hint     = "e.g., 'A SaaS platform for managing tasks with AI assistance'",
        required = True,
        validator = lambda v: (
            len(v.strip()) >= 10,
            "Description must be at least 10 characters"
        ),
    ),

    "project_type": Question(
        key     = "project_type",
        text    = "What type of project is this?",
        hint    = "Choose the closest match",
        choices = [
            "web",      "api",       "saas",
            "desktop",  "mobile",    "fullstack",
            "ecommerce","dashboard", "portfolio",
            "blog",     "cli",       "bot",
            "data",     "ml",
        ],
        default  = "web",
        required = True,
    ),

    "tech_stack": Question(
        key     = "tech_stack",
        text    = "What tech stack should be used?",
        hint    = "Or type 'auto' to let AI decide",
        choices = [
            "React + Node.js",
            "React + FastAPI (Python)",
            "Next.js + PostgreSQL",
            "Vue.js + Django",
            "Svelte + FastAPI",
            "HTML/CSS/JS (vanilla)",
            "Python + Flask",
            "Python + FastAPI",
            "React Native (mobile)",
            "auto",
        ],
        default  = "auto",
        required = False,
    ),

    "platforms": Question(
        key          = "platforms",
        text         = "Which platforms should this run on?",
        hint         = "Select all that apply",
        choices      = ["web", "windows", "macos", "linux", "android", "all"],
        multi_select = True,
        default      = ["web"],
        required     = True,
    ),

    "style": Question(
        key     = "style",
        text    = "What visual style do you want?",
        hint    = "Affects colors, fonts, animations",
        choices = [
            "dark",         "light",
            "minimal",      "colorful",
            "corporate",    "horror",
            "cyberpunk",    "glassmorphism",
            "auto",
        ],
        default  = "dark",
        required = False,
    ),

    "color_scheme": Question(
        key     = "color_scheme",
        text    = "What color scheme?",
        hint    = "Primary color palette",
        choices = [
            "purple-black",  "red-black",
            "blue-dark",     "green-dark",
            "orange-dark",   "white-minimal",
            "auto",
        ],
        default     = "purple-black",
        required    = False,
        depends_on  = {"style": ["dark", "cyberpunk", "horror"]},
    ),

    "database": Question(
        key     = "database",
        text    = "Does this project need a database?",
        choices = [
            "none",       "sqlite",
            "postgresql", "mysql",
            "mongodb",    "supabase",
            "firebase",   "redis",
        ],
        default  = "none",
        required = False,
    ),

    "auth_required": Question(
        key     = "auth_required",
        text    = "Does this project need user authentication?",
        choices = ["yes", "no"],
        default = "no",
        depends_on = {
            "project_type": [
                "saas", "ecommerce", "dashboard",
                "fullstack", "web"
            ]
        },
    ),

    "features": Question(
        key          = "features",
        text         = "What key features should be included?",
        hint         = "Comma-separated or select from list",
        choices      = [
            "user auth",      "dashboard",
            "file upload",    "email system",
            "payment system", "admin panel",
            "API docs",       "dark mode toggle",
            "search",         "notifications",
            "charts/graphs",  "export (PDF/CSV)",
            "multi-language", "PWA support",
        ],
        multi_select = True,
        required     = False,
    ),

    "pages": Question(
        key          = "pages",
        text         = "What pages/sections are needed?",
        hint         = "For web projects",
        choices      = [
            "Landing/Home",   "About",
            "Features",       "Pricing",
            "Contact",        "Blog",
            "Dashboard",      "Login/Register",
            "Profile",        "Settings",
            "Admin",          "404",
        ],
        multi_select = True,
        required     = False,
        depends_on   = {
            "project_type": [
                "web", "saas", "ecommerce",
                "portfolio", "blog", "dashboard"
            ]
        },
    ),

    "deploy_target": Question(
        key     = "deploy_target",
        text    = "Where should this be deployed?",
        choices = [
            "render",    "vercel",
            "railway",   "fly.io",
            "netlify",   "github-pages",
            "none",
        ],
        default  = "render",
        required = False,
    ),

    "background_type": Question(
        key     = "background_type",
        text    = "What kind of background for the UI?",
        choices = [
            "animated particles",
            "animated gradient",
            "video background",
            "static image",
            "plain dark",
            "auto",
        ],
        default  = "animated particles",
        required = False,
        depends_on = {
            "project_type": ["web", "saas", "portfolio", "landing"]
        },
    ),

    "github_private": Question(
        key     = "github_private",
        text    = "Should the GitHub repository be private?",
        choices = ["yes", "no"],
        default = "no",
        required = False,
    ),
}


# ── QUESTION SESSION ──────────────────────────────────────
@dataclass
class QuestionSession:
    """Tracks progress of a question-answer session."""
    session_id:   str
    started_at:   float = field(default_factory=time.time)
    answers:      Dict[str, Any] = field(default_factory=dict)
    skipped:      Set[str] = field(default_factory=set)
    queue:        List[str] = field(default_factory=list)
    current_idx:  int = 0
    is_complete:  bool = False
    spec:         ProjectSpec = field(default_factory=ProjectSpec)

    @property
    def progress_pct(self) -> float:
        if not self.queue:
            return 0.0
        return (self.current_idx / len(self.queue)) * 100

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at

    def current_question_key(self) -> Optional[str]:
        if self.current_idx < len(self.queue):
            return self.queue[self.current_idx]
        return None

    def record_answer(self, key: str, value: Any) -> None:
        self.answers[key] = value
        if self.current_idx < len(self.queue):
            self.current_idx += 1


# ── QUESTION ENGINE ───────────────────────────────────────
class QuestionEngine:
    """
    Manages the Q&A flow before building a project.

    Flow:
    1. Determine which questions to ask (based on project type)
    2. Ask questions one by one
    3. Apply smart defaults for skipped questions
    4. Build ProjectSpec from answers
    5. Generate AI build prompt
    """

    def __init__(
        self,
        on_question:    Optional[Callable] = None,
        on_complete:    Optional[Callable] = None,
        on_progress:    Optional[Callable] = None,
        fast_mode:      bool = False,
    ):
        """
        on_question(question, session) -> None
        on_complete(spec) -> None
        on_progress(pct, current_key) -> None
        fast_mode: skip optional questions, use defaults
        """
        self.on_question = on_question
        self.on_complete = on_complete
        self.on_progress = on_progress
        self.fast_mode   = fast_mode

        self._sessions:  Dict[str, QuestionSession] = {}
        self._lock       = threading.Lock()
        self._q_bank     = QUESTION_BANK

        logger.info(
            f"QuestionEngine initialized. "
            f"Questions: {len(self._q_bank)}, "
            f"fast_mode={fast_mode}"
        )

    # ── SESSION MANAGEMENT ────────────────────────────────
    def new_session(self, session_id: Optional[str] = None) -> QuestionSession:
        """Create a new question session."""
        sid = session_id or f"session_{int(time.time())}"
        session = QuestionSession(session_id=sid)

        # Determine initial question queue
        session.queue = self._build_question_queue(project_type=None)

        with self._lock:
            self._sessions[sid] = session

        logger.info(
            f"New session: {sid}, "
            f"questions: {len(session.queue)}"
        )
        return session

    def get_session(self, session_id: str) -> Optional[QuestionSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    # ── QUESTION QUEUE ────────────────────────────────────
    def _build_question_queue(
        self,
        project_type: Optional[str] = None,
    ) -> List[str]:
        """
        Build ordered list of question keys to ask.
        Required questions first, then optional based on project type.
        """
        queue = list(REQUIRED_QUESTIONS)

        if self.fast_mode:
            return queue

        # Add optional questions
        always_optional = [
            "tech_stack",
            "platforms",
            "style",
            "deploy_target",
        ]

        type_specific: Dict[str, List[str]] = {
            "web":       ["color_scheme", "background_type", "pages", "features"],
            "saas":      ["database", "auth_required", "features", "pages", "github_private"],
            "api":       ["database", "auth_required", "features"],
            "desktop":   ["platforms", "features"],
            "mobile":    ["database", "auth_required", "features"],
            "ecommerce": ["database", "auth_required", "features", "pages"],
            "dashboard": ["database", "auth_required", "features", "pages"],
            "portfolio": ["style", "color_scheme", "pages", "background_type"],
            "blog":      ["database", "pages", "features"],
            "bot":       ["database", "features"],
        }

        for q in always_optional:
            if q not in queue:
                queue.append(q)

        specific = type_specific.get(project_type or "web", [])
        for q in specific:
            if q not in queue:
                queue.append(q)

        # Filter to only questions that exist in bank
        queue = [q for q in queue if q in self._q_bank]

        return queue

    # ── NEXT QUESTION ─────────────────────────────────────
    def get_next_question(
        self, session: QuestionSession
    ) -> Optional[Question]:
        """
        Get the next question to ask in the session.
        Returns None if all questions are answered.
        """
        while session.current_idx < len(session.queue):
            key = session.queue[session.current_idx]
            q   = self._q_bank.get(key)

            if not q:
                session.current_idx += 1
                continue

            # Check dependency condition
            if q.depends_on:
                if not self._check_dependency(q, session.answers):
                    # Skip this question
                    session.skipped.add(key)
                    session.current_idx += 1
                    continue

            # Notify progress
            if self.on_progress:
                try:
                    self.on_progress(session.progress_pct, key)
                except Exception:
                    pass

            return q

        # All done
        session.is_complete = True
        return None

    def _check_dependency(
        self,
        question: Question,
        answers:  Dict[str, Any],
    ) -> bool:
        """
        Check if a question's dependency condition is met.
        depends_on = {"project_type": ["web", "saas"]}
        → Only ask if project_type is "web" or "saas"
        """
        if not question.depends_on:
            return True

        for dep_key, dep_values in question.depends_on.items():
            answer = answers.get(dep_key)
            if answer is None:
                return True  # Dep not answered yet → ask anyway

            if isinstance(dep_values, list):
                if answer not in dep_values:
                    return False
            else:
                if answer != dep_values:
                    return False

        return True

    # ── SUBMIT ANSWER ─────────────────────────────────────
    def submit_answer(
        self,
        session: QuestionSession,
        key:     str,
        value:   Any,
    ) -> Tuple[bool, str]:
        """
        Submit an answer for a question.
        Returns (valid, error_message).
        """
        q = self._q_bank.get(key)
        if not q:
            return False, f"Unknown question: {key}"

        # Clean value
        clean_value = self._clean_answer(value, q)

        # Validate
        if q.validator and clean_value:
            try:
                valid, msg = q.validator(clean_value)
                if not valid:
                    return False, msg
            except Exception as e:
                logger.warning(f"Validator error for '{key}': {e}")

        # Apply default if empty
        if not clean_value and not clean_value == 0:
            if q.default is not None:
                clean_value = q.default
            elif q.required:
                return False, f"'{q.text}' is required"

        # Store
        session.record_answer(key, clean_value)

        # Update question queue if project_type was answered
        if key == "project_name":
            session.spec.name = str(clean_value)
        elif key == "description":
            session.spec.description = str(clean_value)
        elif key == "project_type":
            session.spec.project_type = str(clean_value)
            # Rebuild queue with proper type-specific questions
            old_idx = session.current_idx
            session.queue = self._build_question_queue(str(clean_value))
            session.current_idx = min(old_idx, len(session.queue))

        logger.debug(f"Answer recorded: {key} = {str(clean_value)[:50]}")
        return True, ""

    def _clean_answer(self, value: Any, question: Question) -> Any:
        """Clean and normalize an answer value."""
        if isinstance(value, str):
            value = value.strip()

        # Handle yes/no
        if question.choices == ["yes", "no"]:
            if isinstance(value, str):
                return value.lower() in ("yes", "y", "true", "1")
            return bool(value)

        # Handle multi-select
        if question.multi_select:
            if isinstance(value, str):
                # Parse comma-separated or single value
                parts = [v.strip() for v in value.split(",")]
                return [p for p in parts if p]
            if isinstance(value, list):
                return value
            return [value] if value else []

        # Handle "auto" → use default
        if value == "auto" and question.default:
            return question.default

        return value

    # ── SKIP QUESTION ─────────────────────────────────────
    def skip_question(
        self, session: QuestionSession, key: str
    ) -> None:
        """Skip a question and use its default value."""
        q = self._q_bank.get(key)
        if q and q.default is not None:
            session.answers[key] = q.default
        session.skipped.add(key)
        session.current_idx += 1
        logger.debug(f"Question skipped: {key}")

    def skip_all_remaining(self, session: QuestionSession) -> None:
        """Skip all remaining questions with defaults."""
        while session.current_idx < len(session.queue):
            key = session.queue[session.current_idx]
            self.skip_question(session, key)

    # ── BUILD SPEC FROM ANSWERS ───────────────────────────
    def build_spec(self, session: QuestionSession) -> ProjectSpec:
        """Convert session answers to ProjectSpec."""
        a    = session.answers
        spec = ProjectSpec()

        # Identity
        spec.name         = str(a.get("project_name", "my-project"))
        spec.description  = str(a.get("description", ""))
        spec.project_type = str(a.get("project_type", "web"))

        # Technical
        stack_raw = str(a.get("tech_stack", "auto"))
        if stack_raw != "auto":
            spec.stack = stack_raw
            if "+" in stack_raw:
                parts         = stack_raw.split("+")
                spec.frontend = parts[0].strip()
                spec.backend  = parts[1].strip() if len(parts) > 1 else ""
        else:
            spec.stack = self._auto_select_stack(spec.project_type)

        spec.database      = str(a.get("database", "none"))
        spec.auth_required = bool(a.get("auth_required", False))
        spec.api_required  = spec.backend != "" or spec.project_type in ("api", "saas")

        # Platform
        platforms_raw = a.get("platforms", ["web"])
        if isinstance(platforms_raw, str):
            if platforms_raw == "all":
                spec.platforms = ["web", "windows", "macos", "linux", "android"]
            else:
                spec.platforms = [platforms_raw]
        else:
            if "all" in platforms_raw:
                spec.platforms = ["web", "windows", "macos", "linux", "android"]
            else:
                spec.platforms = list(platforms_raw)

        spec.mobile_first = "android" in spec.platforms or "ios" in spec.platforms

        # Design
        spec.style          = str(a.get("style", "dark"))
        spec.color_scheme   = str(a.get("color_scheme", "purple-black"))
        spec.animations     = True  # Always on
        spec.responsive     = True  # Always on
        spec.background_type = str(a.get("background_type", "animated particles"))

        # Features and pages
        features_raw = a.get("features", [])
        spec.features = (
            features_raw if isinstance(features_raw, list)
            else [features_raw] if features_raw else []
        )

        pages_raw = a.get("pages", [])
        spec.pages = (
            pages_raw if isinstance(pages_raw, list)
            else [pages_raw] if pages_raw else []
        )

        # Deploy
        spec.deploy_target = str(a.get("deploy_target", "render"))
        spec.github_auto   = True
        spec.is_private    = bool(a.get("github_private", False))

        # Logo
        spec.logo_needed = True

        session.spec = spec

        # Notify completion
        if self.on_complete:
            try:
                self.on_complete(spec)
            except Exception as e:
                logger.error(f"on_complete callback error: {e}")

        logger.info(
            f"ProjectSpec built: {spec.name} ({spec.project_type}) "
            f"stack={spec.stack} platforms={spec.platforms}"
        )

        return spec

    # ── AUTO STACK SELECTION ──────────────────────────────
    def _auto_select_stack(self, project_type: str) -> str:
        """Auto-select best tech stack based on project type."""
        defaults: Dict[str, str] = {
            "web":       "HTML + CSS + Vanilla JS",
            "api":       "FastAPI (Python)",
            "saas":      "React + FastAPI + PostgreSQL",
            "desktop":   "PyQt6 (Python)",
            "mobile":    "React Native",
            "fullstack": "Next.js + FastAPI",
            "ecommerce": "Next.js + FastAPI + PostgreSQL",
            "dashboard": "React + FastAPI + PostgreSQL",
            "portfolio": "HTML + CSS + JavaScript",
            "blog":      "Next.js + MDX",
            "cli":       "Python + Click",
            "bot":       "Python + discord.py",
            "data":      "Python + Pandas + FastAPI",
            "ml":        "Python + FastAPI + scikit-learn",
        }
        return defaults.get(project_type, "HTML + CSS + JavaScript")

    # ── QUICK SPEC FROM PROMPT ────────────────────────────
    def quick_spec_from_prompt(self, prompt: str) -> ProjectSpec:
        """
        Parse a free-text prompt into a ProjectSpec.
        Used when user types everything in one line.
        e.g., "Create a dark SaaS app called TaskFlow with auth and dashboard"
        """
        prompt_lower = prompt.lower()
        spec = ProjectSpec()

        # Extract project name (quoted or capitalized)
        name_match = re.search(
            r'(?:called|named|name[d]?\s+is?)\s+["\']?([A-Za-z0-9\-_]+)["\']?',
            prompt, re.IGNORECASE
        )
        if name_match:
            spec.name = name_match.group(1)
        else:
            # First capitalized word that isn't a common word
            common = {"create","build","make","a","an","the","with","for","my"}
            words  = prompt.split()
            for w in words:
                clean = re.sub(r'[^\w]', '', w)
                if clean and clean[0].isupper() and clean.lower() not in common:
                    spec.name = clean
                    break

        if not spec.name:
            spec.name = "my-project"

        # Project type
        type_keywords = {
            "saas":      ["saas", "subscription", "platform"],
            "api":       ["api", "rest api", "endpoint", "backend"],
            "ecommerce": ["shop", "store", "ecommerce", "e-commerce"],
            "dashboard": ["dashboard", "admin panel", "analytics"],
            "portfolio": ["portfolio", "personal site", "resume"],
            "blog":      ["blog", "articles", "posts"],
            "mobile":    ["mobile", "android", "ios", "app"],
            "desktop":   ["desktop", "gui", "window app"],
            "bot":       ["bot", "discord bot", "telegram bot"],
            "cli":       ["cli", "command line", "terminal tool"],
        }
        spec.project_type = "web"  # default
        for ptype, keywords in type_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                spec.project_type = ptype
                break

        # Description
        spec.description = prompt[:200]

        # Stack detection
        stack_keywords = {
            "React + FastAPI": ["react", "fastapi"],
            "Next.js + PostgreSQL": ["nextjs", "next.js"],
            "Vue.js + Django": ["vue", "django"],
            "HTML + CSS + JavaScript": ["html", "vanilla", "static"],
            "Python + Flask": ["flask"],
            "React Native": ["react native"],
        }
        for stack, keywords in stack_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                spec.stack = stack
                break

        # Style
        if any(w in prompt_lower for w in ["dark", "horror", "scary"]):
            spec.style = "dark"
        elif "light" in prompt_lower:
            spec.style = "light"
        elif "cyberpunk" in prompt_lower:
            spec.style = "cyberpunk"

        # Features
        feature_keywords = {
            "user auth": ["auth", "login", "register", "authentication"],
            "dashboard": ["dashboard"],
            "payment system": ["payment", "stripe", "billing"],
            "file upload": ["file upload", "upload"],
            "API docs": ["api docs", "swagger", "openapi"],
        }
        spec.features = []
        for feature, keywords in feature_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                spec.features.append(feature)

        # Database
        if any(w in prompt_lower for w in ["database", "db", "postgresql", "mysql"]):
            spec.database = "postgresql"
        elif "mongodb" in prompt_lower:
            spec.database = "mongodb"
        elif "sqlite" in prompt_lower:
            spec.database = "sqlite"

        # Auth
        spec.auth_required = any(
            w in prompt_lower for w in ["auth", "login", "register"]
        )

        # Stack default if not found
        if not spec.stack:
            spec.stack = self._auto_select_stack(spec.project_type)

        logger.info(
            f"Quick spec parsed: {spec.name} ({spec.project_type}) "
            f"from prompt '{prompt[:60]}...'"
        )

        return spec

    # ── INTERACTIVE CLI MODE ──────────────────────────────
    def run_cli_session(self) -> Optional[ProjectSpec]:
        """
        Run an interactive CLI question session.
        Used when running without GUI.
        """
        print("\n" + "=" * 55)
        print(f" ShadowForge OS — Project Setup Wizard")
        print("=" * 55)
        print("Answer the following questions to set up your project.")
        print("Press Enter to use the default value [shown in brackets].")
        print("=" * 55 + "\n")

        session = self.new_session()

        while True:
            q = self.get_next_question(session)
            if q is None:
                break

            # Display question
            print(f"\n{'─'*50}")
            print(f"[{session.current_idx}/{len(session.queue)}] {q.text}")

            if q.hint:
                print(f"  Hint: {q.hint}")

            if q.choices:
                if q.multi_select:
                    print(f"  Options (comma-separated): {', '.join(q.choices)}")
                else:
                    print(f"  Options: {', '.join(q.choices)}")

            if q.default is not None:
                default_str = (
                    ', '.join(q.default)
                    if isinstance(q.default, list)
                    else str(q.default)
                )
                print(f"  Default: [{default_str}]")

            # Get input
            try:
                user_input = input("  → ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\nSetup cancelled.")
                return None

            # Handle empty (use default)
            if not user_input and q.default is not None:
                valid, err = self.submit_answer(session, q.key, q.default)
            elif user_input.lower() in ("skip", "s", ""):
                self.skip_question(session, q.key)
                continue
            else:
                valid, err = self.submit_answer(session, q.key, user_input)
                if not valid:
                    print(f"  ✗ {err}")
                    continue  # Re-ask

        # Build spec
        spec = self.build_spec(session)

        print("\n" + "=" * 55)
        print(" Project Specification Summary:")
        print("=" * 55)
        print(f"  Name:     {spec.name}")
        print(f"  Type:     {spec.project_type}")
        print(f"  Stack:    {spec.stack}")
        print(f"  Platform: {', '.join(spec.platforms)}")
        print(f"  Style:    {spec.style}")
        print(f"  Deploy:   {spec.deploy_target}")
        print("=" * 55)

        confirm = input("\nProceed with building? [Y/n]: ").strip().lower()
        if confirm in ("n", "no"):
            print("Build cancelled.")
            return None

        return spec

    # ── STATS ─────────────────────────────────────────────
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_questions": len(self._q_bank),
                "active_sessions": len(self._sessions),
                "fast_mode":       self.fast_mode,
            }
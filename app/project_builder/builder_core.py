# ============================================================
# SHADOWFORGE OS — PROJECT BUILDER CORE
# Orchestrates the full project generation pipeline.
# Questions → Blueprint → Code → Files → GitHub → Deploy.
# ============================================================

import json
import time
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.logger import get_logger, Timer
from core.constants import (
    WORKSPACE_DIR, BUILDER_SUPPORTED_TYPES,
    CODE_EXTENSIONS, ARCHIVE_EXTENSIONS,
)

logger = get_logger("Builder.Core")


# ── BUILD PHASES ──────────────────────────────────────────
class BuildPhase(str, Enum):
    PLANNING    = "planning"
    QUESTIONING = "questioning"
    BLUEPRINTING= "blueprinting"
    GENERATING  = "generating"
    VALIDATING  = "validating"
    PACKAGING   = "packaging"
    DEPLOYING   = "deploying"
    COMPLETE    = "complete"
    FAILED      = "failed"


# ── PROJECT SPEC ──────────────────────────────────────────
@dataclass
class ProjectSpec:
    """Complete specification for a project to be built."""
    name:               str
    type:               str             # web, api, saas, cli, etc.
    description:        str
    platform:           List[str]       # web, desktop, mobile
    stack:              Dict[str, str]  # frontend, backend, database, etc.
    features:           List[str]
    style:              Dict[str, str]  # colors, fonts, theme
    auth_required:      bool  = False
    database:           str   = ""
    deployment_target:  str   = "render"
    logo_style:         str   = "minimal"
    background_type:    str   = "animated"
    has_dark_theme:     bool  = True
    github_push:        bool  = False
    workspace_path:     Optional[Path] = None
    created_at:         str   = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    metadata:           Dict[str, Any] = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Convert spec to a context string for AI prompts."""
        lines = [
            f"PROJECT: {self.name}",
            f"TYPE: {self.type}",
            f"DESCRIPTION: {self.description}",
            f"PLATFORM: {', '.join(self.platform)}",
            f"FRONTEND: {self.stack.get('frontend', 'HTML/CSS/JS')}",
            f"BACKEND: {self.stack.get('backend', 'Python/FastAPI')}",
            f"DATABASE: {self.database or 'None'}",
            f"FEATURES: {', '.join(self.features)}",
            f"AUTH: {'Yes' if self.auth_required else 'No'}",
            f"THEME: {self.style.get('theme', 'dark')}",
            f"COLORS: {self.style.get('colors', 'dark purple + red')}",
            f"DEPLOY: {self.deployment_target}",
        ]
        return "\n".join(lines)


# ── BUILD RESULT ──────────────────────────────────────────
@dataclass
class BuildResult:
    success:        bool
    project_name:   str
    workspace_path: Optional[Path]
    files_created:  int   = 0
    errors:         List[str] = field(default_factory=list)
    warnings:       List[str] = field(default_factory=list)
    duration_s:     float = 0.0
    github_url:     str   = ""
    deploy_url:     str   = ""
    phase:          BuildPhase = BuildPhase.COMPLETE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success":      self.success,
            "name":         self.project_name,
            "path":         str(self.workspace_path) if self.workspace_path else "",
            "files":        self.files_created,
            "errors":       self.errors,
            "warnings":     self.warnings,
            "duration":     round(self.duration_s, 2),
            "github":       self.github_url,
            "deploy":       self.deploy_url,
        }


# ── BUILDER CORE ──────────────────────────────────────────
class BuilderCore:
    """
    Main project generation orchestrator.

    Pipeline:
    1. Receive project spec (from Q&A engine)
    2. Generate AI blueprint
    3. Generate all project files
    4. Validate output
    5. Package for deployment
    6. Optional: push to GitHub
    """

    def __init__(self, config, agent_core=None):
        self.config      = config
        self._agent      = agent_core
        self._phase      = BuildPhase.PLANNING
        self._listeners: List[Callable] = []
        self._current_build: Optional[BuildResult] = None

        logger.info("BuilderCore initialized.")

    # ── EVENT LISTENERS ───────────────────────────────────
    def add_listener(self, callback: Callable) -> None:
        self._listeners.append(callback)

    def _notify(self, event: str, data: Dict[str, Any]) -> None:
        for cb in self._listeners:
            try:
                cb(event, data)
            except Exception:
                pass

    def _set_phase(self, phase: BuildPhase) -> None:
        self._phase = phase
        self._notify("phase_change", {
            "phase":    phase.value,
            "label":    phase.value.replace("_", " ").title(),
        })
        logger.info(f"Build phase: {phase.value}")

    # ── MAIN BUILD ────────────────────────────────────────
    def build(
        self,
        spec:          ProjectSpec,
        progress_cb:   Optional[Callable] = None,
    ) -> BuildResult:
        """
        Execute full project build from spec.
        Returns BuildResult with all details.
        """
        start_time = time.perf_counter()
        logger.info(f"Starting build: {spec.name} ({spec.type})")

        if progress_cb:
            self.add_listener(progress_cb)

        # Setup workspace
        workspace = self._setup_workspace(spec)
        spec.workspace_path = workspace

        result = BuildResult(
            success        = False,
            project_name   = spec.name,
            workspace_path = workspace,
        )
        self._current_build = result

        try:
            # Phase 1: Generate blueprint
            self._set_phase(BuildPhase.BLUEPRINTING)
            blueprint = self._generate_blueprint(spec)
            self._notify("blueprint_ready", {"blueprint": blueprint[:500]})

            # Phase 2: Generate all files
            self._set_phase(BuildPhase.GENERATING)
            files_created = self._generate_files(spec, blueprint, workspace)
            result.files_created = files_created

            # Phase 3: Generate configs and docs
            self._generate_configs(spec, workspace)
            self._generate_readme(spec, workspace)
            self._generate_env_example(spec, workspace)
            self._generate_gitignore(workspace)

            # Phase 4: Validate
            self._set_phase(BuildPhase.VALIDATING)
            errors, warnings = self._validate_project(workspace)
            result.errors   = errors
            result.warnings = warnings

            if errors:
                logger.warning(f"Build has {len(errors)} errors.")
                self._notify("validation_errors", {"errors": errors})

            # Phase 5: Package
            self._set_phase(BuildPhase.PACKAGING)
            zip_path = self._create_zip(workspace)
            self._notify("packaged", {"zip": str(zip_path)})

            # Phase 6: GitHub push (if requested)
            if spec.github_push and self.config.has("GITHUB_TOKEN"):
                self._set_phase(BuildPhase.DEPLOYING)
                github_url = self._push_to_github(spec, workspace)
                result.github_url = github_url

            # Done
            result.success    = True
            result.duration_s = time.perf_counter() - start_time
            self._set_phase(BuildPhase.COMPLETE)

            logger.info(
                f"Build complete: {spec.name} | "
                f"files={result.files_created} | "
                f"errors={len(result.errors)} | "
                f"duration={result.duration_s:.1f}s"
            )

            self._notify("build_complete", result.to_dict())
            return result

        except Exception as e:
            result.errors.append(str(e))
            result.duration_s = time.perf_counter() - start_time
            self._set_phase(BuildPhase.FAILED)
            logger.error(f"Build failed: {e}", exc_info=True)
            self._notify("build_failed", {"error": str(e)})
            return result

    # ── WORKSPACE SETUP ───────────────────────────────────
    def _setup_workspace(self, spec: ProjectSpec) -> Path:
        """Create clean project workspace directory."""
        import re
        safe_name = re.sub(r'[^\w\-_]', '_', spec.name.strip().lower())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workspace = WORKSPACE_DIR / f"{safe_name}_{timestamp}"
        workspace.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace: {workspace}")
        return workspace

    # ── BLUEPRINT GENERATION ──────────────────────────────
    def _generate_blueprint(self, spec: ProjectSpec) -> str:
        """Use AI to generate a detailed project blueprint."""
        if not self._agent:
            return self._default_blueprint(spec)

        prompt = f"""
Generate a detailed technical blueprint for this project.

{spec.to_prompt_context()}

Output a JSON blueprint with this structure:
{{
  "folder_structure": ["list of all folders"],
  "files": [
    {{"path": "relative/path/file.ext", "description": "what this file does"}},
    ...
  ],
  "dependencies": {{"frontend": [], "backend": [], "dev": []}},
  "api_routes": ["{{"method": "GET", "path": "/api/..."}}"],
  "database_tables": [],
  "env_vars": ["VAR_NAME=description"]
}}

Include ALL files needed for a production-ready project.
Be specific. Don't omit files.
""".strip()

        try:
            from agent.agent_core import MessageRole
            response = self._agent.provider_manager.complete(
                messages = [
                    {"role": "system", "content": "You are a senior software architect. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens  = 4096,
                temperature = 0.3,
            )

            content = response.get("content", "")

            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    blueprint_data = json.loads(json_match.group())
                    return json.dumps(blueprint_data, indent=2)
                except json.JSONDecodeError:
                    pass

            return content

        except Exception as e:
            logger.warning(f"Blueprint generation failed: {e}. Using default.")
            return self._default_blueprint(spec)

    def _default_blueprint(self, spec: ProjectSpec) -> str:
        """Default blueprint when AI is unavailable."""
        structure = {
            "folder_structure": [
                "src", "src/components", "src/pages", "src/api",
                "public", "public/assets", "config", "tests", "docs",
            ],
            "files": [
                {"path": "src/main.py", "description": "Entry point"},
                {"path": "src/config.py", "description": "Configuration"},
                {"path": "requirements.txt", "description": "Dependencies"},
                {"path": ".env.example", "description": "Environment template"},
                {"path": "README.md", "description": "Documentation"},
                {"path": ".gitignore", "description": "Git ignore rules"},
            ],
            "dependencies": {"backend": ["fastapi", "uvicorn"], "dev": ["pytest"]},
        }
        return json.dumps(structure, indent=2)

    # ── FILE GENERATION ───────────────────────────────────
    def _generate_files(
        self,
        spec:      ProjectSpec,
        blueprint: str,
        workspace: Path,
    ) -> int:
        """Generate all project files using AI."""
        if not self._agent:
            logger.warning("No agent available — creating skeleton only.")
            return self._create_skeleton(workspace, blueprint)

        prompt = f"""
Generate a COMPLETE, production-ready {spec.type} project.

PROJECT CONTEXT:
{spec.to_prompt_context()}

BLUEPRINT:
{blueprint[:2000]}

RULES:
1. Generate ALL files listed in the blueprint
2. Each file must be COMPLETE — no placeholders, no "TODO", no "..."
3. Wrap each file in: <file path="path/to/file.ext">CONTENT</file>
4. Include ALL imports, ALL functions, production-ready code
5. Follow best practices for the chosen stack
6. Make it actually work out of the box

Generate the most important files first.
Include: main entry point, config, all components, routes, models, tests, README.
""".strip()

        try:
            response = self._agent.provider_manager.complete(
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a senior full-stack developer. "
                            "Generate complete, production-ready code. "
                            "Use <file path='...'> tags for each file. "
                            "Never truncate. Always complete."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens  = 8192,
                temperature = 0.4,
            )

            content = response.get("content", "")
            return self._write_files_from_response(content, workspace)

        except Exception as e:
            logger.error(f"File generation failed: {e}")
            return self._create_skeleton(workspace, blueprint)

    def _write_files_from_response(
        self, response: str, workspace: Path
    ) -> int:
        """Parse <file> tags and write files to workspace."""
        import re
        pattern = re.compile(
            r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>',
            re.DOTALL | re.IGNORECASE,
        )

        written = 0
        for rel_path_str, content in pattern.findall(response):
            try:
                target = (workspace / rel_path_str.lstrip("/\\")).resolve()

                # Security check
                if not str(target).startswith(str(workspace.resolve())):
                    logger.warning(f"Path traversal blocked: {rel_path_str}")
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content.strip())

                written += 1
                self._notify("file_written", {
                    "path": str(target.relative_to(workspace)),
                    "size": len(content),
                })

            except Exception as e:
                logger.warning(f"Could not write {rel_path_str}: {e}")

        logger.info(f"Files written from AI response: {written}")
        return written

    def _create_skeleton(self, workspace: Path, blueprint: str) -> int:
        """Create minimal project skeleton when AI is unavailable."""
        created = 0
        try:
            data = json.loads(blueprint)
            folders = data.get("folder_structure", [])
            for folder in folders:
                (workspace / folder).mkdir(parents=True, exist_ok=True)
                created += 1
        except Exception:
            pass
        return created

    # ── CONFIG GENERATION ─────────────────────────────────
    def _generate_configs(self, spec: ProjectSpec, workspace: Path) -> None:
        """Generate deployment and build config files."""

        # Docker (optional)
        dockerfile = workspace / "Dockerfile"
        if not dockerfile.exists():
            docker_content = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
            dockerfile.write_text(docker_content)

        # render.yaml
        render_yaml = workspace / "render.yaml"
        if not render_yaml.exists():
            render_content = f"""services:
  - type: web
    name: {spec.name.lower().replace(' ', '-')}
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
"""
            render_yaml.write_text(render_content)

    # ── README GENERATION ─────────────────────────────────
    def _generate_readme(self, spec: ProjectSpec, workspace: Path) -> None:
        readme_path = workspace / "README.md"
        if readme_path.exists():
            return

        content = f"""# {spec.name}

> {spec.description}

## Stack
- Frontend: {spec.stack.get('frontend', 'HTML/CSS/JS')}
- Backend: {spec.stack.get('backend', 'Python/FastAPI')}
- Database: {spec.database or 'None'}

## Setup

```bash
# Clone
git clone <your-repo-url>
cd {spec.name.lower().replace(' ', '-')}

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run
python -m uvicorn src.main:app --reload
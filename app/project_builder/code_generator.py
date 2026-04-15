# ============================================================
# SHADOWFORGE OS — CODE GENERATOR
# Uses AI to generate actual file contents.
# Smart prompting: generates files in batches by layer.
# Frontend → Backend → Config → Tests → Docs.
# ============================================================

import re
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple, Generator
from dataclasses import dataclass, field
from enum import Enum

from core.logger import get_logger, Timer
from project_builder.builder_core import ProjectSpec

logger = get_logger("Builder.CodeGenerator")


# ── GENERATION LAYER ──────────────────────────────────────
class GenerationLayer(str, Enum):
    CONFIG     = "config"       # Generated first
    CORE       = "core"         # Core business logic
    MODELS     = "models"       # Data models
    SERVICES   = "services"     # Services / business logic
    ROUTES     = "routes"       # API routes / pages
    COMPONENTS = "components"   # UI components
    STYLES     = "styles"       # CSS / styles
    SCRIPTS    = "scripts"      # JavaScript
    TESTS      = "tests"        # Test files
    DOCS       = "docs"         # Documentation
    DEPLOY     = "deploy"       # Deployment configs


# ── FILE GENERATION PLAN ──────────────────────────────────
@dataclass
class FileGenerationPlan:
    path:        str
    layer:       GenerationLayer
    description: str
    depends_on:  List[str] = field(default_factory=list)
    priority:    int       = 5   # 1=highest, 10=lowest
    generated:   bool      = False
    content:     str       = ""
    error:       str       = ""


# ── GENERATION RESULT ─────────────────────────────────────
@dataclass
class GenerationResult:
    total_planned:  int
    total_generated:int
    total_failed:   int
    files:          Dict[str, str]  # path -> content
    errors:         Dict[str, str]  # path -> error
    duration_s:     float
    tokens_used:    int
    provider_used:  str

    @property
    def success_rate(self) -> float:
        if self.total_planned == 0:
            return 0.0
        return self.total_generated / self.total_planned * 100


# ── LAYER-SPECIFIC PROMPTS ────────────────────────────────
LAYER_SYSTEM_PROMPTS = {
    GenerationLayer.CONFIG: """
You are a DevOps and configuration expert.
Generate production-ready configuration files.
Include all required settings, proper defaults, and clear comments.
""",
    GenerationLayer.CORE: """
You are a senior software architect.
Generate clean, well-structured core application code.
Use proper design patterns, type hints, and docstrings.
""",
    GenerationLayer.MODELS: """
You are a database and data modeling expert.
Generate clean data models with proper relationships, indexes, and constraints.
Include validation and serialization.
""",
    GenerationLayer.SERVICES: """
You are a senior backend developer.
Generate service layer code with proper error handling, logging, and business logic.
""",
    GenerationLayer.ROUTES: """
You are a full-stack developer.
Generate complete route handlers with proper HTTP methods, status codes, and error responses.
""",
    GenerationLayer.COMPONENTS: """
You are a senior frontend developer.
Generate clean, reusable UI components with proper props, events, and accessibility.
""",
    GenerationLayer.STYLES: """
You are a CSS expert specializing in dark, cinematic UIs.
Generate clean, well-organized CSS with custom properties, animations, and responsive design.
Use the dark horror-tech aesthetic: black backgrounds, purple glow, blood red accents.
""",
    GenerationLayer.SCRIPTS: """
You are a JavaScript expert.
Generate clean, modular JavaScript with proper error handling and modern ES6+ syntax.
""",
    GenerationLayer.TESTS: """
You are a testing expert.
Generate comprehensive tests covering happy paths, edge cases, and error conditions.
Include proper fixtures, mocks, and assertions.
""",
    GenerationLayer.DOCS: """
You are a technical writer.
Generate clear, comprehensive documentation with examples, setup instructions, and API references.
""",
    GenerationLayer.DEPLOY: """
You are a DevOps engineer.
Generate production-ready deployment configurations for the specified platform.
Include environment variable documentation and deployment steps.
""",
}


# ── FILE CLASSIFIER ───────────────────────────────────────
def classify_file(path: str) -> Tuple[GenerationLayer, int]:
    """
    Classify a file path into a generation layer and priority.
    Returns (layer, priority).
    """
    path_lower = path.lower()

    # Config files (highest priority — generated first)
    if any(name in path_lower for name in [
        "config", ".env", "settings", "constants",
        "requirements.txt", "package.json", "pyproject.toml",
        "tsconfig", "vite.config", "webpack", "babel",
    ]):
        return GenerationLayer.CONFIG, 1

    # Deploy files
    if any(name in path_lower for name in [
        "dockerfile", "docker-compose", "render.yaml",
        ".github/workflows", "makefile", "nginx",
        "gunicorn", "supervisor",
    ]):
        return GenerationLayer.DEPLOY, 2

    # Models
    if any(name in path_lower for name in [
        "model", "schema", "entity", "migration",
        "database", "db.py",
    ]):
        return GenerationLayer.MODELS, 3

    # Core / main
    if any(name in path_lower for name in [
        "main.py", "main.ts", "main.tsx", "app.py",
        "index.ts", "server.py", "server.ts",
        "core/", "base.py",
    ]):
        return GenerationLayer.CORE, 3

    # Services
    if "service" in path_lower or "services/" in path_lower:
        return GenerationLayer.SERVICES, 4

    # Routes / API
    if any(name in path_lower for name in [
        "route", "router", "api/", "endpoint",
        "controller", "handler",
    ]):
        return GenerationLayer.ROUTES, 5

    # Components (UI)
    if any(name in path_lower for name in [
        "component", "widget", "page", "view",
        ".tsx", ".jsx", ".vue", ".svelte",
    ]):
        return GenerationLayer.COMPONENTS, 6

    # Styles
    if any(ext in path_lower for ext in [
        ".css", ".scss", ".sass", ".less",
        "style", "theme",
    ]):
        return GenerationLayer.STYLES, 6

    # JavaScript
    if path_lower.endswith(".js") or path_lower.endswith(".ts"):
        return GenerationLayer.SCRIPTS, 7

    # Tests
    if any(name in path_lower for name in [
        "test", "spec", "conftest", "__test__",
    ]):
        return GenerationLayer.TESTS, 8

    # Docs
    if any(name in path_lower for name in [
        "readme", ".md", "doc", "changelog", "license",
    ]):
        return GenerationLayer.DOCS, 9

    # Default
    return GenerationLayer.CORE, 5


# ── CODE GENERATOR ────────────────────────────────────────
class CodeGenerator:
    """
    AI-powered code generator for ShadowForge projects.

    Generates complete file contents using AI.
    Works in layers: config → core → models → services → routes → UI → tests.
    Supports batched generation for large projects.
    """

    MAX_FILES_PER_BATCH = 5
    MAX_TOKENS_PER_FILE = 3000
    MAX_TOTAL_TOKENS    = 100_000

    def __init__(self, provider_manager=None):
        self._provider = provider_manager
        self._generated_files: Dict[str, str] = {}
        self._generation_log: List[Dict] = []
        self._total_tokens = 0

        logger.info("CodeGenerator initialized.")

    # ── PLAN GENERATION ───────────────────────────────────
    def plan(
        self,
        spec:      ProjectSpec,
        file_list: List[str],
    ) -> List[FileGenerationPlan]:
        """
        Create a prioritized generation plan for all files.
        """
        plans = []

        for path in file_list:
            layer, priority = classify_file(path)
            plans.append(FileGenerationPlan(
                path        = path,
                layer       = layer,
                description = self._describe_file(path, spec),
                priority    = priority,
            ))

        # Sort by priority
        plans.sort(key=lambda p: (p.priority, p.path))

        logger.info(
            f"Generation plan created: {len(plans)} files. "
            f"Layers: {set(p.layer.value for p in plans)}"
        )
        return plans

    def _describe_file(self, path: str, spec: ProjectSpec) -> str:
        """Generate a description for a file based on its path and spec."""
        filename = Path(path).name
        descriptions = {
            "main.py":        f"FastAPI application entry point for {spec.name}",
            "main.tsx":       f"React application entry for {spec.name}",
            "config.py":      f"Configuration management for {spec.name}",
            "database.py":    f"Database connection and session for {spec.database or 'SQLite'}",
            "models":         f"SQLAlchemy/Pydantic models",
            "routes":         f"API route handlers",
            "components":     f"React/Vue UI components",
            "README.md":      f"Project documentation for {spec.name}",
            ".env.example":   f"Environment variables template",
            ".gitignore":     f"Git ignore rules",
            "requirements.txt": f"Python dependencies",
            "package.json":   f"Node.js package configuration",
            "Dockerfile":     f"Docker build configuration",
        }
        for key, desc in descriptions.items():
            if key in path or key == filename:
                return desc
        return f"Implementation for {filename}"

    # ── GENERATE SINGLE FILE ──────────────────────────────
    def generate_file(
        self,
        plan:     FileGenerationPlan,
        spec:     ProjectSpec,
        context:  Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate content for a single file using AI.
        Returns the file content string.
        """
        if not self._provider:
            return self._generate_placeholder(plan, spec)

        system_prompt = LAYER_SYSTEM_PROMPTS.get(
            plan.layer,
            LAYER_SYSTEM_PROMPTS[GenerationLayer.CORE]
        )

        # Build context from already-generated files
        context_str = ""
        if context:
            relevant_context = {
                path: content[:500]
                for path, content in list(context.items())[:3]
            }
            if relevant_context:
                context_str = "EXISTING FILES FOR CONTEXT:\n" + "\n".join(
                    f"--- {p} ---\n{c}"
                    for p, c in relevant_context.items()
                )

        user_prompt = f"""
Generate the complete content for this file:

FILE: {plan.path}
DESCRIPTION: {plan.description}
LAYER: {plan.layer.value}

PROJECT CONTEXT:
{spec.to_prompt_context()}

{context_str}

RULES:
- Generate COMPLETE file content only
- No explanations before or after
- No markdown code fences
- Just the raw file content
- Production-ready code
- Include all imports
- Add brief inline comments for complex logic
- For Python: use type hints, docstrings
- For JavaScript/TypeScript: use ES6+, proper exports
- For CSS: use CSS custom properties, BEM methodology
""".strip()

        try:
            result = self._provider.complete(
                messages = [
                    {"role": "system", "content": system_prompt.strip()},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens  = self.MAX_TOKENS_PER_FILE,
                temperature = 0.3,
            )

            content = result.get("content", "").strip()
            tokens  = result.get("tokens", 0)
            self._total_tokens += tokens

            # Clean up markdown code fences if AI added them
            content = self._strip_code_fences(content, plan.path)

            self._generation_log.append({
                "path":     plan.path,
                "layer":    plan.layer.value,
                "success":  True,
                "tokens":   tokens,
                "length":   len(content),
            })

            logger.debug(
                f"Generated: {plan.path} "
                f"({len(content)} chars, {tokens} tokens)"
            )

            return content

        except Exception as e:
            logger.error(f"Generation failed for {plan.path}: {e}")
            self._generation_log.append({
                "path":    plan.path,
                "success": False,
                "error":   str(e)[:100],
            })
            return self._generate_placeholder(plan, spec)

    def _strip_code_fences(self, content: str, path: str) -> str:
        """Remove markdown code fences that AI sometimes adds."""
        # Pattern: ```lang\nCODE\n```
        pattern = re.compile(
            r'^```[\w]*\n(.*?)```\s*$',
            re.DOTALL
        )
        match = pattern.match(content)
        if match:
            return match.group(1)

        # Also handle ``` without language
        if content.startswith("```") and content.endswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines)

        return content

    def _generate_placeholder(
        self, plan: FileGenerationPlan, spec: ProjectSpec
    ) -> str:
        """Generate a meaningful placeholder when AI is unavailable."""
        ext = Path(plan.path).suffix.lower()

        templates: Dict[str, str] = {
            ".py": (
                f'"""\\n'
                f'{plan.description}\\n'
                f'Generated by ShadowForge OS for {spec.name}\\n'
                f'"""\\n\\n'
                f'# TODO: Implement {Path(plan.path).stem}\\n'
            ),
            ".ts": (
                f'// {plan.description}\\n'
                f'// ShadowForge OS — {spec.name}\\n\\n'
                f'// TODO: Implement\\nexport {{}}\\n'
            ),
            ".tsx": (
                f'// {plan.description}\\nimport React from "react"\\n\\n'
                f'export default function {Path(plan.path).stem}() {{\\n'
                f'  return <div>{Path(plan.path).stem}</div>\\n'
                f'}}\\n'
            ),
            ".js": f'// {plan.description}\\n// TODO: Implement\\n',
            ".css": (
                f'/* {plan.description} */\\n'
                f'/* ShadowForge OS — {spec.name} */\\n\\n'
                f':root {{\\n'
                f'  --color-bg: #05010a;\\n'
                f'  --color-accent: #6600cc;\\n'
                f'  --color-red: #ff0015;\\n'
                f'}}\\n'
            ),
            ".html": (
                f'<!DOCTYPE html>\\n<html lang="en">\\n<head>\\n'
                f'  <meta charset="UTF-8">\\n'
                f'  <title>{spec.name}</title>\\n'
                f'</head>\\n<body>\\n'
                f'  <!-- {plan.description} -->\\n'
                f'</body>\\n</html>\\n'
            ),
            ".md": (
                f'# {spec.name}\\n\\n'
                f'> {spec.description}\\n\\n'
                f'Generated by ShadowForge OS.\\n'
            ),
            ".json": f'{{}}\\n',
            ".yml": f'# {plan.description}\\n# TODO: Configure\\n',
            ".yaml":f'# {plan.description}\\n# TODO: Configure\\n',
        }

        return templates.get(ext, f"# {plan.description}\n# TODO: Implement\n")

    # ── BATCH GENERATION ──────────────────────────────────
    def generate_batch(
        self,
        plans:         List[FileGenerationPlan],
        spec:          ProjectSpec,
        progress_cb:   Optional[Callable] = None,
    ) -> GenerationResult:
        """
        Generate all files in the plan, in order of priority.
        Calls progress_cb(completed, total, current_file) after each file.
        """
        start_time    = time.perf_counter()
        total         = len(plans)
        generated     = 0
        failed        = 0
        files_content: Dict[str, str] = {}
        errors:        Dict[str, str] = {}
        tokens_total  = 0

        logger.info(f"Starting batch generation: {total} files")

        for i, plan in enumerate(plans):
            if self._total_tokens >= self.MAX_TOTAL_TOKENS:
                logger.warning(
                    f"Token limit reached ({self._total_tokens}). "
                    f"Stopping generation."
                )
                break

            # Progress callback
            if progress_cb:
                try:
                    progress_cb(i, total, plan.path)
                except Exception:
                    pass

            # Generate content
            try:
                content = self.generate_file(
                    plan    = plan,
                    spec    = spec,
                    context = {
                        p: c[:300]
                        for p, c in list(files_content.items())[-5:]
                    },
                )

                files_content[plan.path] = content
                plan.generated = True
                plan.content   = content
                generated     += 1

            except Exception as e:
                plan.error = str(e)
                errors[plan.path] = str(e)
                failed += 1
                logger.warning(f"Failed to generate {plan.path}: {e}")

            # Small delay to avoid rate limiting
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)

        duration = time.perf_counter() - start_time

        result = GenerationResult(
            total_planned   = total,
            total_generated = generated,
            total_failed    = failed,
            files           = files_content,
            errors          = errors,
            duration_s      = duration,
            tokens_used     = self._total_tokens,
            provider_used   = getattr(
                self._provider, 'get_best_provider',
                lambda: "unknown"
            )(),
        )

        logger.info(
            f"Batch generation complete: "
            f"{generated}/{total} files | "
            f"tokens={self._total_tokens} | "
            f"duration={duration:.1f}s | "
            f"success_rate={result.success_rate:.1f}%"
        )

        return result

    # ── WRITE TO DISK ─────────────────────────────────────
    def write_to_workspace(
        self,
        result:    GenerationResult,
        workspace: Path,
    ) -> int:
        """
        Write all generated files to the workspace directory.
        Returns count of successfully written files.
        """
        written = 0

        for rel_path, content in result.files.items():
            target = workspace / rel_path

            try:
                # Security: ensure no path traversal
                resolved  = target.resolve()
                workspace_resolved = workspace.resolve()

                if not str(resolved).startswith(str(workspace_resolved)):
                    logger.warning(f"Path traversal blocked: {rel_path}")
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="\n")
                written += 1

            except Exception as e:
                logger.warning(f"Write failed for {rel_path}: {e}")

        logger.info(
            f"Wrote {written}/{len(result.files)} files to workspace."
        )
        return written

    # ── STATS ─────────────────────────────────────────────
    def get_stats(self) -> Dict[str, Any]:
        success = sum(1 for e in self._generation_log if e.get("success"))
        failed  = sum(1 for e in self._generation_log if not e.get("success"))
        return {
            "total_generated":   success,
            "total_failed":      failed,
            "total_tokens_used": self._total_tokens,
            "avg_file_length":   (
                sum(e.get("length", 0) for e in self._generation_log)
                // max(1, success)
            ),
        }

    def reset(self) -> None:
        """Reset generator state for new project."""
        self._generated_files = {}
        self._generation_log  = []
        self._total_tokens    = 0
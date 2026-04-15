# ============================================================
# SHADOWFORGE OS — STRUCTURE GENERATOR
# Generates clean, logical project folder structures.
# Stack-aware: knows what files every type of project needs.
# ============================================================

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from core.logger import get_logger
from project_builder.builder_core import ProjectSpec

logger = get_logger("Builder.Structure")


# ── FILE ENTRY ────────────────────────────────────────────
@dataclass
class FileEntry:
    path:        str
    description: str
    template:    str    = ""   # Template name to use
    required:    bool   = True
    content:     str    = ""   # Static content if any


# ── PROJECT STRUCTURE TEMPLATE ────────────────────────────
@dataclass
class StructureTemplate:
    name:        str
    folders:     List[str]
    files:       List[FileEntry]
    description: str = ""


# ── TEMPLATES BY PROJECT TYPE ─────────────────────────────
def _web_template() -> StructureTemplate:
    return StructureTemplate(
        name    = "web",
        folders = [
            "src", "src/components", "src/pages",
            "src/styles", "src/scripts",
            "public", "public/assets", "public/assets/images",
            "public/assets/fonts", "public/assets/video",
        ],
        files = [
            FileEntry("src/index.html",           "Main HTML entry point"),
            FileEntry("src/styles/main.css",      "Main stylesheet"),
            FileEntry("src/styles/variables.css", "CSS design tokens"),
            FileEntry("src/styles/animations.css","CSS animations"),
            FileEntry("src/styles/responsive.css","Responsive breakpoints"),
            FileEntry("src/scripts/main.js",      "Main JavaScript"),
            FileEntry("src/scripts/animations.js","Animation controllers"),
            FileEntry("src/scripts/particles.js", "Particle system"),
            FileEntry("public/assets/logo.svg",   "Project logo"),
            FileEntry(".env.example",              "Environment template"),
            FileEntry(".gitignore",                "Git ignore"),
            FileEntry("README.md",                 "Documentation"),
        ],
    )


def _api_template() -> StructureTemplate:
    return StructureTemplate(
        name    = "api",
        folders = [
            "src", "src/routes", "src/models",
            "src/services", "src/middleware",
            "src/utils", "src/schemas",
            "tests", "tests/unit", "tests/integration",
            "config", "docs",
        ],
        files = [
            FileEntry("src/main.py",                  "FastAPI app entry"),
            FileEntry("src/config.py",                "App configuration"),
            FileEntry("src/database.py",              "Database connection"),
            FileEntry("src/routes/__init__.py",       "Routes init"),
            FileEntry("src/routes/health.py",         "Health check endpoint"),
            FileEntry("src/routes/auth.py",           "Auth endpoints"),
            FileEntry("src/models/__init__.py",       "Models init"),
            FileEntry("src/models/user.py",           "User model"),
            FileEntry("src/services/__init__.py",     "Services init"),
            FileEntry("src/services/auth_service.py","Auth business logic"),
            FileEntry("src/middleware/cors.py",       "CORS middleware"),
            FileEntry("src/middleware/auth.py",       "JWT auth middleware"),
            FileEntry("src/schemas/user.py",          "Pydantic schemas"),
            FileEntry("src/utils/security.py",        "Password hashing"),
            FileEntry("tests/__init__.py",            "Tests init"),
            FileEntry("tests/conftest.py",            "Pytest fixtures"),
            FileEntry("tests/test_health.py",         "Health endpoint test"),
            FileEntry("requirements.txt",             "Dependencies"),
            FileEntry(".env.example",                 "Environment template"),
            FileEntry(".gitignore",                   "Git ignore"),
            FileEntry("Dockerfile",                   "Docker config"),
            FileEntry("docker-compose.yml",           "Docker compose"),
            FileEntry("render.yaml",                  "Render deploy config"),
            FileEntry("README.md",                    "Documentation"),
            FileEntry("pyproject.toml",               "Project metadata"),
        ],
    )


def _saas_template() -> StructureTemplate:
    return StructureTemplate(
        name    = "saas",
        folders = [
            "frontend", "frontend/src",
            "frontend/src/components", "frontend/src/pages",
            "frontend/src/hooks", "frontend/src/store",
            "frontend/src/styles", "frontend/public",
            "backend", "backend/src",
            "backend/src/api", "backend/src/models",
            "backend/src/services", "backend/src/middleware",
            "backend/src/schemas", "backend/src/utils",
            "backend/tests",
            "shared", "shared/types",
            "config", "docs", "scripts",
            ".github", ".github/workflows",
        ],
        files = [
            # Frontend
            FileEntry("frontend/src/main.tsx",              "React entry point"),
            FileEntry("frontend/src/App.tsx",               "Root component"),
            FileEntry("frontend/src/pages/Home.tsx",        "Home page"),
            FileEntry("frontend/src/pages/Dashboard.tsx",   "User dashboard"),
            FileEntry("frontend/src/pages/Auth.tsx",        "Login/Register"),
            FileEntry("frontend/src/pages/Pricing.tsx",     "Pricing page"),
            FileEntry("frontend/src/components/Navbar.tsx", "Navigation"),
            FileEntry("frontend/src/components/Footer.tsx", "Footer"),
            FileEntry("frontend/src/components/Button.tsx", "Button component"),
            FileEntry("frontend/src/components/Modal.tsx",  "Modal component"),
            FileEntry("frontend/src/hooks/useAuth.ts",      "Auth hook"),
            FileEntry("frontend/src/store/auth.ts",         "Auth state"),
            FileEntry("frontend/src/styles/globals.css",    "Global styles"),
            FileEntry("frontend/package.json",              "Node dependencies"),
            FileEntry("frontend/tsconfig.json",             "TypeScript config"),
            FileEntry("frontend/vite.config.ts",            "Vite build config"),
            FileEntry("frontend/.env.example",              "Frontend env template"),
            # Backend
            FileEntry("backend/src/main.py",                "FastAPI entry"),
            FileEntry("backend/src/config.py",              "Backend config"),
            FileEntry("backend/src/database.py",            "DB connection"),
            FileEntry("backend/src/api/auth.py",            "Auth API routes"),
            FileEntry("backend/src/api/users.py",           "Users API routes"),
            FileEntry("backend/src/api/subscriptions.py",   "Billing routes"),
            FileEntry("backend/src/models/user.py",         "User model"),
            FileEntry("backend/src/models/subscription.py", "Subscription model"),
            FileEntry("backend/src/services/auth.py",       "Auth service"),
            FileEntry("backend/src/services/email.py",      "Email service"),
            FileEntry("backend/src/middleware/auth.py",     "Auth middleware"),
            FileEntry("backend/src/schemas/user.py",        "User schemas"),
            FileEntry("backend/tests/conftest.py",          "Test fixtures"),
            FileEntry("backend/tests/test_auth.py",         "Auth tests"),
            FileEntry("backend/requirements.txt",           "Python deps"),
            FileEntry("backend/.env.example",               "Backend env"),
            # Root
            FileEntry("docker-compose.yml",                 "Full stack Docker"),
            FileEntry("Makefile",                           "Dev commands"),
            FileEntry(".github/workflows/ci.yml",           "CI/CD pipeline"),
            FileEntry(".gitignore",                         "Git ignore"),
            FileEntry("README.md",                          "Full documentation"),
        ],
    )


def _cli_template() -> StructureTemplate:
    return StructureTemplate(
        name    = "cli",
        folders = [
            "src", "src/commands", "src/utils",
            "tests", "docs",
        ],
        files = [
            FileEntry("src/__init__.py",         "Package init"),
            FileEntry("src/main.py",             "CLI entry point"),
            FileEntry("src/cli.py",              "Click app definition"),
            FileEntry("src/commands/__init__.py","Commands init"),
            FileEntry("src/commands/build.py",   "Build command"),
            FileEntry("src/commands/deploy.py",  "Deploy command"),
            FileEntry("src/utils/helpers.py",    "Utility functions"),
            FileEntry("src/utils/config.py",     "Config management"),
            FileEntry("tests/__init__.py",       "Tests init"),
            FileEntry("tests/test_cli.py",       "CLI tests"),
            FileEntry("setup.py",                "Package setup"),
            FileEntry("pyproject.toml",          "Project config"),
            FileEntry("requirements.txt",        "Dependencies"),
            FileEntry(".env.example",            "Environment template"),
            FileEntry(".gitignore",              "Git ignore"),
            FileEntry("README.md",               "Documentation"),
            FileEntry("Makefile",                "Dev shortcuts"),
        ],
    )


TEMPLATES: Dict[str, StructureTemplate] = {
    "web":     _web_template(),
    "api":     _api_template(),
    "saas":    _saas_template(),
    "cli":     _cli_template(),
}

# For unknown types, use API template as default
DEFAULT_TEMPLATE = _api_template()


# ── STRUCTURE GENERATOR ───────────────────────────────────
class StructureGenerator:
    """
    Generates project folder/file structures based on ProjectSpec.

    1. Selects appropriate template based on project type
    2. Customizes template based on stack, features, auth needs
    3. Creates all directories and placeholder files
    4. Returns file tree for display
    """

    def __init__(self):
        self._templates = TEMPLATES
        logger.info(
            f"StructureGenerator ready. "
            f"Templates: {list(self._templates.keys())}"
        )

    # ── GET TEMPLATE ──────────────────────────────────────
    def get_template(self, project_type: str) -> StructureTemplate:
        """Get the best template for a project type."""
        # Direct match
        if project_type in self._templates:
            return self._templates[project_type]

        # Fuzzy match
        for key in self._templates:
            if key in project_type or project_type in key:
                return self._templates[key]

        logger.warning(
            f"No template for type '{project_type}'. Using default."
        )
        return DEFAULT_TEMPLATE

    # ── CUSTOMIZE TEMPLATE ────────────────────────────────
    def customize_template(
        self,
        template: StructureTemplate,
        spec:     ProjectSpec,
    ) -> StructureTemplate:
        """Add/remove files based on spec details."""
        import copy
        custom = copy.deepcopy(template)

        # Add auth files if needed
        if spec.auth_required:
            auth_files = [
                FileEntry("src/auth/__init__.py",   "Auth module"),
                FileEntry("src/auth/jwt.py",        "JWT handling"),
                FileEntry("src/auth/models.py",     "Auth models"),
                FileEntry("src/auth/routes.py",     "Auth routes"),
                FileEntry("src/auth/schemas.py",    "Auth schemas"),
            ]
            existing_paths = {f.path for f in custom.files}
            for af in auth_files:
                if af.path not in existing_paths:
                    custom.files.append(af)
            if "src/auth" not in custom.folders:
                custom.folders.append("src/auth")

        # Add database files if needed
        if spec.database and spec.database.lower() != "none":
            db_files = [
                FileEntry("src/database.py",        "Database connection"),
                FileEntry("src/migrations/__init__.py", "Migrations"),
                FileEntry("alembic.ini",            "Alembic config"),
            ]
            existing_paths = {f.path for f in custom.files}
            for df in db_files:
                if df.path not in existing_paths:
                    custom.files.append(df)
            if "src/migrations" not in custom.folders:
                custom.folders.append("src/migrations")

        # Add GitHub Actions if GitHub push requested
        if spec.github_push:
            gh_files = [
                FileEntry(".github/workflows/build.yml",   "Build workflow"),
                FileEntry(".github/workflows/deploy.yml",  "Deploy workflow"),
            ]
            existing_paths = {f.path for f in custom.files}
            for gf in gh_files:
                if gf.path not in existing_paths:
                    custom.files.append(gf)
            for folder in [".github", ".github/workflows"]:
                if folder not in custom.folders:
                    custom.folders.append(folder)

        # Add Docker files
        existing_paths = {f.path for f in custom.files}
        if "Dockerfile" not in existing_paths:
            custom.files.append(FileEntry("Dockerfile", "Docker build"))
        if "docker-compose.yml" not in existing_paths:
            custom.files.append(FileEntry("docker-compose.yml", "Docker compose"))

        return custom

    # ── CREATE STRUCTURE ──────────────────────────────────
    def create(
        self,
        spec:      ProjectSpec,
        workspace: Path,
    ) -> Tuple[List[Path], List[Path]]:
        """
        Create the project directory structure.
        Returns (created_dirs, created_files).
        """
        template = self.get_template(spec.type)
        template = self.customize_template(template, spec)

        created_dirs:  List[Path] = []
        created_files: List[Path] = []

        # Create folders
        for folder in template.folders:
            dir_path = workspace / folder
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(dir_path)
            except Exception as e:
                logger.warning(f"Could not create dir {folder}: {e}")

        # Create placeholder files
        for file_entry in template.files:
            file_path = workspace / file_entry.path
            if file_path.exists():
                continue

            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                if file_entry.content:
                    file_path.write_text(file_entry.content, encoding="utf-8")
                else:
                    file_path.write_text(
                        f"# {file_entry.description}\n"
                        f"# Generated by ShadowForge OS\n",
                        encoding="utf-8",
                    )
                created_files.append(file_path)
            except Exception as e:
                logger.warning(f"Could not create file {file_entry.path}: {e}")

        logger.info(
            f"Structure created: "
            f"{len(created_dirs)} dirs, {len(created_files)} files"
        )

        return created_dirs, created_files

    # ── GENERATE TREE STRING ──────────────────────────────
    def generate_tree(
        self,
        workspace: Path,
        max_depth: int = 4,
        prefix:    str = "",
    ) -> str:
        """
        Generate a visual file tree string for display.
        Like the 'tree' command output.
        """
        lines = [workspace.name + "/"]

        def _tree(path: Path, depth: int, pre: str) -> None:
            if depth > max_depth:
                return
            try:
                items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
            except PermissionError:
                return

            for i, item in enumerate(items):
                # Skip hidden files except .github, .env
                if item.name.startswith(".") and item.name not in (
                    ".github", ".gitignore", ".env.example"
                ):
                    continue

                is_last   = (i == len(items) - 1)
                connector = "└── " if is_last else "├── "
                extension = "    " if is_last else "│   "

                lines.append(f"{pre}{connector}{item.name}")

                if item.is_dir() and depth < max_depth:
                    _tree(item, depth + 1, pre + extension)

        _tree(workspace, 1, prefix)
        return "\n".join(lines)

    # ── TO JSON ───────────────────────────────────────────
    def to_json(self, spec: ProjectSpec) -> Dict[str, Any]:
        """Export structure as JSON for API responses."""
        template = self.get_template(spec.type)
        template = self.customize_template(template, spec)

        return {
            "type":    spec.type,
            "folders": template.folders,
            "files":   [
                {"path": f.path, "description": f.description}
                for f in template.files
            ],
        }
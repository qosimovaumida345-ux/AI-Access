# ============================================================
# SHADOWFORGE OS — REPOSITORY MANAGER
# High-level repository operations: setup, push, gitignore,
# README generation, branch strategy, secrets injection.
# ============================================================

import re
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import get_logger
from core.constants import APP_NAME, APP_VERSION, WORKSPACE_DIR
from github.github_api import GitHubAPI, RepoInfo, GitHubError
from github.workflow_generator import WorkflowGenerator

logger = get_logger("GitHub.RepoManager")


# ── PROJECT REPO CONFIG ───────────────────────────────────
@dataclass
class ProjectRepoConfig:
    name:           str
    description:    str
    private:        bool = False
    topics:         List[str] = field(default_factory=list)
    platforms:      List[str] = field(
        default_factory=lambda: ["windows", "macos", "linux"]
    )
    python_version: str = "3.11"
    entry_script:   str = "app/core/main.py"
    license_type:   str = "MIT"
    has_landing:    bool = True
    deploy_target:  str = "github-pages"
    branch:         str = "main"


@dataclass
class RepoSetupResult:
    success:       bool
    repo:          Optional[RepoInfo]
    url:           str = ""
    files_pushed:  int = 0
    workflows:     List[str] = field(default_factory=list)
    errors:        List[str] = field(default_factory=list)
    duration:      float = 0.0


# ── REPO MANAGER ─────────────────────────────────────────
class RepoManager:
    """
    Orchestrates complete repository setup for ShadowForge projects.
    """

    GITIGNORE_PYTHON = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg
*.egg-info/
dist/
build/
eggs/
parts/
var/
sdist/
develop-eggs/
.installed.cfg
lib/
lib64/
.eggs/
.pytest_cache/
.mypy_cache/
.coverage
coverage.xml
htmlcov/
.tox/
.nox/
.hypothesis/
*.prof

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# ShadowForge secrets — NEVER COMMIT
app/.env
.env.local
.env.*.local
secrets.json
*.pem
*.key
*.p12

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db
desktop.ini

# PyInstaller
*.spec
dist/
build/

# Logs
*.log
logs/

# Temp
temp/
tmp/
*.tmp

# Node (for any web components)
node_modules/
.npm

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""

    def __init__(self, config):
        self.config = config
        github_cfg  = config.get_github_config()

        token    = github_cfg.get("token", "")
        username = github_cfg.get("username", "")

        if not token or not username:
            logger.warning(
                "GitHub token/username not configured. "
                "Repo operations will be disabled."
            )
            self._api = None
        else:
            self._api = GitHubAPI(token=token, username=username)

        logger.info("RepoManager initialized.")

    @property
    def is_configured(self) -> bool:
        return self._api is not None

    # ── FULL PROJECT SETUP ────────────────────────────────
    def setup_project_repo(
        self,
        project_config: ProjectRepoConfig,
        local_dir:      Path,
        on_progress:    Optional[Any] = None,
    ) -> RepoSetupResult:
        """
        Complete repo setup for a generated project:
        1. Create repo
        2. Add .gitignore
        3. Generate README
        4. Add GitHub Actions workflows
        5. Push all project files
        6. Set up branch protection
        """
        if not self.is_configured:
            return RepoSetupResult(
                success=False,
                repo=None,
                errors=["GitHub not configured. Add GITHUB_TOKEN to .env"],
            )

        start_time = time.perf_counter()
        errors: List[str] = []
        workflow_files: List[str] = []

        def progress(step: str, pct: int = 0) -> None:
            logger.info(f"[{pct:3d}%] {step}")
            if on_progress:
                try:
                    on_progress(step, pct)
                except Exception:
                    pass

        try:
            progress("Creating GitHub repository...", 5)

            # ── 1. Create repo ────────────────────────────
            topics = project_config.topics + [
                "shadowforge", "ai-generated",
                project_config.name.lower().replace(" ", "-"),
            ]
            topics = list(set(topics))[:20]

            repo = self._api.create_repo(
                name        = project_config.name,
                description = project_config.description[:350],
                private     = project_config.private,
                topics      = topics,
                auto_init   = True,
            )

            progress("Repository created.", 15)
            time.sleep(2)  # GitHub init delay

            # ── 2. Add .gitignore ─────────────────────────
            progress("Writing .gitignore...", 20)
            self._api.push_file(
                repo_name = repo.name,
                file_path = ".gitignore",
                content   = self.GITIGNORE_PYTHON,
                message   = "Add .gitignore",
                branch    = project_config.branch,
            )

            # ── 3. Generate README ────────────────────────
            progress("Generating README.md...", 25)
            readme = self._generate_readme(project_config, repo)
            self._api.push_file(
                repo_name = repo.name,
                file_path = "README.md",
                content   = readme,
                message   = "Add README.md",
                branch    = project_config.branch,
            )

            # ── 4. Add .env.example ───────────────────────
            progress("Writing .env.example...", 30)
            env_example = self._generate_env_example()
            self._api.push_file(
                repo_name = repo.name,
                file_path = "app/.env.example",
                content   = env_example,
                message   = "Add .env.example",
                branch    = project_config.branch,
            )

            # ── 5. Generate GitHub Actions workflows ──────
            progress("Generating GitHub Actions workflows...", 35)
            workflows_dir = local_dir / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)

            wf_gen = WorkflowGenerator(
                app_name    = project_config.name,
                app_version = self.config.get_app_settings().get(
                    "version", APP_VERSION
                ),
            )

            wf_results = wf_gen.write_all_workflows(
                output_dir = workflows_dir,
                platforms  = project_config.platforms,
            )

            for wf_name, ok in wf_results.items():
                if ok:
                    workflow_files.append(wf_name)
                else:
                    errors.append(f"Workflow generation failed: {wf_name}")

            # Push workflows
            progress("Pushing GitHub Actions workflows...", 45)
            for wf_file in workflows_dir.glob("*.yml"):
                content = wf_file.read_text(encoding="utf-8")
                self._api.push_file(
                    repo_name = repo.name,
                    file_path = f".github/workflows/{wf_file.name}",
                    content   = content,
                    message   = f"Add workflow: {wf_file.name}",
                    branch    = project_config.branch,
                )

            # ── 6. Push project files ─────────────────────
            progress("Pushing project files...", 55)

            if local_dir.exists():
                success_count, fail_count = self._api.push_directory(
                    repo_name  = repo.name,
                    local_dir  = local_dir,
                    branch     = project_config.branch,
                    commit_msg = (
                        f"feat: Initial project — {project_config.name}\n\n"
                        f"Generated by {APP_NAME} v{APP_VERSION}"
                    ),
                )
                if fail_count > 0:
                    errors.append(f"{fail_count} files failed to push")
            else:
                success_count = 0
                errors.append(f"Local directory not found: {local_dir}")

            progress("Finalizing...", 90)

            # ── 7. Set up secrets hint ────────────────────
            logger.info(
                f"\n{'='*50}\n"
                f"IMPORTANT: Add these secrets to your GitHub repo:\n"
                f"  Settings → Secrets → Actions → New repository secret\n"
                f"\n"
                f"  OPENROUTER_API_KEY=your_key\n"
                f"  GROQ_API_KEY=your_key\n"
                f"  GOOGLE_AI_API_KEY=your_key\n"
                f"  FORGE_GITHUB_TOKEN=your_token\n"
                f"  GITHUB_USERNAME=your_username\n"
                f"\n"
                f"  After adding secrets, push a tag to trigger builds:\n"
                f"  git tag v1.0.0 && git push origin v1.0.0\n"
                f"{'='*50}"
            )

            progress("Done!", 100)

            duration = time.perf_counter() - start_time

            return RepoSetupResult(
                success      = True,
                repo         = repo,
                url          = repo.url,
                files_pushed = success_count,
                workflows    = workflow_files,
                errors       = errors,
                duration     = duration,
            )

        except GitHubError as e:
            logger.error(f"GitHub error during repo setup: {e}")
            return RepoSetupResult(
                success  = False,
                repo     = None,
                errors   = [str(e)],
                duration = time.perf_counter() - start_time,
            )
        except Exception as e:
            logger.error(f"Unexpected error during repo setup: {e}", exc_info=True)
            return RepoSetupResult(
                success  = False,
                repo     = None,
                errors   = [str(e)],
                duration = time.perf_counter() - start_time,
            )

    # ── README GENERATOR ──────────────────────────────────
    def _generate_readme(
        self,
        cfg:  ProjectRepoConfig,
        repo: RepoInfo,
    ) -> str:
        """Generate a comprehensive README.md."""

        platform_badges = " ".join([
            f"![{p.capitalize()}](https://img.shields.io/badge/{p.capitalize()}-supported-"
            f"{'blue' if p != 'android' else 'green'}.svg)"
            for p in cfg.platforms
        ])

        install_section = (
            "```bash\n"
            "# 1. Clone the repository\n"
            f"git clone {repo.clone_url}\n"
            f"cd {repo.name}\n"
            "\n"
            "# 2. Install dependencies\n"
            "pip install -r requirements.txt\n"
            "\n"
            "# 3. Configure API keys\n"
            "cp app/.env.example app/.env\n"
            "# Edit app/.env and add your API keys\n"
            "\n"
            "# 4. Run the app\n"
            f"python {cfg.entry_script}\n"
            "```"
        )

        workflow_section = "\n".join([
            f"- `{wf}` — automated CI/CD"
            for wf in ["build.yml", "release.yml", "test.yml"]
        ])

        readme = (
            f"# {cfg.name}\n\n"
            f"> {cfg.description}\n\n"
            f"{platform_badges}\n"
            f"![Built with ShadowForge](https://img.shields.io/badge/Built%20with-ShadowForge%20OS-purple.svg)\n"
            f"![Python](https://img.shields.io/badge/Python-{cfg.python_version}-blue.svg)\n"
            f"![License](https://img.shields.io/badge/License-{cfg.license_type}-green.svg)\n\n"
            f"## ⚡ Quick Start\n\n"
            f"### Prerequisites\n"
            f"- Python {cfg.python_version}+\n"
            f"- At least one AI provider API key\n\n"
            f"### Installation\n\n"
            f"{install_section}\n\n"
            f"## 🔑 API Keys\n\n"
            f"Copy `app/.env.example` to `app/.env` and fill in your keys:\n\n"
            f"| Variable | Provider | Required |\n"
            f"|----------|----------|----------|\n"
            f"| `OPENROUTER_API_KEY` | OpenRouter | Recommended |\n"
            f"| `GROQ_API_KEY` | Groq | Optional |\n"
            f"| `GOOGLE_AI_API_KEY` | Google Gemini | Optional |\n"
            f"| `OPENAI_API_KEY` | OpenAI | Optional |\n\n"
            f"## 🤖 Features\n\n"
            f"- **Multi-Provider AI** — OpenRouter, Groq, Google Gemini, OpenAI\n"
            f"- **Auto-Installer** — missing packages installed automatically\n"
            f"- **Cross-Platform** — {', '.join(p.capitalize() for p in cfg.platforms)}\n"
            f"- **GitHub Integration** — automated workflows, releases\n"
            f"- **ShadowForge Engine** — AI-powered project generation\n\n"
            f"## 📦 GitHub Actions Workflows\n\n"
            f"{workflow_section}\n\n"
            f"## 🏗️ Project Structure\n\n"
            f"```\n"
            f"{cfg.name}/\n"
            f"├── app/\n"
            f"│   ├── core/          # Core engine\n"
            f"│   ├── agent/         # AI agents\n"
            f"│   ├── github/        # GitHub integration\n"
            f"│   ├── ui/            # User interface\n"
            f"│   └── .env           # Your API keys (never commit!)\n"
            f"├── .github/\n"
            f"│   └── workflows/     # CI/CD pipelines\n"
            f"├── requirements.txt\n"
            f"└── README.md\n"
            f"```\n\n"
            f"## 📄 License\n\n"
            f"[{cfg.license_type}](LICENSE) © {datetime.now().year} — Built with "
            f"[ShadowForge OS](https://github.com/shadowforge)\n\n"
            f"---\n\n"
            f"*Generated by {APP_NAME} v{APP_VERSION} on "
            f"{datetime.now().strftime('%Y-%m-%d')}*\n"
        )

        return readme

    # ── ENV EXAMPLE GENERATOR ─────────────────────────────
    def _generate_env_example(self) -> str:
        """Generate a .env.example file with all supported keys."""
        return (
            "# ============================================================\n"
            "# ShadowForge OS — Environment Configuration\n"
            "# Copy this file to app/.env and fill in your values.\n"
            "# NEVER commit app/.env to version control!\n"
            "# ============================================================\n\n"
            "# ── AI PROVIDERS ─────────────────────────────────────────────\n"
            "# OpenRouter (recommended — access to 100+ models)\n"
            "OPENROUTER_API_KEY=your_openrouter_key_here\n\n"
            "# Groq (ultra-fast inference)\n"
            "GROQ_API_KEY=your_groq_key_here\n\n"
            "# Google Gemini\n"
            "GOOGLE_AI_API_KEY=your_google_ai_key_here\n\n"
            "# OpenAI\n"
            "OPENAI_API_KEY=your_openai_key_here\n\n"
            "# ── GITHUB ───────────────────────────────────────────────────\n"
            "FORGE_GITHUB_TOKEN=your_github_personal_access_token\n"
            "GITHUB_USERNAME=your_github_username\n\n"
            "# ── APP SETTINGS ─────────────────────────────────────────────\n"
            "DEBUG=false\n"
            "LOG_LEVEL=INFO\n"
            "WORKSPACE_DIR=workspace\n"
        )

    # ── QUICK HELPERS ─────────────────────────────────────
    def list_repos(self, limit: int = 30) -> List[RepoInfo]:
        """Return a list of the user's repositories."""
        if not self.is_configured:
            logger.warning("GitHub not configured.")
            return []
        try:
            return self._api.list_repos(limit=limit)
        except GitHubError as e:
            logger.error(f"Failed to list repos: {e}")
            return []

    def delete_repo(self, repo_name: str) -> bool:
        """Delete a repository (use with caution!)."""
        if not self.is_configured:
            logger.warning("GitHub not configured.")
            return False
        try:
            return self._api.delete_repo(repo_name)
        except GitHubError as e:
            logger.error(f"Failed to delete repo '{repo_name}': {e}")
            return False

    def get_repo(self, repo_name: str) -> Optional[RepoInfo]:
        """Fetch info for a single repository."""
        if not self.is_configured:
            return None
        try:
            return self._api.get_repo(repo_name)
        except GitHubError as e:
            logger.error(f"Failed to get repo '{repo_name}': {e}")
            return None

    def push_file(
        self,
        repo_name: str,
        file_path: str,
        content:   str,
        message:   str = "Update file",
        branch:    str = "main",
    ) -> bool:
        """Push a single file to a repository."""
        if not self.is_configured:
            return False
        try:
            self._api.push_file(
                repo_name = repo_name,
                file_path = file_path,
                content   = content,
                message   = message,
                branch    = branch,
            )
            return True
        except GitHubError as e:
            logger.error(f"Failed to push file '{file_path}': {e}")
            return False

# ============================================================
# SHADOWFORGE OS — GITHUB API CLIENT
# Full GitHub REST API wrapper. Creates repos, pushes code,
# manages releases, triggers workflows, handles auth.
# Uses PyGithub + direct REST calls for full control.
# ============================================================

import os
import re
import json
import time
import base64
import logging
import threading
import mimetypes
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple, Generator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.logger import get_logger
from core.constants import APP_NAME, APP_VERSION

logger = get_logger("GitHub.API")


# ── DATA CLASSES ──────────────────────────────────────────
@dataclass
class RepoInfo:
    name:           str
    full_name:      str
    description:    str
    url:            str
    clone_url:      str
    ssh_url:        str
    default_branch: str
    private:        bool
    created_at:     str
    topics:         List[str] = field(default_factory=list)
    has_actions:    bool = False


@dataclass
class ReleaseInfo:
    id:          int
    tag_name:    str
    name:        str
    body:        str
    draft:       bool
    prerelease:  bool
    url:         str
    upload_url:  str
    assets:      List[Dict] = field(default_factory=list)
    created_at:  str = ""


@dataclass
class CommitInfo:
    sha:       str
    message:   str
    author:    str
    timestamp: str
    url:       str


@dataclass
class WorkflowRun:
    id:         int
    name:       str
    status:     str
    conclusion: Optional[str]
    url:        str
    created_at: str


class GitHubError(Exception):
    """GitHub API error with status code."""
    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        super().__init__(f"GitHub API Error [{status_code}]: {message}")


# ── RATE LIMIT TRACKER ────────────────────────────────────
@dataclass
class RateLimitState:
    remaining:   int = 5000
    limit:       int = 5000
    reset_time:  float = 0.0
    last_check:  float = 0.0

    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= 5

    @property
    def seconds_until_reset(self) -> float:
        now = time.time()
        return max(0, self.reset_time - now)

    @property
    def percent_used(self) -> float:
        if self.limit == 0:
            return 0.0
        return (1 - self.remaining / self.limit) * 100


# ── GITHUB API CLIENT ─────────────────────────────────────
class GitHubAPI:
    """
    Full-featured GitHub REST API v3 client.

    Features:
    - Repository CRUD
    - File push (single + bulk)
    - Releases & asset upload
    - GitHub Actions trigger & monitor
    - Branch management
    - Rate limit awareness
    - Retry logic
    - Progress callbacks
    """

    BASE_URL    = "https://api.github.com"
    UPLOAD_URL  = "https://uploads.github.com"
    API_VERSION = "2022-11-28"

    MAX_FILE_SIZE_MB  = 50    # GitHub file size limit
    BULK_COMMIT_LIMIT = 100   # Max files per commit via Tree API

    def __init__(
        self,
        token:    str,
        username: str,
        progress_callback: Optional[Any] = None,
    ):
        self.token    = token
        self.username = username
        self._progress_cb = progress_callback
        self._rate_limit  = RateLimitState()
        self._lock        = threading.Lock()

        # Build session with retry logic
        self._session = self._build_session()

        # Verify token on init
        self._verify_auth()

        logger.info(f"GitHubAPI initialized for user: {username}")

    # ── SESSION SETUP ─────────────────────────────────────
    def _build_session(self) -> requests.Session:
        session = requests.Session()

        # Headers
        session.headers.update({
            "Authorization":        f"Bearer {self.token}",
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
            "User-Agent":           f"{APP_NAME}/{APP_VERSION}",
        })

        # Retry strategy
        retry = Retry(
            total             = 4,
            backoff_factor    = 1.5,
            status_forcelist  = [429, 500, 502, 503, 504],
            allowed_methods   = ["GET", "POST", "PUT", "PATCH", "DELETE"],
            raise_on_status   = False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    # ── AUTH VERIFY ───────────────────────────────────────
    def _verify_auth(self) -> None:
        """Verify GitHub token is valid."""
        try:
            resp = self._get("/user")
            actual_login = resp.get("login", "")
            if actual_login.lower() != self.username.lower():
                logger.warning(
                    f"Token username mismatch: "
                    f"config='{self.username}' actual='{actual_login}'. "
                    f"Using actual: '{actual_login}'"
                )
                self.username = actual_login
            logger.info(f"GitHub auth verified: {actual_login}")
        except GitHubError as e:
            logger.error(f"GitHub auth failed: {e}")
            raise

    # ── REQUEST HELPERS ───────────────────────────────────
    def _request(
        self,
        method:   str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make an authenticated GitHub API request."""

        # Rate limit check
        if self._rate_limit.is_exhausted:
            wait = self._rate_limit.seconds_until_reset + 1
            logger.warning(f"Rate limit exhausted. Waiting {wait:.0f}s...")
            time.sleep(wait)

        url = (
            endpoint if endpoint.startswith("https://")
            else f"{self.BASE_URL}{endpoint}"
        )

        try:
            resp = self._session.request(
                method  = method.upper(),
                url     = url,
                timeout = 30,
                **kwargs,
            )

            # Update rate limit from headers
            self._update_rate_limit(resp.headers)

            # Handle response
            if resp.status_code == 204:
                return {}  # No content

            if resp.status_code == 404:
                raise GitHubError("Resource not found", 404)

            if resp.status_code == 401:
                raise GitHubError("Invalid or expired token", 401)

            if resp.status_code == 403:
                body = resp.json() if resp.content else {}
                msg  = body.get("message", "Forbidden")
                if "rate limit" in msg.lower():
                    wait = self._rate_limit.seconds_until_reset + 1
                    logger.warning(f"Rate limited. Waiting {wait:.0f}s...")
                    time.sleep(wait)
                    return self._request(method, endpoint, **kwargs)
                raise GitHubError(msg, 403)

            if resp.status_code == 422:
                body = resp.json() if resp.content else {}
                raise GitHubError(
                    body.get("message", "Unprocessable entity"), 422
                )

            if resp.status_code >= 400:
                try:
                    body = resp.json()
                    msg  = body.get("message", f"HTTP {resp.status_code}")
                except Exception:
                    msg = f"HTTP {resp.status_code}"
                raise GitHubError(msg, resp.status_code)

            if resp.content:
                return resp.json()
            return {}

        except requests.exceptions.Timeout:
            raise GitHubError("Request timed out", 408)
        except requests.exceptions.ConnectionError as e:
            raise GitHubError(f"Connection error: {str(e)[:100]}", 0)

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        return self._request("GET", endpoint, params=params)

    def _post(self, endpoint: str, data: Dict) -> Any:
        return self._request("POST", endpoint, json=data)

    def _put(self, endpoint: str, data: Dict) -> Any:
        return self._request("PUT", endpoint, json=data)

    def _patch(self, endpoint: str, data: Dict) -> Any:
        return self._request("PATCH", endpoint, json=data)

    def _delete(self, endpoint: str) -> Any:
        return self._request("DELETE", endpoint)

    def _update_rate_limit(self, headers: Dict) -> None:
        """Parse rate limit headers."""
        try:
            with self._lock:
                if "X-RateLimit-Remaining" in headers:
                    self._rate_limit.remaining = int(
                        headers["X-RateLimit-Remaining"]
                    )
                if "X-RateLimit-Limit" in headers:
                    self._rate_limit.limit = int(headers["X-RateLimit-Limit"])
                if "X-RateLimit-Reset" in headers:
                    self._rate_limit.reset_time = float(
                        headers["X-RateLimit-Reset"]
                    )
                self._rate_limit.last_check = time.time()
        except Exception:
            pass

    # ── REPOSITORY OPERATIONS ────────────────────────────
    def repo_exists(self, repo_name: str) -> bool:
        """Check if a repository exists."""
        try:
            self._get(f"/repos/{self.username}/{repo_name}")
            return True
        except GitHubError as e:
            if e.status_code == 404:
                return False
            raise

    def create_repo(
        self,
        name:        str,
        description: str  = "",
        private:     bool = False,
        topics:      Optional[List[str]] = None,
        auto_init:   bool = True,
    ) -> RepoInfo:
        """Create a new GitHub repository."""
        # Sanitize name
        safe_name = re.sub(r'[^\w\-.]', '-', name.strip()).strip('-')

        if self.repo_exists(safe_name):
            logger.info(f"Repo already exists: {safe_name}")
            return self.get_repo(safe_name)

        payload: Dict[str, Any] = {
            "name":          safe_name,
            "description":   description[:350] if description else f"{APP_NAME} project",
            "private":       private,
            "auto_init":     auto_init,
            "has_issues":    True,
            "has_wiki":      False,
            "has_projects":  False,
        }

        logger.info(f"Creating repo: {safe_name} (private={private})")
        data = self._post("/user/repos", payload)

        info = RepoInfo(
            name           = data["name"],
            full_name      = data["full_name"],
            description    = data.get("description", ""),
            url            = data["html_url"],
            clone_url      = data["clone_url"],
            ssh_url        = data["ssh_url"],
            default_branch = data.get("default_branch", "main"),
            private        = data["private"],
            created_at     = data.get("created_at", ""),
        )

        # Add topics
        if topics:
            self.set_repo_topics(safe_name, topics)
            info.topics = topics

        logger.info(f"Repo created: {info.url}")
        return info

    def get_repo(self, repo_name: str) -> RepoInfo:
        """Get repository info."""
        data = self._get(f"/repos/{self.username}/{repo_name}")
        return RepoInfo(
            name           = data["name"],
            full_name      = data["full_name"],
            description    = data.get("description", ""),
            url            = data["html_url"],
            clone_url      = data["clone_url"],
            ssh_url        = data["ssh_url"],
            default_branch = data.get("default_branch", "main"),
            private        = data["private"],
            created_at     = data.get("created_at", ""),
        )

    def delete_repo(self, repo_name: str) -> bool:
        """Delete a repository. IRREVERSIBLE."""
        try:
            self._delete(f"/repos/{self.username}/{repo_name}")
            logger.warning(f"Repo deleted: {repo_name}")
            return True
        except GitHubError:
            return False

    def set_repo_topics(self, repo_name: str, topics: List[str]) -> bool:
        """Set repository topics/tags."""
        try:
            clean_topics = [
                re.sub(r'[^a-z0-9\-]', '-', t.lower())[:50]
                for t in topics[:20]
            ]
            self._put(
                f"/repos/{self.username}/{repo_name}/topics",
                {"names": clean_topics},
            )
            return True
        except GitHubError as e:
            logger.warning(f"Set topics failed: {e}")
            return False

    def update_repo(
        self,
        repo_name:   str,
        description: Optional[str] = None,
        homepage:    Optional[str] = None,
        private:     Optional[bool] = None,
    ) -> bool:
        """Update repository metadata."""
        payload: Dict[str, Any] = {}
        if description is not None: payload["description"] = description
        if homepage    is not None: payload["homepage"]    = homepage
        if private     is not None: payload["private"]     = private

        if not payload:
            return True

        try:
            self._patch(f"/repos/{self.username}/{repo_name}", payload)
            return True
        except GitHubError as e:
            logger.error(f"Update repo failed: {e}")
            return False

    # ── FILE OPERATIONS ───────────────────────────────────
    def get_file_sha(
        self, repo_name: str, file_path: str, branch: str = "main"
    ) -> Optional[str]:
        """Get SHA of existing file (needed for updates)."""
        try:
            data = self._get(
                f"/repos/{self.username}/{repo_name}/contents/{file_path}",
                params={"ref": branch},
            )
            return data.get("sha")
        except GitHubError:
            return None

    def push_file(
        self,
        repo_name:  str,
        file_path:  str,
        content:    str,
        message:    str    = "Update via ShadowForge",
        branch:     str    = "main",
        encoding:   str    = "utf-8",
    ) -> bool:
        """
        Push a single file to GitHub repository.
        Creates or updates the file.
        """
        # Encode content to base64
        try:
            content_bytes  = content.encode(encoding)
            content_b64    = base64.b64encode(content_bytes).decode("ascii")
        except Exception as e:
            logger.error(f"Encoding error for {file_path}: {e}")
            return False

        # Check file size
        if len(content_bytes) > self.MAX_FILE_SIZE_MB * 1024 * 1024:
            logger.warning(
                f"File too large for GitHub API: {file_path} "
                f"({len(content_bytes)/1024/1024:.1f}MB)"
            )
            return False

        payload: Dict[str, Any] = {
            "message": message,
            "content": content_b64,
            "branch":  branch,
        }

        # Get existing SHA if file exists (required for updates)
        existing_sha = self.get_file_sha(repo_name, file_path, branch)
        if existing_sha:
            payload["sha"] = existing_sha

        try:
            self._put(
                f"/repos/{self.username}/{repo_name}/contents/{file_path}",
                payload,
            )
            logger.debug(f"File pushed: {file_path}")
            return True
        except GitHubError as e:
            logger.error(f"Push file failed ({file_path}): {e}")
            return False

    def push_directory(
        self,
        repo_name:  str,
        local_dir:  Path,
        branch:     str  = "main",
        commit_msg: str  = "ShadowForge: Initial commit",
        exclude_patterns: Optional[List[str]] = None,
    ) -> Tuple[int, int]:
        """
        Push entire directory to GitHub using Tree API.
        Much faster than pushing file by file.
        Returns (success_count, fail_count).
        """
        local_dir = Path(local_dir)
        if not local_dir.exists():
            raise GitHubError(f"Local directory not found: {local_dir}", 0)

        exclude_patterns = exclude_patterns or [
            "__pycache__", ".git", ".env", "*.pyc",
            "*.pyo", "node_modules", ".DS_Store",
            "*.egg-info", "dist/", "build/",
            "*.log", "temp/", ".pytest_cache/",
        ]

        # Collect all files
        files_to_push: List[Tuple[str, str]] = []  # (github_path, local_path)

        for file_path in local_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Check exclusions
            rel_path = file_path.relative_to(local_dir)
            skip = False

            for pattern in exclude_patterns:
                pattern_clean = pattern.rstrip("/")
                if (pattern_clean in str(rel_path) or
                    file_path.name == pattern_clean or
                    file_path.match(pattern)):
                    skip = True
                    break

            if skip:
                continue

            github_path = str(rel_path).replace("\\", "/")
            files_to_push.append((github_path, str(file_path)))

        logger.info(
            f"Pushing {len(files_to_push)} files to "
            f"{self.username}/{repo_name}..."
        )

        # Get current commit SHA
        try:
            ref_data = self._get(
                f"/repos/{self.username}/{repo_name}/git/ref/heads/{branch}"
            )
            base_tree_sha  = ref_data["object"]["sha"]
            base_commit    = self._get(
                f"/repos/{self.username}/{repo_name}/git/commits/{base_tree_sha}"
            )
            base_tree      = base_commit["tree"]["sha"]
        except GitHubError as e:
            logger.error(f"Could not get base commit: {e}")
            return 0, len(files_to_push)

        # Build tree objects (in chunks to avoid payload limits)
        success = 0
        fail    = 0
        chunk_size = 50  # Files per tree API call

        all_blobs: List[Dict] = []
        total = len(files_to_push)

        for i, (github_path, local_path) in enumerate(files_to_push):
            try:
                with open(local_path, "rb") as f:
                    raw = f.read()

                # Try UTF-8 text encoding, fall back to base64 binary
                try:
                    content_str = raw.decode("utf-8")
                    blob_payload = {
                        "content":  content_str,
                        "encoding": "utf-8",
                    }
                except UnicodeDecodeError:
                    content_b64 = base64.b64encode(raw).decode("ascii")
                    blob_payload = {
                        "content":  content_b64,
                        "encoding": "base64",
                    }

                blob = self._post(
                    f"/repos/{self.username}/{repo_name}/git/blobs",
                    blob_payload,
                )

                all_blobs.append({
                    "path": github_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha":  blob["sha"],
                })
                success += 1

                # Progress
                pct = int((i + 1) / total * 80)
                if self._progress_cb:
                    self._progress_cb("push_file", github_path, pct)

            except Exception as e:
                logger.warning(f"Failed to create blob for {github_path}: {e}")
                fail += 1

        if not all_blobs:
            logger.error("No blobs created. Nothing to commit.")
            return 0, fail

        # Create tree
        try:
            tree_data = self._post(
                f"/repos/{self.username}/{repo_name}/git/trees",
                {
                    "base_tree": base_tree,
                    "tree":      all_blobs,
                },
            )
        except GitHubError as e:
            logger.error(f"Tree creation failed: {e}")
            return success, fail + len(all_blobs)

        # Create commit
        try:
            commit_data = self._post(
                f"/repos/{self.username}/{repo_name}/git/commits",
                {
                    "message": commit_msg,
                    "tree":    tree_data["sha"],
                    "parents": [base_tree_sha],
                    "author": {
                        "name":  "ShadowForge OS",
                        "email": "shadowforge@users.noreply.github.com",
                        "date":  datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                },
            )
        except GitHubError as e:
            logger.error(f"Commit creation failed: {e}")
            return success, fail

        # Update branch reference
        try:
            self._patch(
                f"/repos/{self.username}/{repo_name}/git/refs/heads/{branch}",
                {
                    "sha":   commit_data["sha"],
                    "force": False,
                },
            )
        except GitHubError as e:
            logger.error(f"Branch update failed: {e}")
            return success, fail

        if self._progress_cb:
            self._progress_cb("push_complete", repo_name, 100)

        logger.info(
            f"Directory pushed: {success} files OK, {fail} failed. "
            f"Commit: {commit_data['sha'][:8]}"
        )
        return success, fail

    # ── BRANCH OPERATIONS ────────────────────────────────
    def create_branch(
        self, repo_name: str, branch_name: str, from_branch: str = "main"
    ) -> bool:
        """Create a new branch from existing branch."""
        try:
            ref_data = self._get(
                f"/repos/{self.username}/{repo_name}/git/ref/heads/{from_branch}"
            )
            sha = ref_data["object"]["sha"]

            self._post(
                f"/repos/{self.username}/{repo_name}/git/refs",
                {"ref": f"refs/heads/{branch_name}", "sha": sha},
            )
            logger.info(f"Branch created: {branch_name} from {from_branch}")
            return True
        except GitHubError as e:
            if e.status_code == 422:
                logger.info(f"Branch already exists: {branch_name}")
                return True
            logger.error(f"Create branch failed: {e}")
            return False

    def get_branches(self, repo_name: str) -> List[str]:
        """Get list of branch names."""
        try:
            data = self._get(f"/repos/{self.username}/{repo_name}/branches")
            return [b["name"] for b in data]
        except GitHubError:
            return []

    # ── RELEASE OPERATIONS ────────────────────────────────
    def create_release(
        self,
        repo_name:   str,
        tag:         str,
        name:        str,
        body:        str  = "",
        draft:       bool = False,
        prerelease:  bool = False,
        target:      str  = "main",
    ) -> ReleaseInfo:
        """Create a GitHub release."""
        data = self._post(
            f"/repos/{self.username}/{repo_name}/releases",
            {
                "tag_name":         tag,
                "target_commitish": target,
                "name":             name,
                "body":             body,
                "draft":            draft,
                "prerelease":       prerelease,
            },
        )

        info = ReleaseInfo(
            id         = data["id"],
            tag_name   = data["tag_name"],
            name       = data["name"],
            body       = data.get("body", ""),
            draft      = data["draft"],
            prerelease = data["prerelease"],
            url        = data["html_url"],
            upload_url = data["upload_url"].split("{")[0],  # Remove template part
            created_at = data.get("created_at", ""),
        )

        logger.info(f"Release created: {tag} — {info.url}")
        return info

    def upload_release_asset(
        self,
        release:    ReleaseInfo,
        file_path:  Path,
        asset_name: Optional[str] = None,
    ) -> bool:
        """Upload a file as a release asset."""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"Asset file not found: {file_path}")
            return False

        name         = asset_name or file_path.name
        content_type = (
            mimetypes.guess_type(str(file_path))[0] or
            "application/octet-stream"
        )
        file_size = file_path.stat().st_size

        logger.info(
            f"Uploading release asset: {name} "
            f"({file_size/1024/1024:.1f}MB)"
        )

        try:
            with open(file_path, "rb") as f:
                resp = self._session.post(
                    f"{release.upload_url}?name={name}&label={name}",
                    data    = f,
                    headers = {"Content-Type": content_type},
                    timeout = 300,  # 5 min for large files
                )

            if resp.status_code in (200, 201):
                logger.info(f"Asset uploaded: {name}")
                return True
            else:
                logger.error(
                    f"Asset upload failed: HTTP {resp.status_code}"
                )
                return False

        except Exception as e:
            logger.error(f"Asset upload error: {e}")
            return False

    def get_latest_release(self, repo_name: str) -> Optional[ReleaseInfo]:
        """Get the latest release."""
        try:
            data = self._get(
                f"/repos/{self.username}/{repo_name}/releases/latest"
            )
            return ReleaseInfo(
                id         = data["id"],
                tag_name   = data["tag_name"],
                name       = data["name"],
                body       = data.get("body", ""),
                draft      = data["draft"],
                prerelease = data["prerelease"],
                url        = data["html_url"],
                upload_url = data["upload_url"].split("{")[0],
                created_at = data.get("created_at", ""),
            )
        except GitHubError:
            return None

    # ── GITHUB ACTIONS ────────────────────────────────────
    def trigger_workflow(
        self,
        repo_name:     str,
        workflow_file: str,
        branch:        str = "main",
        inputs:        Optional[Dict] = None,
    ) -> bool:
        """Trigger a GitHub Actions workflow manually."""
        try:
            self._post(
                f"/repos/{self.username}/{repo_name}"
                f"/actions/workflows/{workflow_file}/dispatches",
                {
                    "ref":    branch,
                    "inputs": inputs or {},
                },
            )
            logger.info(f"Workflow triggered: {workflow_file}")
            return True
        except GitHubError as e:
            logger.error(f"Workflow trigger failed: {e}")
            return False

    def get_workflow_runs(
        self, repo_name: str, workflow_file: str, limit: int = 5
    ) -> List[WorkflowRun]:
        """Get recent workflow runs."""
        try:
            data = self._get(
                f"/repos/{self.username}/{repo_name}"
                f"/actions/workflows/{workflow_file}/runs",
                params={"per_page": limit},
            )
            runs = []
            for run in data.get("workflow_runs", []):
                runs.append(WorkflowRun(
                    id         = run["id"],
                    name       = run["name"],
                    status     = run["status"],
                    conclusion = run.get("conclusion"),
                    url        = run["html_url"],
                    created_at = run.get("created_at", ""),
                ))
            return runs
        except GitHubError:
            return []

    def wait_for_workflow(
        self,
        repo_name:     str,
        workflow_file: str,
        timeout_mins:  int = 30,
        poll_interval: int = 30,
        on_update:     Optional[Any] = None,
    ) -> Optional[str]:
        """
        Wait for a workflow to complete.
        Returns conclusion: 'success', 'failure', 'cancelled', or None (timeout).
        """
        start = time.time()
        timeout_secs = timeout_mins * 60

        logger.info(
            f"Waiting for workflow: {workflow_file} "
            f"(timeout: {timeout_mins}min)"
        )

        # Wait for run to appear
        time.sleep(10)

        while time.time() - start < timeout_secs:
            runs = self.get_workflow_runs(repo_name, workflow_file, limit=1)

            if runs:
                run = runs[0]
                elapsed = int(time.time() - start)
                status_msg = (
                    f"Workflow {run.status} "
                    f"(elapsed: {elapsed}s)"
                )
                logger.info(status_msg)

                if on_update:
                    on_update(run.status, elapsed)

                if run.status == "completed":
                    conclusion = run.conclusion or "unknown"
                    logger.info(f"Workflow concluded: {conclusion}")
                    return conclusion

            time.sleep(poll_interval)

        logger.warning(f"Workflow wait timed out after {timeout_mins}min")
        return None

    # ── SECRETS ───────────────────────────────────────────
    def set_repo_secret(
        self,
        repo_name:    str,
        secret_name:  str,
        secret_value: str,
    ) -> bool:
        """
        Set a GitHub Actions secret for a repository.
        Uses libsodium encryption (requires PyNaCl).
        """
        try:
            from nacl import encoding, public as nacl_public

            # Get repo public key
            key_data = self._get(
                f"/repos/{self.username}/{repo_name}/actions/secrets/public-key"
            )
            public_key_b64 = key_data["key"]
            key_id         = key_data["key_id"]

            # Encrypt secret
            public_key = nacl_public.PublicKey(
                public_key_b64.encode("utf-8"),
                encoding.Base64Encoder,
            )
            sealed_box     = nacl_public.SealedBox(public_key)
            encrypted       = sealed_box.encrypt(secret_value.encode("utf-8"))
            encrypted_b64  = base64.b64encode(encrypted).decode("utf-8")

            # Upload secret
            self._put(
                f"/repos/{self.username}/{repo_name}"
                f"/actions/secrets/{secret_name}",
                {
                    "encrypted_value": encrypted_b64,
                    "key_id":          key_id,
                },
            )
            logger.info(f"Secret set: {secret_name}")
            return True

        except ImportError:
            logger.warning(
                "PyNaCl not installed. Cannot set GitHub secrets. "
                "Run: pip install PyNaCl"
            )
            return False
        except GitHubError as e:
            logger.error(f"Set secret failed: {e}")
            return False

    # ── REPO SETUP (all-in-one) ───────────────────────────
    def setup_repo_for_project(
        self,
        project_name: str,
        description:  str,
        local_dir:    Path,
        private:      bool = False,
        topics:       Optional[List[str]] = None,
        commit_msg:   str = "Initial commit — ShadowForge OS",
    ) -> Optional[RepoInfo]:
        """
        Full repo setup: create → push files → return info.
        One call to set up everything.
        """
        try:
            # Create repo
            repo = self.create_repo(
                name        = project_name,
                description = description,
                private     = private,
                topics      = topics or ["shadowforge", "ai-generated"],
                auto_init   = True,
            )

            # Small delay for GitHub to initialize
            time.sleep(2)

            # Push all files
            success, fail = self.push_directory(
                repo_name  = repo.name,
                local_dir  = local_dir,
                commit_msg = commit_msg,
            )

            logger.info(
                f"Repo setup complete: {repo.url} "
                f"({success} files pushed, {fail} failed)"
            )

            return repo

        except GitHubError as e:
            logger.error(f"Repo setup failed: {e}")
            return None

    # ── RATE LIMIT INFO ───────────────────────────────────
    def get_rate_limit(self) -> RateLimitState:
        """Get current rate limit status."""
        try:
            data = self._get("/rate_limit")
            core = data.get("rate", {})
            with self._lock:
                self._rate_limit.remaining  = core.get("remaining", 0)
                self._rate_limit.limit      = core.get("limit", 5000)
                self._rate_limit.reset_time = core.get("reset", 0)
        except GitHubError:
            pass
        return self._rate_limit

    @property
    def rate_limit(self) -> RateLimitState:
        return self._rate_limit

    def __repr__(self) -> str:
        return (
            f"GitHubAPI(user={self.username}, "
            f"rate_limit={self._rate_limit.remaining}/{self._rate_limit.limit})"
        )
#!/usr/bin/env python3
"""Project & Workspace Context Manager for iTOPAZ Agent.

Registers the built-in iTOPAZ projects below and discovers any other
directories under ``clones/``.

Git state (branch, dirty flag, latest commit) is collected lazily and cached
for ``ITOPAZ_GIT_CACHE_TTL`` seconds (default 30). Importing this module runs
no git commands; state is fetched the first time a project's details are
requested, and ``list_projects`` refreshes projects in parallel.
"""

import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

REPO_ROOT = Path(os.environ.get("ITOPAZ_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent)).resolve()

GIT_CACHE_TTL = float(os.environ.get("ITOPAZ_GIT_CACHE_TTL", "30"))
GIT_TIMEOUT = 10
# Read-only queries: skip optional index refresh locks and never prompt for credentials.
_GIT_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
_KEY_FILE_CHECKS = (
    "Jenkinsfile",
    "Dockerfile",
    "package.json",
    "pom.xml",
    "requirements.txt",
    "appsettings.json",
    "docker-compose.yml",
)


def _git(path: Path, *args: str) -> Optional[str]:
    """Run a read-only git command; return stdout, or None on any failure."""
    try:
        res = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            env=_GIT_ENV,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout if res.returncode == 0 else None


@dataclass
class ProjectInfo:
    id: str
    name: str
    path: Path
    category: str  # k8s-infra, backend, frontend, devops, integration
    tech_stack: str
    description: str
    kb_tags: List[str] = field(default_factory=list)
    git_branch: Optional[str] = None
    git_dirty: bool = False
    latest_commit: Optional[str] = None
    key_files: List[str] = field(default_factory=list)
    _refreshed_at: float = field(default=0.0, repr=False, compare=False)

    def refresh_git_info(self, force: bool = False):
        """Refresh git branch, dirty flag, latest commit, and key files.

        Results are reused for GIT_CACHE_TTL seconds unless ``force`` is set.
        Uses two git calls: ``status --porcelain=v2 --branch`` (branch and
        dirty state) and ``log -1`` (commit summary).
        """
        now = time.monotonic()
        if not force and self._refreshed_at and now - self._refreshed_at < GIT_CACHE_TTL:
            return
        self._refreshed_at = now
        self.key_files = [f for f in _KEY_FILE_CHECKS if (self.path / f).exists()]
        if not (self.path / ".git").exists():
            return

        status = _git(self.path, "status", "--porcelain=v2", "--branch")
        if status is not None:
            dirty = False
            for line in status.splitlines():
                if line.startswith("# branch.head "):
                    head = line[len("# branch.head "):].strip()
                    # Match `git rev-parse --abbrev-ref HEAD`, which prints HEAD when detached.
                    self.git_branch = "HEAD" if head == "(detached)" else head
                elif line and not line.startswith("#"):
                    dirty = True
            self.git_dirty = dirty

        commit = _git(self.path, "log", "-1", "--oneline")
        if commit is not None:
            self.latest_commit = commit.strip()


class ProjectManager:
    """Manages workspace projects, discovery, and active project context."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or REPO_ROOT
        self.clones_dir = self.root / "clones"
        self._projects: Dict[str, ProjectInfo] = {}
        self._active_project_id: Optional[str] = None
        self._initialize_registry()

    def _initialize_registry(self):
        """Register known core projects and discover any under clones/."""
        # Built-in projects
        known_defs = [
            {
                "id": "itariff-k8s",
                "name": "iTariff K8s & CI/CD",
                "dir": self.clones_dir / "itariff-k8s-repo",
                "category": "k8s-infra",
                "tech_stack": "Kubernetes / Helm / Jenkins / Docker",
                "description": "iTariff Kubernetes deployments, ConfigMaps, and Jenkins pipelines (tariff-selling-bff, truck service, etc.)",
                "kb_tags": ["itariff", "tariff", "selling-bff", "truck-service", "MSK", "Kafka"],
            },
            {
                "id": "prefiler-k8s",
                "name": "Prefiler K8s & CI/CD",
                "dir": self.clones_dir / "prefiler-k8s-repo",
                "category": "k8s-infra",
                "tech_stack": "Kubernetes / Istio / Jenkins / Helm",
                "description": "Prefiler SIT & DEV Kubernetes manifests, ConfigMaps, Secrets (prefiler-api-secret), and Jenkins pipelines",
                "kb_tags": ["prefiler", "prefiler-api", "prefiler-bff", "istio", "secrets", "euc1-itopaz-sit-eks"],
            },
            {
                "id": "itopaz-k8s",
                "name": "iTOPAZ K8s & CI/CD",
                "dir": self.clones_dir / "itopaz-k8-repo",
                "category": "k8s-infra",
                "tech_stack": "Kubernetes / Jenkins / Docker",
                "description": "Core iTOPAZ deployment manifests and Jenkins CI/CD pipelines (itopaz-export-ui, etc.)",
                "kb_tags": ["itopaz", "export-ui", "jenkins", "quality-gate"],
            },
            {
                "id": "ebx",
                "name": "TIBCO EBX Auto-Healing",
                "dir": self.root / "scripts" / "ebx-auto-healing",
                "category": "devops",
                "tech_stack": "Python / Bash / Systemd",
                "description": "Autonomous self-healing crash detector and service restarter for TIBCO EBX (SIT & PROD Frankfurt)",
                "kb_tags": ["ebx", "tibco", "auto-heal", "10.100.215.180", "10.100.110.76"],
            },
            {
                "id": "prefiler-services",
                "name": "Prefiler Microservices",
                "dir": self.clones_dir / "master-prefiler-service",
                "category": "backend",
                "tech_stack": ".NET 8 / C# / PostgreSQL / Redis",
                "description": "Prefiler backend microservices (master-prefiler-service, aci-prefiler, imdg-prefiler)",
                "kb_tags": ["prefiler-auth", "master-prefiler", "aci-prefiler", "imdg-prefiler"],
            },
            {
                "id": "microfrontend-ui",
                "name": "Prefiler Microfrontend UI",
                "dir": self.clones_dir / "microfrontend-main",
                "category": "frontend",
                "tech_stack": "Angular / single-spa / TypeScript",
                "description": "Prefiler Single-SPA shell container (microfrontend-main) and shared UI components",
                "kb_tags": ["single-spa", "microfrontend", "angular", "microfrontend-shared"],
            },
            {
                "id": "tariff-ui",
                "name": "Tariff Microfrontend UI",
                "dir": self.clones_dir / "tariff-microfrontend-main-ui",
                "category": "frontend",
                "tech_stack": "Angular / Webpack Module Federation",
                "description": "iTariff Microfrontend Shell & Share libraries",
                "kb_tags": ["tariff-ui", "tariff-microfrontend", "module-federation"],
            },
            {
                "id": "infrastructure",
                "name": "Infrastructure & Bastions",
                "dir": self.root / "infrastructure",
                "category": "devops",
                "tech_stack": "AWS / Azure / Bash / SSH Keys",
                "description": "Bastion connections, private SSH keys, Jenkins IP update scripts, cluster configs",
                "kb_tags": ["bastion", "ssh", "keys", "jenkins-ips", "china-aks", "environment-summaries"],
            },
            {
                "id": "jenkins-sonar",
                "name": "Jenkins & SonarQube Tools",
                "dir": self.root / "scripts",
                "category": "devops",
                "tech_stack": "Bash / AWS SSM / Docker Compose",
                "description": "Scripts for remote execution on Jenkins Master and SonarQube host via SSM and SSH",
                "kb_tags": ["jenkins-exec", "sonar-exec", "sonarqube", "spot-fleet", "10.100.95.13"],
            },
        ]

        for pdef in known_defs:
            p = ProjectInfo(
                id=pdef["id"],
                name=pdef["name"],
                path=pdef["dir"],
                category=pdef["category"],
                tech_stack=pdef["tech_stack"],
                description=pdef["description"],
                kb_tags=pdef["kb_tags"],
            )
            self._projects[p.id] = p

        # Dynamically discover any other clones (git state is fetched lazily)
        if self.clones_dir.is_dir():
            known_dirs = {p.path.name for p in self._projects.values()}
            for item in self.clones_dir.iterdir():
                if item.is_dir() and item.name not in known_dirs:
                    pid = item.name.lower().replace("_", "-")
                    p = ProjectInfo(
                        id=pid,
                        name=item.name,
                        path=item,
                        category="repo",
                        tech_stack="Git Repository",
                        description=f"Cloned repository {item.name}",
                        kb_tags=[item.name],
                    )
                    self._projects[p.id] = p
                    known_dirs.add(item.name)

    def list_projects(self) -> List[Dict[str, Any]]:
        """Return structured list of all projects and their git state."""
        items = sorted(self._projects.items())
        with ThreadPoolExecutor(max_workers=min(8, len(items) or 1)) as pool:
            list(pool.map(lambda kv: kv[1].refresh_git_info(), items))
        result = []
        for pid, p in items:
            result.append({
                "id": p.id,
                "name": p.name,
                "path": str(p.path.relative_to(self.root) if p.path.is_relative_to(self.root) else p.path),
                "category": p.category,
                "tech_stack": p.tech_stack,
                "branch": p.git_branch or "N/A",
                "dirty": p.git_dirty,
                "latest_commit": p.latest_commit or "N/A",
                "key_files": p.key_files,
                "is_active": (pid == self._active_project_id),
            })
        return result

    def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        """Get project by ID or directory name."""
        pid_clean = project_id.lower().replace("_", "-").strip()
        if pid_clean in self._projects:
            return self._projects[pid_clean]
        for pid, p in self._projects.items():
            if pid_clean in pid or pid_clean == p.path.name.lower():
                return p
        return None

    def set_active_project(self, project_id: str) -> Optional[ProjectInfo]:
        """Set active project for focused commands."""
        proj = self.get_project(project_id)
        if proj:
            self._active_project_id = proj.id
            proj.refresh_git_info()
            return proj
        return None

    def get_active_project(self) -> Optional[ProjectInfo]:
        """Return currently focused project."""
        if self._active_project_id and self._active_project_id in self._projects:
            proj = self._projects[self._active_project_id]
            proj.refresh_git_info()
            return proj
        return None

    def detect_project_from_path(self, cwd: Path) -> Optional[ProjectInfo]:
        """Detect project if working in a subfolder."""
        for p in self._projects.values():
            try:
                if cwd.resolve().is_relative_to(p.path.resolve()):
                    return p
            except Exception:
                pass
        return None


# Global singleton instance
project_manager = ProjectManager()


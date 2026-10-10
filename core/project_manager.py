#!/usr/bin/env python3
"""Project & Workspace Context Manager for iTOPAZ Agent.

Discovers and manages context for all AllCargo iTOPAZ repositories and services:
- clones/itariff-k8s-repo
- clones/prefiler-k8s-repo
- clones/itopaz-k8-repo
- clones/imdg-prefiler
- clones/aci-prefiler-service
- clones/master-prefiler-service
- clones/microfrontend-main
- clones/microfrontend-shared
- clones/tariff-microfrontend-main-ui
- clones/tariff-microfrontend-share-ui
- clones/tariff-company-service
- clones/mdm-bw-repo
- clones/bw_other_outbound_itopaz
- clones/ecu-zpa-user
- clones/aws-dashboard
- clones/itopaz-agent
- scripts/ebx-auto-healing
- infrastructure
"""

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

REPO_ROOT = Path(os.environ.get("ITOPAZ_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent)).resolve()


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

    def refresh_git_info(self):
        """Query live git branch, status, and commit."""
        if not (self.path / ".git").exists():
            return
        try:
            branch = subprocess.check_output(
                ["git", "-C", str(self.path), "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            self.git_branch = branch
        except Exception:
            pass

        try:
            status = subprocess.check_output(
                ["git", "-C", str(self.path), "status", "--porcelain"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            self.git_dirty = bool(status)
        except Exception:
            pass

        try:
            commit = subprocess.check_output(
                ["git", "-C", str(self.path), "log", "-1", "--oneline"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            self.latest_commit = commit
        except Exception:
            pass

        # Detect key files
        checks = [
            "Jenkinsfile",
            "Dockerfile",
            "package.json",
            "pom.xml",
            "requirements.txt",
            "appsettings.json",
            "docker-compose.yml",
        ]
        self.key_files = [f for f in checks if (self.path / f).exists()]


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
            p.refresh_git_info()
            self._projects[p.id] = p

        # Dynamically discover any other git clones
        if self.clones_dir.is_dir():
            for item in self.clones_dir.iterdir():
                if item.is_dir() and item.name not in [p.path.name for p in self._projects.values()]:
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
                    p.refresh_git_info()
                    self._projects[p.id] = p

    def list_projects(self) -> List[Dict[str, Any]]:
        """Return structured list of all projects and their git state."""
        result = []
        for pid, p in sorted(self._projects.items()):
            p.refresh_git_info()
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


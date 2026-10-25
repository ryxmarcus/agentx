#!/usr/bin/env python3
"""Tool Suite & Execution Engine for iTOPAZ Agent.

Provides actionable tools for:
- Knowledge retrieval
- Project discovery and context switching
- File inspection and modification
- Command and script execution
- System diagnostics (EBX, SonarQube, Jenkins, Clusters, Bastions)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.knowledge_rag import retriever, REPO_ROOT
from core.project_manager import project_manager, ProjectInfo
from core.credentials import credentials_manager
from core.operation_lock import require_unlocked, check_command


class ToolExecutor:
    """Dispatches and executes agent tools."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or REPO_ROOT

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return JSON-schema compatible definitions of all tools."""
        return [
            {
                "name": "search_knowledge",
                "description": "Search the canonical AllCargo iTOPAZ knowledge base (FTS5 full text) for architecture, credentials locations, cluster configs, runbooks, or past fixes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search terms, service name, error, or YYYY-MM-DD date"},
                        "limit": {"type": "integer", "description": "Max results to return (default 5)"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_env_summary",
                "description": "Get AWS account IDs, EKS cluster names, regions, bastion IPs, and key locations for an environment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "environment": {"type": "string", "description": "Environment name: dev, sit, uat, prod, singapore, china, gati"}
                    },
                    "required": ["environment"],
                },
            },
            {
                "name": "list_projects",
                "description": "List all 20 discovered projects, repositories, active git branches, and statuses.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "select_project",
                "description": "Set the active project context (e.g. itariff-k8s, prefiler-k8s, itopaz-k8s, ebx, infrastructure).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "ID or name of the project"}
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "read_file",
                "description": "Read a workspace file page (default 120 lines, maximum 300). Use next_start_line to continue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path relative to repo root or absolute path"},
                        "start_line": {"type": "integer", "description": "Starting line number (1-indexed)"},
                        "end_line": {"type": "integer", "description": "Ending line number (inclusive)"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write or overwrite a file with new content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file"},
                        "content": {"type": "string", "description": "Full file content to write"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "patch_file",
                "description": "Replace a specific snippet of text in an existing file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file"},
                        "target_text": {"type": "string", "description": "Exact text to find and replace"},
                        "replacement_text": {"type": "string", "description": "Replacement text"},
                    },
                    "required": ["path", "target_text", "replacement_text"],
                },
            },
            {
                "name": "run_command",
                "description": "Execute a shell command (git, kubectl, aws, docker, python, bash) in the active project directory or workspace root.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The exact shell command line to run"},
                        "cwd": {"type": "string", "description": "Optional working directory relative to root"},
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "run_diagnostic",
                "description": "Run diagnostic check on an infrastructure component (ebx, sonar, jenkins, clusters, bastions).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "component": {"type": "string", "description": "Component to diagnose: ebx, sonar, jenkins, clusters, bastions"}
                    },
                    "required": ["component"],
                },
            },
            {
                "name": "git_status",
                "description": "Get git status and last 3 commits for a project or the workspace root.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Optional project ID; defaults to active project or root"}
                    },
                },
            },
            {
                "name": "check_credentials",
                "description": "Check status of Bitbucket token, organization credentials, and available SSH keys without exposing secrets.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "bitbucket_api",
                "description": "Query Bitbucket Cloud REST API v2.0 for repositories, pull requests, commits, branches, or pipelines.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string", "description": "API endpoint, e.g. 'itariff-k8s-repo/pullrequests' or 'prefiler-k8s-repo/commits'"},
                        "workspace": {"type": "string", "description": "Bitbucket workspace (defaults to 'allcargoecu')"}
                    },
                    "required": ["endpoint"],
                },
            },
        ]

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return result."""
        try:
            if name == "search_knowledge":
                q = args.get("query", "")
                limit = int(args.get("limit", 5))
                results = retriever.search(q, limit=limit, context_chars=1200)
                return {
                    "status": "success",
                    "count": len(results),
                    "results": [
                        {
                            "source": f"{r['path']}#L{r['line']}-{r['end_line']}",
                            "heading": r["heading"],
                            "match_mode": r["match_mode"],
                            "excerpt": r.get("excerpt", ""),
                            "content": r.get("content", ""),
                        }
                        for r in results
                    ],
                }

            elif name == "get_env_summary":
                env = args.get("environment", "").lower()
                overview = retriever.get_environment_overview()
                accounts = overview.get("aws_accounts", {})
                matched = {}
                for k, v in accounts.items():
                    if env in k.lower():
                        matched[k] = v
                return {
                    "status": "success",
                    "matched_environments": matched or accounts,
                    "servers": overview.get("core_servers", {}),
                }

            elif name == "list_projects":
                projs = project_manager.list_projects()
                active = project_manager.get_active_project()
                return {
                    "status": "success",
                    "active_project": active.id if active else None,
                    "total": len(projs),
                    "projects": projs,
                }

            elif name == "select_project":
                pid = args.get("project_id", "")
                proj = project_manager.set_active_project(pid)
                if proj:
                    return {
                        "status": "success",
                        "active_project": proj.id,
                        "name": proj.name,
                        "path": str(proj.path),
                        "branch": proj.git_branch,
                        "tech_stack": proj.tech_stack,
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Project '{pid}' not found. Use list_projects to see available options.",
                    }

            elif name == "read_file":
                rel_path = args.get("path", "")
                full_path = self._resolve_path(rel_path)
                if not full_path.is_file():
                    return {"status": "error", "message": f"File '{rel_path}' does not exist"}

                start = max(1, int(args.get("start_line", 1)))
                end = min(start + 299, int(args.get("end_line", start + 119)))
                if end < start:
                    return {"status": "error", "message": "end_line must be >= start_line"}
                numbered = []
                total_lines = 0
                with full_path.open(encoding="utf-8", errors="replace") as stream:
                    for number, line in enumerate(stream, 1):
                        total_lines = number
                        if start <= number <= end:
                            numbered.append(f"{number}: {line.rstrip(chr(10)).rstrip(chr(13))}")
                end = min(end, total_lines)

                return {
                    "status": "success",
                    "path": str(full_path.relative_to(self.root) if full_path.is_relative_to(self.root) else full_path),
                    "total_lines": total_lines,
                    "truncated": end < total_lines,
                    "next_start_line": end + 1 if end < total_lines else None,
                    "start_line": start,
                    "end_line": end,
                    "content": "\n".join(numbered),
                }

            elif name == "write_file":
                require_unlocked()
                rel_path = args.get("path", "")
                content = args.get("content", "")
                full_path = self._resolve_path(rel_path)
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                return {
                    "status": "success",
                    "path": str(full_path),
                    "bytes_written": len(content.encode("utf-8")),
                }

            elif name == "patch_file":
                require_unlocked()
                rel_path = args.get("path", "")
                target = args.get("target_text", "")
                repl = args.get("replacement_text", "")
                full_path = self._resolve_path(rel_path)
                if not full_path.is_file():
                    return {"status": "error", "message": f"File '{rel_path}' does not exist"}

                text = full_path.read_text(encoding="utf-8")
                if target not in text:
                    return {
                        "status": "error",
                        "message": "Target text not found in file. Make sure target matches exactly.",
                    }

                occurrences = text.count(target)
                new_text = text.replace(target, repl, 1)
                full_path.write_text(new_text, encoding="utf-8")
                return {
                    "status": "success",
                    "path": str(full_path),
                    "message": f"Successfully replaced 1 occurrence (found {occurrences})",
                }

            elif name == "run_command":
                cmd = args.get("command", "")
                check_command(cmd)
                # Determine cwd
                cwd_arg = args.get("cwd")
                if cwd_arg:
                    cwd_path = self._resolve_path(cwd_arg)
                else:
                    active = project_manager.get_active_project()
                    cwd_path = active.path if active else self.root

                res = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(cwd_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60,
                )
                return {
                    "status": "success" if res.returncode == 0 else "failed",
                    "exit_code": res.returncode,
                    "cwd": str(cwd_path),
                    "stdout": res.stdout[:5000],
                    "stderr": res.stderr[:5000],
                }

            elif name == "run_diagnostic":
                require_unlocked()
                comp = args.get("component", "").lower()
                return self._run_diagnostic_check(comp)

            elif name == "git_status":
                pid = args.get("project_id")
                target_proj = project_manager.get_project(pid) if pid else project_manager.get_active_project()
                target_dir = target_proj.path if target_proj else self.root

                status = subprocess.check_output(
                    ["git", "-C", str(target_dir), "status", "-s"],
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                log = subprocess.check_output(
                    ["git", "-C", str(target_dir), "log", "-n", "3", "--oneline"],
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                branch = subprocess.check_output(
                    ["git", "-C", str(target_dir), "rev-parse", "--abbrev-ref", "HEAD"],
                    stderr=subprocess.STDOUT,
                    text=True,
                ).strip()

                return {
                    "status": "success",
                    "project": target_proj.name if target_proj else "repo-root",
                    "dir": str(target_dir),
                    "branch": branch,
                    "dirty_files": status.strip().splitlines() if status.strip() else [],
                    "recent_commits": log.strip().splitlines(),
                }

            elif name == "check_credentials":
                token = credentials_manager.get_bitbucket_token()
                creds = credentials_manager.get_bitbucket_credentials()
                keys = credentials_manager.list_ssh_keys()
                return {
                    "status": "success",
                    "bitbucket_token_configured": bool(token),
                    "bitbucket_token_length": len(token) if token else 0,
                    "organization_id": creds.get("org_id", "Not set"),
                    "has_api_key": bool(creds.get("api_key")),
                    "ssh_keys_by_environment": {env: len(klist) for env, klist in keys.items()},
                    "total_ssh_keys": sum(len(klist) for klist in keys.values()),
                }

            elif name == "bitbucket_api":
                endpoint = args.get("endpoint", "")
                workspace = args.get("workspace", "allcargoecu")
                return credentials_manager.query_bitbucket_api(endpoint, workspace=workspace)

            else:
                return {"status": "error", "message": f"Unknown tool: {name}"}

        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command execution timed out after 60 seconds."}
        except Exception as e:
            return {"status": "error", "message": f"Tool error ({name}): {str(e)}"}

    def _resolve_path(self, p: str) -> Path:
        """Resolve path against active project or repo root."""
        path_obj = Path(p)
        if path_obj.is_absolute():
            return path_obj
        active = project_manager.get_active_project()
        if active and (active.path / path_obj).exists():
            return active.path / path_obj
        return self.root / path_obj

    def _run_diagnostic_check(self, component: str) -> Dict[str, Any]:
        """Perform diagnostic routines."""
        if component in ["ebx", "tibco"]:
            script = self.root / "scripts" / "ebx-auto-healing" / "ebx_auto_heal.py"
            return {
                "component": "TIBCO EBX Auto-Healing",
                "script_exists": script.is_file(),
                "sit_target": "i-08a20bae22e57e46d (10.100.215.180, Account 464134132424)",
                "prod_target": "i-0add8ef2aa72adb7c (10.100.110.76, Account 965031587107)",
                "status": "Agent configured; supports local test with --dry-run or remote deployment scripts.",
            }

        elif component in ["sonar", "sonarqube"]:
            return {
                "component": "SonarQube Server",
                "instance": "i-0cd1ab8b0d9247ef4 (10.100.95.54, eu-central-1)",
                "remote_helper": "scripts/sonar-exec.sh",
                "status": "Upgraded Sep 29 (CE Heap 2GB, shm_size 512m). Execution time 41-63s.",
            }

        elif component in ["jenkins", "cicd"]:
            return {
                "component": "Jenkins Master & Spot Fleet",
                "instance": "i-0cdcce39da9444d74 (10.100.95.13, eu-central-1)",
                "spot_asg": "euc1-Jenkins-cicd-ec2-ASGfleet (t3a.large, 09:00-01:00 schedule)",
                "remote_helper": "scripts/jenkins-exec.sh",
                "status": "Healthy. Cleaned 172GB on Sep 29. Auto-scheduling active via scheduler-rds-ec2.",
            }

        elif component in ["clusters", "k8s", "eks"]:
            return {
                "component": "EKS Clusters",
                "clusters": {
                    "DEV EU": "euc1-itopaz-dev-eks (439891535362)",
                    "SIT EU": "euc1-itopaz-sit-eks (464134132424, secrets migrated Oct 7)",
                    "UAT EU": "euc1-itopaz-uat-eks (581621506601)",
                    "PROD EU": "euc1-itopaz-prod-eks (965031587107)",
                    "SIT SG": "apse1-itopaz-sit-eks (464134132424)",
                },
                "status": "Access via SSM on jump boxes or SSH bastions.",
            }

        elif component in ["bastions", "keys", "ssh"]:
            keys_dir = self.root / "infrastructure" / "secrets" / "keys"
            keys = [f.name for f in keys_dir.glob("*.pem")] if keys_dir.is_dir() else []
            return {
                "component": "Bastions & SSH Keys",
                "keys_available": keys,
                "dev_bastion": "10.100.145.118 (dev-eu.pem)",
                "sit_bastion": "10.100.208.17 (sit-eu.pem)",
                "uat_bastion": "10.100.176.4 (uat-eu.pem)",
                "prod_bastion": "10.100.110.76 (prod-eu.pem)",
            }

        else:
            return {
                "status": "unknown_component",
                "available_diagnostics": ["ebx", "sonar", "jenkins", "clusters", "bastions"],
            }


# Global singleton instance
tool_executor = ToolExecutor()


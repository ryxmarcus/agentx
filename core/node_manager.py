#!/usr/bin/env python3
"""Node Manager for the iTOPAZ distributed agent.

Purpose
-------
The LOCAL master agent uses this to reach worker nodes. The same logical
workspace lives at a different path/user on each node:

    local    (master) : C:\\Users\\rah_66160\\iTopaz-agents   (user rah_66160, Windows)
    worker-1 (AWS)    : /home/ec2-user/rahul                  (user ec2-user,  Linux)
    worker-2 (Linux)  : /home/ubuntu/rahul                    (user ubuntu,    Linux)

IMPORTANT — SERVER SAFETY
-------------------------
This module NEVER writes to or reconfigures a remote node. It only:
  * reads the local nodes.json registry,
  * builds ssh/scp command lines to run read/execute operations the caller asks for,
  * resolves the correct per-node variables (user, path, key, python).

"When running from local, variables differ; when running from a server, variables
differ" is handled here: each node carries its OWN environment variables, and
`resolve_var()` always returns the value for the *target* node, not the caller's.

Detection
---------
`current_node()` figures out which node this process is physically running on by
comparing the live workspace root against each node's declared `workspace_root`.
That lets the identical codebase behave correctly whether it is the local master
or a copy deployed on a worker — without any server-side change.
"""

import json
import os
import shlex
from core.operation_lock import check_command, require_unlocked
from pathlib import Path
from typing import Any, Dict, List, Optional

# agent repo root (…/iTopaz-agents locally, …/rahul/agent on a worker)
AGENT_ROOT = Path(__file__).resolve().parent.parent


class Node:
    def __init__(self, node_id: str, cfg: Dict[str, Any]):
        self.id = node_id
        self.cfg = cfg
        self.role = cfg.get("role", "worker")
        self.label = cfg.get("label", node_id)
        self.transport = cfg.get("transport", "ssh")
        self.os = cfg.get("os", "linux")
        self.user = cfg.get("user", "")
        self.host = cfg.get("host", "")
        self.workspace_root = cfg.get("workspace_root", "")
        self.agent_entry = cfg.get("agent_entry", "")
        self.python = cfg.get("python", "python3")
        self.ssh_key = cfg.get("ssh_key", "")
        self.ssh_key_fallback = cfg.get("ssh_key_fallback", "")
        # Optional overflow nodes are only recruited when load is high.
        self.optional = bool(cfg.get("optional", False))
        self.activation = cfg.get("activation", "always")  # "always" | "on_load"
        self.notes = cfg.get("notes", "")

    # ------------------------------------------------------------------ #
    def resolve_var(self, name: str) -> Any:
        """Return a node-specific variable for THIS (target) node.

        This is the core of the local-vs-server difference: the caller may be
        local, but when it asks for worker-1's `workspace_root` it gets
        /home/ec2-user/rahul, never the local path.
        """
        return self.cfg.get(name)

    def remote_path(self, *parts: str) -> str:
        """Join a path under this node's workspace_root using POSIX separators
        for linux nodes and native separators for the local windows master."""
        if self.os == "windows":
            return str(Path(self.workspace_root, *parts))
        base = self.workspace_root.rstrip("/")
        tail = "/".join(p.strip("/") for p in parts if p)
        return f"{base}/{tail}" if tail else base

    def _best_key(self) -> str:
        if self.ssh_key and Path(self.ssh_key).exists():
            return self.ssh_key
        if self.ssh_key_fallback and Path(self.ssh_key_fallback).exists():
            return self.ssh_key_fallback
        return self.ssh_key or self.ssh_key_fallback

    # ------------------------------------------------------------------ #
    def ssh_command(self, remote_cmd: str, connect_timeout: int = 8) -> List[str]:
        """Build an argv list that runs `remote_cmd` on this node.

        For the local master this returns a plain shell invocation (no ssh).
        Never performs any configuration — only runs what the caller passes.
        """
        check_command(remote_cmd)
        if self.transport == "local":
            return ["powershell", "-NoProfile", "-Command", remote_cmd] if self.os == "windows" else ["sh", "-c", remote_cmd]

        key = self._best_key()
        argv = [
            "ssh",
            "-i", key,
            "-o", "StrictHostKeyChecking=yes",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={connect_timeout}",
            f"{self.user}@{self.host}",
            remote_cmd,
        ]
        return argv

    def agent_invocation(self, task: str) -> List[str]:
        """Build the command to run this node's OWN agent entrypoint with a task.

        Uses the node's own python + agent_entry (its server-side paths), so the
        remote agent runs with its local variables, not the master's.
        """
        require_unlocked()
        if self.cfg.get("agent_deployed") is False:
            raise RuntimeError(f"Agent entry point is not deployed on {self.id}: {self.agent_entry}")
        if self.transport == "local":
            return [self.python, self.agent_entry, task]
        inner = f"{shlex.quote(self.python)} {shlex.quote(self.agent_entry)} {shlex.quote(task)}"
        return self.ssh_command(inner)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "role": self.role,
            "label": self.label,
            "transport": self.transport,
            "os": self.os,
            "user": self.user,
            "workspace_root": self.workspace_root,
            "agent_entry": self.agent_entry,
            "python": self.python,
            "optional": self.optional,
            "activation": self.activation,
        }
        if self.transport == "ssh":
            d["host"] = self.host
            d["ssh_key"] = self._best_key()
        return d


class NodeManager:
    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or (AGENT_ROOT / "nodes.json")
        self._nodes: Dict[str, Node] = {}
        self._load()

    def _load(self):
        if not self.registry_path.is_file():
            return
        try:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception:
            return
        for node_id, cfg in raw.items():
            if node_id.startswith("_"):
                continue
            if not isinstance(cfg, dict):
                continue
            self._nodes[node_id] = Node(node_id, cfg)

    # ------------------------------------------------------------------ #
    def get(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def list_nodes(self) -> List[Dict[str, Any]]:
        return [n.to_dict() for n in self._nodes.values()]

    def workers(self, include_optional: bool = False) -> List[Node]:
        """Return worker nodes.

        By default returns only the always-on primary workers. Optional
        overflow nodes (e.g. worker-2) are excluded unless `include_optional`
        is True — i.e. unless the caller has decided load is high enough to
        recruit them.
        """
        result = []
        for n in self._nodes.values():
            if n.role != "worker" or not n.cfg.get("enabled", True):
                continue
            if n.optional and not include_optional:
                continue
            result.append(n)
        return result

    def primary_workers(self) -> List[Node]:
        """Always-on workers (the default pool, excludes overflow)."""
        return self.workers(include_optional=False)

    def overflow_workers(self) -> List[Node]:
        """Optional nodes recruited only when load increases."""
        return [n for n in self._nodes.values() if n.role == "worker" and n.optional]

    def select_workers(self, high_load: bool = False) -> List[Node]:
        """Pick the worker set for a dispatch.

        high_load=False -> primary workers only.
        high_load=True  -> primary workers plus optional overflow nodes.
        """
        return self.workers(include_optional=high_load)

    def master(self) -> Optional[Node]:
        for n in self._nodes.values():
            if n.role == "master":
                return n
        return None

    def current_node(self) -> Optional[Node]:
        """Detect which registered node this process is physically running on.

        Matches the live agent root against each node's workspace_root so the
        same code identifies itself correctly on the master or any worker.
        """
        here = str(os.environ.get("ITOPAZ_WORKSPACE_ROOT", AGENT_ROOT)).replace("\\", "/").rstrip("/").lower()
        for n in self._nodes.values():
            root = (n.workspace_root or "").replace("\\", "/").rstrip("/").lower()
            if not root:
                continue
            # agent may live either at workspace_root (local) or workspace_root/agent (worker)
            if here == root or here == f"{root}/agent" or here.startswith(root + "/"):
                return n
        return None


# Global singleton — safe to import anywhere in the agent.
node_manager = NodeManager()

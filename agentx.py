#!/usr/bin/env python3
"""AllCargo iTOPAZ Autonomous Multi-Project Agent CLI.

Can be run locally from terminal:
- Interactive REPL mode:  python3 agent/itopaz_agent.py
- Single-command mode:    python3 agent/itopaz_agent.py "Fix tariff-selling-bff build issue"
- Fast knowledge search:  python3 agent/itopaz_agent.py --search "2026-10-07 prefiler secret"
- Project switch:         python3 agent/itopaz_agent.py -p itariff-k8s
"""

import argparse
import json
import shutil
import os
try:
    import readline
except ImportError:
    readline = None
import sys
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.agent_loop import AgentLoop
from core.knowledge_rag import retriever
from core.llm_client import UniversalLLMClient
from core.node_manager import node_manager
from core.project_manager import project_manager
from core.tools import tool_executor
from core.operation_lock import is_locked

VERSION = "1.4.0"
BANNER = """\033[1;36m
+--------------------------------------------------------------+
|            AllCargo iTOPAZ Autonomous Agent CLI               |
|            Local DevOps & Multi-Project Assistant             |
+--------------------------------------------------------------+\033[0m
"""

HELP_TEXT = """\033[1mCommands:\033[0m
  \033[33m/projects\033[0m              List discovered repositories in workspace
  \033[33m/project <id>\033[0m          Switch active project focus (e.g. /p itariff-k8s)
  \033[33m/kb <query>\033[0m            Direct knowledge base search (FTS5 full text)
  \033[33m/doctor\033[0m                Show local health and lock status
  \033[33m/status\033[0m                Git status & recent commits for current project
  \033[33m/env <name>\033[0m            Show AWS/EKS/Bastion details (dev, sit, uat, prod, sg)
  \033[33m/keys\033[0m                  Check Bitbucket token & SSH key counts
  \033[33m/diag <comp>\033[0m           Run diagnostic (ebx, sonar, jenkins, clusters, bastions)
  \033[33m/nodes\033[0m                 List master + worker nodes and show which one you're on
  \033[33m/run-on <id> <cmd>\033[0m     Run a command on a worker node over SSH (executes supplied command)
  \033[33m!<shell cmd>\033[0m           Run shell command directly in active project directory
  \033[33m/clear\033[0m                 Clear terminal screen
  \033[33m/help\033[0m                  Show this help message
  \033[33m/exit\033[0m or \033[33m/quit\033[0m         Exit agent session

\033[1mTasks:\033[0m
  Enter any natural language task or question to let the agent autonomously
  investigate, search knowledge, and read files. Writing and command
  execution follow the workspace operation lock.
"""


def node_tag(node):
    if not node.get("enabled", True):
        return "[disabled / standby]"
    if node.get("optional"):
        return "[optional]"
    return "[primary]" if node["role"] == "worker" else ""


def doctor_report():
    from core.knowledge_rag import REPO_ROOT as workspace
    current = node_manager.current_node()
    sources = ["knowledge-base/KNOWLEDGE-BASE.md", "infrastructure/activity-log.md", "infrastructure/environment-summaries.md"]
    return {
        "version": VERSION,
        "workspace": str(workspace),
        "python": sys.version.split()[0],
        "current_node": current.id if current else "unknown",
        "operation_locked": is_locked(),
        "ssh_available": shutil.which("ssh") is not None,
        "knowledge_sources": {path: (workspace / path).is_file() for path in sources},
        "active_workers": [node.id for node in node_manager.workers()],
        "nodes": [{"id": node["id"], "enabled": node.get("enabled", True), "optional": node.get("optional", False), "agent_deployed": node.get("agent_deployed"), "key_exists": Path(node["ssh_key"]).is_file() if "ssh_key" in node else None} for node in node_manager.list_nodes()],
        "scope": "Local inspection only; no network or provider calls",
    }


def print_doctor():
    print(json.dumps(doctor_report(), indent=2))


def setup_history():
    """Enable readline command history."""
    if readline is None:
        return
    hist_file = REPO_ROOT / ".tmp" / ".itopaz_agent_history"
    try:
        hist_file.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    try:
        if hist_file.is_file():
            readline.read_history_file(str(hist_file))
    except Exception:
        pass
    import atexit
    atexit.register(lambda: readline.write_history_file(str(hist_file)) if hist_file.parent.exists() else None)


def print_projects_table():
    projs = project_manager.list_projects()
    active = project_manager.get_active_project()
    print(f"\n\033[1;34m=== Discovered Projects ({len(projs)}) ===\033[0m")
    print(f"{'ID':22} | {'BRANCH':14} | {'NAME':25} | {'PATH'}")
    print("-" * 80)
    for p in projs:
        is_act = " \033[1;32m*\033[0m" if active and active.id == p["id"] else "  "
        dirty = "\033[31m(dirty)\033[0m" if p["dirty"] else ""
        print(f"{is_act} {p['id']:20} | {p['branch']:14} | {p['name'][:24]:25} | {p['path']} {dirty}")
    print()


def interactive_repl(loop: AgentLoop):
    """Run interactive REPL loop."""
    print(BANNER)
    print(f"Version: {VERSION} | Operation lock: {'LOCKED' if is_locked() else 'UNLOCKED'}")
    active = project_manager.get_active_project()
    print(f"Provider: \033[1;32m{loop.llm.provider}\033[0m | Model: \033[1;32m{loop.llm.model}\033[0m")
    print("Type \033[1;33m/help\033[0m for commands or enter any DevOps/coding task directly.\n")
    setup_history()

    while True:
        try:
            active = project_manager.get_active_project()
            proj_badge = f"\033[1;35m[{active.id}]\033[0m " if active else "\033[1;34m[all]\033[0m "
            prompt = f"{proj_badge}\033[1;32miTOPAZ-Agent>\033[0m "
            user_input = input(prompt).strip()

            if not user_input:
                continue

            if user_input in ["/exit", "/quit", "exit", "quit"]:
                print("\nGoodbye!")
                break

            elif user_input in ["/help", "help"]:
                print(HELP_TEXT)

            elif user_input == "/doctor":
                print_doctor()

            elif user_input in ["/clear", "clear"]:
                os.system("cls" if os.name == "nt" else "clear")

            elif user_input in ["/projects", "/list"]:
                print_projects_table()

            elif user_input.split(maxsplit=1)[0] in ("/project", "/p"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    target = parts[1].strip()
                    proj = project_manager.set_active_project(target)
                    if proj:
                        print(f"\033[1;32mActive project set to:\033[0m {proj.name} ({proj.path}) [branch: {proj.git_branch}]")
                    else:
                        print(f"\033[1;31mError:\033[0m Project '{target}' not found. Run /projects to see options.")
                else:
                    active = project_manager.get_active_project()
                    print(f"Current active project: {active.name if active else 'None'}")

            elif user_input.startswith("/kb"):
                q = user_input[3:].strip()
                if not q:
                    print("Usage: /kb <search terms>")
                    continue
                results = retriever.search(q, limit=5, context_chars=300)
                print(f"\n\033[1;34m=== Knowledge Results ({len(results)}) ===\033[0m")
                for r in results:
                    print(f"\033[1;36m{r['path']}#L{r['line']}\033[0m [{r['heading']}]")
                    print(f"  {r.get('excerpt', '')}\n")

            elif user_input.startswith("/diag"):
                parts = user_input.split(maxsplit=1)
                comp = parts[1].strip() if len(parts) > 1 else "clusters"
                res = tool_executor.execute_tool("run_diagnostic", {"component": comp})
                print(f"\n\033[1;34m=== Diagnostic: {comp} ===\033[0m")
                for k, v in res.items():
                    print(f"  \033[1m{k}\033[0m: {v}")
                print()

            elif user_input.startswith("/status"):
                res = tool_executor.execute_tool("git_status", {})
                print(f"\n\033[1;34m=== Git Status: {res.get('project')} ===\033[0m")
                print(f"Branch: \033[1;32m{res.get('branch')}\033[0m")
                if res.get("dirty_files"):
                    print("Modified files:")
                    for f in res.get("dirty_files", []):
                        print(f"  \033[31m{f}\033[0m")
                else:
                    print("Working tree clean.")
                print("Recent commits:")
                for c in res.get("recent_commits", []):
                    print(f"  {c}")
                print()

            elif user_input.startswith("/env"):
                parts = user_input.split(maxsplit=1)
                env_target = parts[1].strip() if len(parts) > 1 else "all"
                res = tool_executor.execute_tool("get_env_summary", {"environment": env_target})
                print(f"\n\033[1;34m=== Environment Summary ===\033[0m")
                for env, data in res.get("matched_environments", {}).items():
                    print(f"ΓÇó \033[1m{env}\033[0m: Account \033[36m{data.get('account_id')}\033[0m | Cluster \033[32m{data.get('cluster')}\033[0m | Bastion \033[33m{data.get('bastion')}\033[0m")
                print()

            elif user_input in ["/keys", "/creds"]:
                res = tool_executor.execute_tool("check_credentials", {})
                print(f"\n\033[1;34m=== Credentials & Keys Status ===\033[0m")
                status_color = "\033[1;32mConfigured\033[0m" if res.get("bitbucket_token_configured") else "\033[1;31mMissing\033[0m"
                print(f"Bitbucket Token:     {status_color} (length: {res.get('bitbucket_token_length')})")
                print(f"Organization ID:     {res.get('organization_id')}")
                print(f"Total SSH Keys:      \033[1;32m{res.get('total_ssh_keys')}\033[0m across {len(res.get('ssh_keys_by_environment', {}))} environments")
                for env, count in res.get("ssh_keys_by_environment", {}).items():
                    print(f"  ΓÇó \033[1m{env:12}\033[0m: {count} key(s)")
                print()

            elif user_input.startswith("/nodes"):
                cur = node_manager.current_node()
                print(f"\n\033[1;34m=== Registered Nodes ===\033[0m")
                print(f"Running on: \033[1;32m{cur.id if cur else 'unknown'}\033[0m\n")
                for n in node_manager.list_nodes():
                    marker = " \033[1;32m*\033[0m" if cur and cur.id == n["id"] else "  "
                    tgt = n.get("host", "localhost")
                    tag = " " + node_tag(n)
                    print(f"{marker} \033[1m{n['id']:10}\033[0m [{n['role']:6}] {n['user']}@{tgt}  ->  {n['workspace_root']}{tag}")
                print()

            elif user_input.startswith("/run-on"):
                # /run-on <node-id> <command...>
                parts = user_input.split(maxsplit=2)
                if len(parts) < 3:
                    print("Usage: /run-on <node-id> <command>   (e.g. /run-on worker-2 'git -C rahul pull')")
                    continue
                node_id, remote_cmd = parts[1].strip(), parts[2].strip()
                node = node_manager.get(node_id)
                if not node:
                    print(f"\033[1;31mError:\033[0m Node '{node_id}' not found. Try /nodes.")
                    continue
                argv = node.ssh_command(remote_cmd)
                print(f"\033[1;34m[{node.id}] {node.user}@{node.host or 'local'}:\033[0m {remote_cmd}")
                try:
                    import subprocess as _sp
                    res = _sp.run(argv, stdout=_sp.PIPE, stderr=_sp.PIPE, text=True, timeout=120)
                    if res.stdout:
                        print(res.stdout)
                    if res.stderr:
                        print(f"\033[31m{res.stderr}\033[0m")
                except Exception as e:
                    print(f"\033[1;31mError:\033[0m {e}")

            elif user_input.startswith("!"):
                cmd = user_input[1:].strip()
                res = tool_executor.execute_tool("run_command", {"command": cmd})
                if res.get("stdout"):
                    print(res["stdout"])
                if res.get("stderr"):
                    print(f"\033[31m{res['stderr']}\033[0m")

            else:
                # Free-form agent task
                answer = loop.run_task(user_input)
                print(f"\n{answer}\n")

        except KeyboardInterrupt:
            print("\n(Use /exit to quit)")
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n\033[1;31mError:\033[0m {e}\n")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="AllCargo iTOPAZ Autonomous Multi-Project Agent CLI")
    parser.add_argument("task", nargs="?", help="Task or question to execute non-interactively")
    parser.add_argument("-p", "--project", help="Select active project ID (e.g. itariff-k8s, prefiler-k8s)")
    parser.add_argument("--provider", choices=["auto", "openai", "anthropic", "gemini", "ollama", "bedrock", "offline"], help="LLM provider")
    parser.add_argument("--model", help="Specific model name")
    parser.add_argument("--list-projects", action="store_true", help="List all discovered projects and exit")
    parser.add_argument("--search", help="Search knowledge base and exit")
    parser.add_argument("--diag", help="Run diagnostic component and exit")
    parser.add_argument("--env-summary", help="Show environment summary and exit")
    parser.add_argument("--keys", action="store_true", help="Show credentials, Bitbucket token status, and SSH keys")
    parser.add_argument("--nodes", action="store_true", help="List registered master/worker nodes and exit")

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--doctor", action="store_true", help="Report local health and operation lock as JSON; no network calls")

    parser.add_argument("--serve", action="store_true", help="Serve HTTP health and authenticated knowledge search")
    parser.add_argument("--port", type=int, default=8082, help="HTTP port (default 8082)")
    parser.add_argument("--control-status", action="store_true", help="Check DEV controller, chatbot and dashboard")
    parser.add_argument("--chat", help="Ask the connected knowledge chatbot")
    parser.add_argument("--approve", help="Review and explicitly approve a resource proposal from the Windows master")
    dashboard = parser.add_mutually_exclusive_group()
    dashboard.add_argument("--dashboard-accounts", action="store_true", help="List configured AWS accounts directly from the Dashboard API")
    dashboard.add_argument("--dashboard-action", metavar="JSON_FILE", help="Review and approve one exact AWS action directly through the Dashboard API")

    args = parser.parse_args()
    if args.dashboard_accounts or args.dashboard_action:
        from core.dashboard_client import accounts, approve_file
        try:
            result = approve_file(args.dashboard_action) if args.dashboard_action else accounts()
            print(json.dumps(result, indent=2))
        except Exception as error:
            parser.exit(1, f"Dashboard request failed: {error}\n")
        return
    if args.control_status or args.chat or args.approve:
        from core.control_client import request, approve
        try:
            result = approve(args.approve) if args.approve else request("/control/chat", {"question": args.chat}) if args.chat else request("/control/status")
            print(json.dumps(result, indent=2))
        except Exception as error:
            parser.exit(1, f"Control request failed: {error}\n")
        return
    if args.serve:
        from core.http_server import serve
        serve(port=args.port)
        return
    if args.doctor:
        print_doctor()
        return

    if args.nodes:
        cur = node_manager.current_node()
        print(f"\n=== Registered Nodes (running on: {cur.id if cur else 'unknown'}) ===")
        for n in node_manager.list_nodes():
            tgt = n.get("host", "localhost")
            tag = " " + node_tag(n)
            print(f"  {n['id']:10} [{n['role']:6}] {n['user']}@{tgt} -> {n['workspace_root']}{tag}")
        print()
        return

    if args.keys:
        res = tool_executor.execute_tool("check_credentials", {})
        print(f"\n=== Credentials & Keys Status ===")
        print(f"Bitbucket Token:     {'Configured' if res.get('bitbucket_token_configured') else 'Missing'} (length: {res.get('bitbucket_token_length')})")
        print(f"Organization ID:     {res.get('organization_id')}")
        print(f"Total SSH Keys:      {res.get('total_ssh_keys')} across {len(res.get('ssh_keys_by_environment', {}))} environments")
        for env, count in res.get("ssh_keys_by_environment", {}).items():
            print(f"  ΓÇó {env:12}: {count} key(s)")
        print()
        return

    if args.list_projects:
        print_projects_table()
        return

    if args.search:
        results = retriever.search(args.search, limit=5, context_chars=500)
        print(f"\nResults for '{args.search}' ({len(results)} matches):")
        for r in results:
            print(f"- {r['path']}#L{r['line']} [{r['heading']}]\n  {r.get('excerpt', '')}\n")
        return

    if args.diag:
        res = tool_executor.execute_tool("run_diagnostic", {"component": args.diag})
        for k, v in res.items():
            print(f"{k}: {v}")
        return

    if args.env_summary:
        res = tool_executor.execute_tool("get_env_summary", {"environment": args.env_summary})
        for env, data in res.get("matched_environments", {}).items():
            print(f"{env}: Account {data.get('account_id')} | Cluster {data.get('cluster')} | Bastion {data.get('bastion')}")
        return

    # Select project if passed
    if args.project:
        proj = project_manager.set_active_project(args.project)
        if not proj:
            print(f"Warning: Project '{args.project}' not found. Proceeding with workspace root.")

    # Initialize client & loop
    llm = UniversalLLMClient()
    if args.provider:
        llm.provider = args.provider
    if args.model:
        llm.model = args.model

    loop = AgentLoop(llm_client=llm, verbose=True)

    if args.task:
        answer = loop.run_task(args.task)
        print(f"\n{answer}")
    else:
        interactive_repl(loop)


if __name__ == "__main__":
    main()


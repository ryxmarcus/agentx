#!/usr/bin/env python3
"""Autonomous ReAct Loop for iTOPAZ Agent.

Orchestrates reasoning, tool execution, and knowledge synthesis.
"""

import json
import sys
from typing import Any, Dict, List, Optional

from core.knowledge_rag import retriever
from core.llm_client import UniversalLLMClient, ToolCall
from core.project_manager import project_manager, ProjectInfo
from core.tools import tool_executor


class AgentLoop:
    """Executes multi-step reasoning and tool calls to solve user tasks."""

    def __init__(self, llm_client: Optional[UniversalLLMClient] = None, verbose: bool = True):
        self.llm = llm_client or UniversalLLMClient()
        self.tools = tool_executor.get_tool_definitions()
        self.verbose = verbose

    def _build_system_prompt(self, active_project: Optional[ProjectInfo]) -> str:
        """Construct system prompt with context and operational principles."""
        proj_str = "No specific project selected (operating across workspace)."
        if active_project:
            proj_str = (
                f"Active Project: {active_project.name} (id: {active_project.id})\n"
                f"- Directory: {active_project.path}\n"
                f"- Git Branch: {active_project.git_branch or 'N/A'}\n"
                f"- Tech Stack: {active_project.tech_stack}\n"
                f"- Key Files: {', '.join(active_project.key_files) or 'None'}\n"
            )

        return f"""You are the AllCargo iTOPAZ Autonomous Engineer & DevOps Assistant.
You have direct access to:
1. The canonical knowledge base:
   - knowledge-base/KNOWLEDGE-BASE.md (domain, architecture, cluster & inventory reference)
   - infrastructure/activity-log.md (reverse-chronological operational & incident changes)
   - infrastructure/environment-summaries.md (scoped evidence per environment)
   - scripts/ebx-auto-healing/README.md (TIBCO EBX auto-healing)
   - AI-INDEX.md (retrieval workflow)
2. All 20 projects and repositories in this workspace (clones/, scripts/, infrastructure/).
3. AWS, Kubernetes, Jenkins, SonarQube, and bastion hosts across DEV, SIT, UAT, PROD, Singapore, and China.

Current Project Context:
{proj_str}

Operational Guidelines:
- Ground answers in canonical files. Cite file paths and line ranges (e.g. `KNOWLEDGE-BASE.md#L1046`).
- When diagnosing issues, check recent entries in `infrastructure/activity-log.md` first.
- Always use available tools (search_knowledge, read_file, run_command, git_status, run_diagnostic) rather than guessing.
- Verify file locations and git branch before editing.
- Never output raw secret credentials (use referenced secret names like prefiler-api-secret or files in infrastructure/secrets/).
- Keep explanations clear, actionable, and formatted in clean markdown.
"""

    def run_task(self, user_goal: str, max_turns: int = 8) -> str:
        """Execute task through ReAct loop until complete."""
        active_proj = project_manager.get_active_project()
        system_prompt = self._build_system_prompt(active_proj)

        # Pre-seed relevant knowledge chunks into prompt for faster grounded reasoning
        kb_context = retriever.get_context_for_prompt(user_goal, max_results=3, max_chars=3000)

        initial_message = (
            f"User Task: {user_goal}\n\n"
            f"Relevant Knowledge Base Findings:\n{kb_context}"
        )

        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": initial_message}
        ]

        if self.verbose:
            print(f"\n[\033[1;34mAgent\033[0m] Provider: {self.llm.provider} | Model: {self.llm.model}")
            if active_proj:
                print(f"[\033[1;34mAgent\033[0m] Focused Project: \033[1;32m{active_proj.name}\033[0m ({active_proj.git_branch})")

        turn = 0
        final_answer = ""

        while turn < max_turns:
            turn += 1
            if self.verbose:
                print(f"[\033[1;34mTurn {turn}/{max_turns}\033[0m] Thinking...", end="\r", flush=True)

            response = self.llm.chat_complete(
                messages=messages,
                tools=self.tools,
                system_prompt=system_prompt,
            )

            # If no tool calls, response is complete
            if not response.tool_calls:
                final_answer = response.content
                if self.verbose:
                    print(f"[\033[1;32mComplete\033[0m] Task finished in {turn} turns.\n")
                break

            # Execute tool calls
            assistant_content = response.content or "Executing tool actions to resolve task..."
            messages.append({"role": "assistant", "content": assistant_content})

            if self.verbose:
                print(f"\n[\033[1;33mAction\033[0m] {assistant_content}")

            for tc in response.tool_calls:
                if self.verbose:
                    print(f"  ΓööΓöÇΓû║ \033[1;36m{tc.name}\033[0m({json.dumps(tc.arguments)})")

                tool_result = tool_executor.execute_tool(tc.name, tc.arguments)

                # Format tool result for next turn
                result_str = json.dumps(tool_result, ensure_ascii=False, indent=2)
                messages.append({
                    "role": "user",
                    "content": f"[Tool Result: {tc.name}]\n{result_str}",
                })

            # In offline rule engine mode, stop after tool execution + synthesize
            if self.llm.provider == "offline":
                final_answer = self._synthesize_offline_result(user_goal, tool_result, tc.name)
                break

        if not final_answer:
            final_answer = response.content or "Completed actions. Check tool outputs above."

        return final_answer

    def _synthesize_offline_result(self, goal: str, result: Dict[str, Any], tool_name: str) -> str:
        """Create structured response when in offline mode."""
        lines = [f"### Execution Summary: {goal}\n"]
        if tool_name == "search_knowledge":
            lines.append(f"Found **{result.get('count', 0)}** matching knowledge sections:")
            for r in result.get("results", []):
                lines.append(f"- **[{r['source']}] {r['heading']}**")
                lines.append(f"  {r.get('excerpt', '')}\n")
        elif tool_name == "list_projects":
            lines.append(f"Registered **{result.get('total', 0)}** projects in workspace:")
            for p in result.get("projects", []):
                active_mark = " (ACTIVE)" if p["is_active"] else ""
                lines.append(f"- **{p['name']}** [`{p['id']}`]{active_mark} ΓÇö Branch: `{p['branch']}` | Path: `{p['path']}`")
        elif tool_name == "get_env_summary":
            lines.append("Environment Details:")
            for env, data in result.get("matched_environments", {}).items():
                lines.append(f"- **{env}**: Account `{data.get('account_id')}` | Cluster `{data.get('cluster')}` | Bastion `{data.get('bastion')}`")
        elif tool_name == "run_diagnostic":
            lines.append(f"Diagnostic Report: **{result.get('component', '')}**")
            for k, v in result.items():
                if k != "component":
                    lines.append(f"- **{k}**: {v}")
        elif tool_name == "git_status":
            lines.append(f"Project **{result.get('project')}** (branch `{result.get('branch')}`):")
            lines.append("Recent commits:")
            for c in result.get("recent_commits", []):
                lines.append(f"  - `{c}`")
            if result.get("dirty_files"):
                lines.append(f"Modified files ({len(result.get('dirty_files'))}):")
                for df in result.get("dirty_files", []):
                    lines.append(f"  - `{df}`")
            else:
                lines.append("Working tree clean.")
        else:
            lines.append(f"Tool `{tool_name}` output:\n```json\n{json.dumps(result, indent=2)}\n```")

        return "\n".join(lines)


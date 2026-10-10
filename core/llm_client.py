#!/usr/bin/env python3
"""Multi-Provider LLM Client for iTOPAZ Agent.

Supports:
1. OpenAI / OpenAI-Compatible (OpenAI, Groq, OpenRouter, DeepSeek, Local Ollama /v1)
2. Anthropic Claude (Direct Claude API)
3. AWS Bedrock (SigV4 / Converse API)
4. Google Gemini (Generative Language API)
5. Ollama Native (http://localhost:11434/api/chat)
6. Offline / Rule-Based Assistant (No API key required)
"""

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    provider: str = "unknown"
    model: str = "unknown"


class UniversalLLMClient:
    """Manages connections to multiple LLM providers with automatic fallback."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.provider = self.config.get("provider", "auto")
        self.model = self.config.get("model", "")
        self._detect_provider()

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from config.json or environment variables."""
        defaults = {
            "provider": os.environ.get("AGENT_LLM_PROVIDER", "auto"),
            "model": os.environ.get("AGENT_LLM_MODEL", ""),
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "openai_base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
            "ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            "bedrock_region": os.environ.get("BEDROCK_REGION", "eu-central-1"),
            "bedrock_model_id": os.environ.get("BEDROCK_MODEL_ID", "eu.amazon.nova-lite-v1:0"),
        }

        # Check local config file if exists
        p = config_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    file_conf = json.load(f)
                    defaults.update(file_conf)
            except Exception:
                pass

        return defaults

    def _detect_provider(self):
        """Auto-detect provider based on available credentials."""
        if self.provider != "auto":
            return

        if self.config.get("openai_api_key"):
            self.provider = "openai"
            if not self.model:
                self.model = "gpt-4o"
        elif self.config.get("anthropic_api_key"):
            self.provider = "anthropic"
            if not self.model:
                self.model = "claude-3-5-sonnet-20240620"
        elif self.config.get("gemini_api_key"):
            self.provider = "gemini"
            if not self.model:
                self.model = "gemini-1.5-pro"
        elif self._is_ollama_alive():
            self.provider = "ollama"
            if not self.model:
                self.model = "qwen2.5-coder:latest"
        elif os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_PROFILE"):
            self.provider = "bedrock"
            if not self.model:
                self.model = self.config.get("bedrock_model_id", "eu.amazon.nova-lite-v1:0")
        else:
            self.provider = "offline"
            self.model = "rule-based-assistant"

    def _is_ollama_alive(self) -> bool:
        """Check if local Ollama server is responding."""
        base = self.config.get("ollama_base_url", "http://localhost:11434")
        try:
            req = urllib.request.Request(f"{base}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1) as resp:
                return resp.status == 200
        except Exception:
            return False

    def chat_complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate response and tool calls."""
        if self.provider == "openai":
            return self._call_openai_compatible(messages, tools, system_prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(messages, tools, system_prompt)
        elif self.provider == "gemini":
            return self._call_gemini(messages, tools, system_prompt)
        elif self.provider == "ollama":
            return self._call_ollama(messages, tools, system_prompt)
        elif self.provider == "bedrock":
            return self._call_bedrock(messages, tools, system_prompt)
        else:
            return self._call_offline_rule_engine(messages, tools, system_prompt)

    # ------------------ OpenAI-Compatible ------------------
    def _call_openai_compatible(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt: Optional[str],
    ) -> LLMResponse:
        api_key = self.config.get("openai_api_key", "")
        base_url = self.config.get("openai_base_url", "https://api.openai.com/v1").rstrip("/")
        endpoint = f"{base_url}/chat/completions"

        formatted_msgs = []
        if system_prompt:
            formatted_msgs.append({"role": "system", "content": system_prompt})
        formatted_msgs.extend(messages)

        payload: Dict[str, Any] = {
            "model": self.model or "gpt-4o",
            "messages": formatted_msgs,
            "temperature": 0.2,
        }

        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
            payload["tool_choice"] = "auto"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        tool_calls = []

        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                args = {}
            tool_calls.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            raw_response=data,
            provider="openai",
            model=self.model,
        )

    # ------------------ Anthropic Claude ------------------
    def _call_anthropic(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt: Optional[str],
    ) -> LLMResponse:
        api_key = self.config.get("anthropic_api_key", "")
        endpoint = "https://api.anthropic.com/v1/messages"

        # Separate system message
        anthropic_msgs = []
        for m in messages:
            if m["role"] != "system":
                anthropic_msgs.append({"role": m["role"], "content": m["content"]})

        payload: Dict[str, Any] = {
            "model": self.model or "claude-3-5-sonnet-20240620",
            "messages": anthropic_msgs,
            "max_tokens": 4096,
            "temperature": 0.2,
        }
        if system_prompt:
            payload["system"] = system_prompt

        if tools:
            payload["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t.get("parameters", {}),
                }
                for t in tools
            ]

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        content_parts = []
        tool_calls = []

        for block in data.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        arguments=block.get("input", {}),
                    )
                )

        return LLMResponse(
            content="\n".join(content_parts),
            tool_calls=tool_calls,
            raw_response=data,
            provider="anthropic",
            model=self.model,
        )

    # ------------------ Google Gemini ------------------
    def _call_gemini(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt: Optional[str],
    ) -> LLMResponse:
        api_key = self.config.get("gemini_api_key", "")
        model_name = self.model or "gemini-1.5-pro"
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": str(m["content"])}]})

        payload: Dict[str, Any] = {"contents": contents}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        cand = data.get("candidates", [{}])[0]
        parts = cand.get("content", {}).get("parts", [])
        text_out = "".join([p.get("text", "") for p in parts if "text" in p])

        return LLMResponse(
            content=text_out,
            tool_calls=[],
            raw_response=data,
            provider="gemini",
            model=model_name,
        )

    # ------------------ Local Ollama ------------------
    def _call_ollama(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt: Optional[str],
    ) -> LLMResponse:
        base = self.config.get("ollama_base_url", "http://localhost:11434").rstrip("/")
        endpoint = f"{base}/api/chat"

        ollama_msgs = []
        if system_prompt:
            ollama_msgs.append({"role": "system", "content": system_prompt})
        ollama_msgs.extend(messages)

        payload = {
            "model": self.model or "qwen2.5-coder:latest",
            "messages": ollama_msgs,
            "stream": False,
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]

        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        msg = data.get("message", {})
        content = msg.get("content", "")
        tool_calls = []
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", "call_1"),
                    name=fn.get("name", ""),
                    arguments=fn.get("arguments", {}),
                )
            )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            raw_response=data,
            provider="ollama",
            model=self.model,
        )

    # ------------------ AWS Bedrock Fallback ------------------
    def _call_bedrock(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt: Optional[str],
    ) -> LLMResponse:
        # Check if boto3 or AWS CLI is callable
        try:
            import boto3

            client = boto3.client(
                "bedrock-runtime",
                region_name=self.config.get("bedrock_region", "eu-central-1"),
            )
            bedrock_msgs = []
            for m in messages:
                if m["role"] in ["user", "assistant"]:
                    bedrock_msgs.append({
                        "role": m["role"],
                        "content": [{"text": str(m["content"])}],
                    })

            kwargs: Dict[str, Any] = {
                "modelId": self.model or self.config.get("bedrock_model_id", "eu.amazon.nova-lite-v1:0"),
                "messages": bedrock_msgs,
            }
            if system_prompt:
                kwargs["system"] = [{"text": system_prompt}]

            res = client.converse(**kwargs)
            out_text = res.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
            return LLMResponse(
                content=out_text,
                tool_calls=[],
                raw_response=res,
                provider="bedrock",
                model=self.model,
            )
        except Exception:
            return self._call_offline_rule_engine(messages, tools, system_prompt)

    # ------------------ Offline / Rule Engine Fallback ------------------
    def _call_offline_rule_engine(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt: Optional[str],
    ) -> LLMResponse:
        """Rule-based engine when no LLM API is available."""
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = str(m.get("content", ""))
                break

        low = last_user_msg.lower()
        tool_calls = []

        # Intent detection
        if any(w in low for w in ["search", "find", "where", "how", "password", "secret", "redis", "postgres", "rds"]):
            query = re.sub(r"^(search|find|lookup|show)\s+(for\s+)?", "", last_user_msg, flags=re.I).strip()
            tool_calls.append(ToolCall(id="call_auto_kb", name="search_knowledge", arguments={"query": query or last_user_msg, "limit": 4}))
            content = f"Searching knowledge base for: '{query or last_user_msg}'"

        elif any(w in low for w in ["project", "projects", "repo", "repos", "clone"]):
            if any(w in low for w in ["list", "show", "all"]):
                tool_calls.append(ToolCall(id="call_auto_proj", name="list_projects", arguments={}))
                content = "Listing all registered projects in workspace."
            else:
                # select project
                for p_id in ["itariff", "prefiler", "itopaz", "ebx", "infrastructure", "sonar", "jenkins"]:
                    if p_id in low:
                        tool_calls.append(ToolCall(id="call_auto_sel", name="select_project", arguments={"project_id": p_id}))
                        content = f"Selecting project '{p_id}'."
                        break
                if not tool_calls:
                    tool_calls.append(ToolCall(id="call_auto_proj", name="list_projects", arguments={}))
                    content = "Checking projects."

        elif any(w in low for w in ["status", "git", "branch", "diff"]):
            tool_calls.append(ToolCall(id="call_auto_git", name="git_status", arguments={}))
            content = "Checking git status for the current workspace/project."

        elif any(w in low for w in ["diag", "diagnose", "health", "check"]):
            comp = "clusters"
            for c in ["ebx", "sonar", "jenkins", "bastions", "clusters"]:
                if c in low:
                    comp = c
                    break
            tool_calls.append(ToolCall(id="call_auto_diag", name="run_diagnostic", arguments={"component": comp}))
            content = f"Running diagnostic check for: {comp}"

        elif any(w in low for w in ["env", "environment", "cluster", "account", "sit", "dev", "uat", "prod"]):
            env_target = "sit"
            for e in ["dev", "sit", "uat", "prod", "singapore", "china", "gati"]:
                if e in low:
                    env_target = e
                    break
            tool_calls.append(ToolCall(id="call_auto_env", name="get_env_summary", arguments={"environment": env_target}))
            content = f"Retrieving environment information for: {env_target}"

        else:
            # Default to knowledge search
            tool_calls.append(ToolCall(id="call_auto_default", name="search_knowledge", arguments={"query": last_user_msg, "limit": 3}))
            content = f"Consulting knowledge base for: '{last_user_msg}'"

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            raw_response={"mode": "offline-rule-engine"},
            provider="offline",
            model="rule-based-assistant",
        )


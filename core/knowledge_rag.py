#!/usr/bin/env python3
"""Knowledge Base RAG & Retrieval Engine for iTOPAZ Agent.

Integrates with canonical knowledge sources:
- knowledge-base/KNOWLEDGE-BASE.md
- infrastructure/activity-log.md
- infrastructure/environment-summaries.md
- scripts/ebx-auto-healing/README.md
- AI-INDEX.md
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Root directory of the repository
REPO_ROOT = Path(os.environ.get("ITOPAZ_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent)).resolve()

# Add scripts directory to sys.path for knowledge_sources if available
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from knowledge_sources import ROOT as KS_ROOT, sections, source_files
except ImportError:
    KS_ROOT = REPO_ROOT

    def source_files() -> List[Path]:
        candidates = [
            REPO_ROOT / "knowledge-base" / "KNOWLEDGE-BASE.md",
            REPO_ROOT / "infrastructure" / "activity-log.md",
            REPO_ROOT / "infrastructure" / "environment-summaries.md",
            REPO_ROOT / "scripts" / "ebx-auto-healing" / "README.md",
        ]
        return [p for p in candidates if p.is_file()]

    def sections(path: Path):
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        current_heading = path.name
        start_line = 1
        body_lines = []
        for idx, line in enumerate(lines, 1):
            if line.startswith("#"):
                if body_lines:
                    yield current_heading, start_line, "\n".join(body_lines)
                    body_lines = []
                current_heading = line.lstrip("#").strip()
                start_line = idx
            else:
                body_lines.append(line)
        if body_lines:
            yield current_heading, start_line, "\n".join(body_lines)


class KnowledgeRetriever:
    """Fast SQLite FTS5 + Semantic retriever for iTOPAZ knowledge base."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or REPO_ROOT
        self._db: Optional[sqlite3.Connection] = None
        self._source_signature = None

    def _ensure_index(self) -> sqlite3.Connection:
        # Check if source files modified
        files = source_files()
        signature = tuple((str(f), f.stat().st_mtime_ns, f.stat().st_size)
                          for f in files if f.exists())

        if self._db is not None and signature == self._source_signature:
            return self._db

        db = sqlite3.connect(":memory:")
        db.execute(
            "CREATE VIRTUAL TABLE docs USING fts5("
            "path UNINDEXED, heading, content, line UNINDEXED, tokenize='unicode61'"
            ")"
        )
        for path in files:
            if not path.is_file():
                continue
            rel = str(path.relative_to(self.root))
            for heading, line, body in sections(path):
                db.execute(
                    "INSERT INTO docs(path, heading, content, line) VALUES (?, ?, ?, ?)",
                    (rel, heading, body, line),
                )
        if self._db is not None:
            self._db.close()
        self._db = db
        self._source_signature = signature
        return self._db

    def search(
        self,
        query: str,
        limit: int = 5,
        source: Optional[str] = None,
        context_chars: int = 1500,
    ) -> List[Dict[str, Any]]:
        """Search canonical knowledge base using SQLite FTS5."""
        db = self._ensure_index()
        terms = re.findall(r"[\w]+", query, flags=re.UNICODE)
        if not terms:
            return []

        quoted = ['"' + t.replace('"', '""') + '"' for t in terms]
        date_hint = re.search(r"\d{4}-\d{2}-\d{2}", query)
        hint = date_hint.group() if date_hint else ""

        statement = (
            "SELECT path, heading, line, snippet(docs, 2, '', '', ' ... ', 24), bm25(docs, 0, 5, 1), content "
            "FROM docs WHERE docs MATCH ? AND (? IS NULL OR path = ?) "
            "ORDER BY (CASE WHEN ? != '' AND (instr(path, ?) > 0 OR instr(heading, ?) > 0) THEN -100 ELSE 0 END) + bm25(docs, 0, 5, 1) LIMIT ?"
        )

        mode = "all_terms"
        rows = db.execute(
            statement,
            (" AND ".join(quoted), source, source, hint, hint, hint, limit),
        ).fetchall()

        if not rows and len(quoted) > 1:
            mode = "any_term"
            rows = db.execute(
                statement,
                (" OR ".join(quoted), source, source, hint, hint, hint, limit),
            ).fetchall()

        results = []
        for path, heading, line, excerpt, score, content in rows:
            line_int = int(line)
            end_line = line_int + len(content.splitlines()) - 1
            res: Dict[str, Any] = {
                "path": path,
                "heading": heading,
                "line": line_int,
                "end_line": end_line,
                "excerpt": excerpt,
                "score": round(-score, 4),
                "match_mode": mode,
            }
            if context_chars > 0:
                res["content"] = content[:context_chars]
                res["truncated"] = len(content) > context_chars
            results.append(res)
        return results

    def query_semantic(self, query: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Query FAISS semantic index if available, falling back to full-text search."""
        query_script = self.root / "scripts" / "query_knowledge.py"
        if not query_script.is_file():
            return None

        try:
            res = subprocess.run(
                [sys.executable, str(query_script), "--json", "--top", str(limit), query],
                cwd=str(self.root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return data.get("results", [])
        except Exception:
            pass
        return None

    def get_context_for_prompt(self, query: str, max_results: int = 4, max_chars: int = 3500) -> str:
        """Format top relevant knowledge chunks into prompt context for LLM reasoning."""
        if max_chars <= 0 or max_results <= 0:
            return ""
        results = self.search(query, limit=max_results, context_chars=0)
        if not results:
            return "No matching knowledge base entries found."[:max_chars]

        chunks = []
        total_len = 0
        seen = set()
        for r in results:
            identity = (r['path'], r['line'])
            if identity in seen:
                continue
            seen.add(identity)
            chunk = (
                f"### [{r['path']}#L{r['line']}-{r['end_line']}] {r['heading']}\n"
                f"{r.get('content', r.get('excerpt', ''))}\n"
            )
            remaining = max_chars - total_len - (1 if chunks else 0)
            if remaining <= 0:
                break
            chunk = chunk[:remaining]
            total_len += len(chunk) + (1 if chunks else 0)
            chunks.append(chunk)

        return "\n".join(chunks)

    def get_environment_overview(self) -> Dict[str, Any]:
        """Return quick reference of AWS accounts, clusters, and bastions."""
        return {
            "aws_accounts": {
                "DEV EU": {"account_id": "439891535362", "region": "eu-central-1", "cluster": "euc1-itopaz-dev-eks", "bastion": "10.100.145.118"},
                "SIT EU": {"account_id": "464134132424", "region": "eu-central-1", "cluster": "euc1-itopaz-sit-eks", "bastion": "10.100.208.17"},
                "UAT EU": {"account_id": "581621506601", "region": "eu-central-1", "cluster": "euc1-itopaz-uat-eks", "bastion": "10.100.176.4"},
                "PROD EU": {"account_id": "965031587107", "region": "eu-central-1", "cluster": "euc1-itopaz-prod-eks", "bastion": "10.100.110.76"},
                "SIT SG": {"account_id": "464134132424", "region": "ap-southeast-1", "cluster": "apse1-itopaz-sit-eks", "bastion": "10.151.4.165"},
                "GATI EBX": {"account_id": "637423558749", "region": "ap-south-1", "cluster": "N/A (EC2)", "bastion": "10.100.208.17"},
            },
            "core_servers": {
                "jenkins_master": {"ip": "10.100.95.13", "instance": "i-0cdcce39da9444d74", "region": "eu-central-1"},
                "sonarqube": {"ip": "10.100.95.54", "instance": "i-0cd1ab8b0d9247ef4", "region": "eu-central-1"},
                "sit_jump": {"instance": "i-0bd3314ea08e6fb27", "method": "SSM"},
            },
            "canonical_docs": [
                "knowledge-base/KNOWLEDGE-BASE.md",
                "infrastructure/activity-log.md",
                "infrastructure/environment-summaries.md",
                "AI-INDEX.md",
            ],
        }


# Global singleton instance
retriever = KnowledgeRetriever()


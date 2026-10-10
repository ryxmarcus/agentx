#!/usr/bin/env python3
"""Credentials and Secrets Manager for iTOPAZ Agent.

Manages:
1. Bitbucket access tokens & API authentication
2. SSH keys for all environments (dev, sit, uat, prod, mdm, intranet, shared)
3. Authenticated Git URLs for Bitbucket operations
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(os.environ.get("ITOPAZ_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent)).resolve()


class CredentialsManager:
    """Manages Bitbucket authentication and environment SSH keys."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or REPO_ROOT
        self.agent_secrets_dir = self.root / "agent" / "secrets"
        self.infra_secrets_dir = self.root / "infrastructure" / "secrets"

    def get_bitbucket_token(self) -> Optional[str]:
        """Load Bitbucket token from secrets files or environment."""
        # 1. Environment variable
        if os.environ.get("BITBUCKET_TOKEN"):
            return os.environ["BITBUCKET_TOKEN"].strip()

        # 2. agent/secrets/bitbucket_token.txt
        p1 = self.agent_secrets_dir / "bitbucket_token.txt"
        if p1.is_file():
            content = p1.read_text(encoding="utf-8").strip()
            if content:
                # First line is the token
                return content.splitlines()[0].strip()

        # 3. infrastructure/secrets/bitbucket_token.txt
        p2 = self.infra_secrets_dir / "bitbucket_token.txt"
        if p2.is_file():
            content = p2.read_text(encoding="utf-8").strip()
            if content:
                return content.splitlines()[0].strip()

        return None

    def get_bitbucket_credentials(self) -> Dict[str, str]:
        """Load parsed Bitbucket credentials (org ID, API key, etc.)."""
        result = {}
        token = self.get_bitbucket_token()
        if token:
            result["token"] = token

        candidates = [
            self.agent_secrets_dir / "bitbucket_credentials.txt",
            self.infra_secrets_dir / "bitbucket_credentials.txt",
        ]
        for c in candidates:
            if c.is_file():
                for line in c.read_text(encoding="utf-8").splitlines():
                    if "Organization ID" in line and "-" in line:
                        result["org_id"] = line.split("-", 1)[1].strip()
                    elif "API key" in line and "-" in line:
                        result["api_key"] = line.split("-", 1)[1].strip()
                break
        return result

    def get_authenticated_git_url(self, repo_slug_or_url: str) -> str:
        """Construct authenticated Bitbucket git URL using x-token-auth."""
        token = self.get_bitbucket_token()
        if not token:
            raise ValueError("Bitbucket token not found in secrets or environment.")

        # If already a bitbucket URL
        slug = repo_slug_or_url
        if "bitbucket.org" in slug:
            # extract path like allcargoecu/itariff-k8s-repo.git
            parts = slug.split("bitbucket.org/")[-1].lstrip("/")
            slug = parts.replace(".git", "")

        if not slug.startswith("allcargoecu/"):
            slug = f"allcargoecu/{slug}"

        return f"https://x-token-auth:{token}@bitbucket.org/{slug}.git"

    def list_ssh_keys(self) -> Dict[str, List[str]]:
        """List all available SSH keys organized by environment."""
        keys_dirs = [
            self.agent_secrets_dir / "keys",
            self.infra_secrets_dir / "keys",
        ]
        found: Dict[str, List[str]] = {}

        for kdir in keys_dirs:
            if not kdir.is_dir():
                continue
            for item in kdir.rglob("*.pem"):
                env = item.parent.name if item.parent != kdir else "root"
                found.setdefault(env, []).append(item.name)

        return {k: sorted(list(set(v))) for k, v in found.items()}

    def get_ssh_key_path(self, environment: str, key_name: Optional[str] = None) -> Optional[Path]:
        """Find the exact path to a requested SSH key."""
        keys_dirs = [
            self.agent_secrets_dir / "keys",
            self.infra_secrets_dir / "keys",
        ]
        env_lower = environment.lower()

        for kdir in keys_dirs:
            if not kdir.is_dir():
                continue
            # Search in env subfolder first
            env_folder = kdir / env_lower
            if env_folder.is_dir():
                pem_files = list(env_folder.glob("*.pem"))
                if key_name:
                    for f in pem_files:
                        if key_name.lower() in f.name.lower():
                            return f
                elif pem_files:
                    return pem_files[0]

            # Search globally in keys
            for f in kdir.rglob("*.pem"):
                if key_name and key_name.lower() in f.name.lower():
                    return f
                if env_lower in f.parent.name.lower() or env_lower in f.name.lower():
                    return f

        return None

    def query_bitbucket_api(
        self, endpoint: str, workspace: str = "allcargoecu", params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Query the official Bitbucket Cloud REST API v2.0."""
        token = self.get_bitbucket_token()
        if not token:
            return {"error": "Bitbucket token not found."}

        ep = endpoint.lstrip("/")
        if not ep.startswith("repositories"):
            ep = f"repositories/{workspace}/{ep}"

        url = f"https://api.bitbucket.org/2.0/{ep}"
        if params:
            query_str = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_str}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"status": "success", "data": data}
        except urllib.error.HTTPError as e:
            return {"status": "error", "code": e.code, "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global singleton instance
credentials_manager = CredentialsManager()


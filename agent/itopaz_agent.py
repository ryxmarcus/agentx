#!/usr/bin/env python3
"""Compatibility entry point for the canonical repository-root CLI."""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    runpy.run_path(str(ROOT / "agentx.py"), run_name="__main__")

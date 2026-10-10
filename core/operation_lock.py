"""Default-locked mutation guard for agent tools, not an OS security boundary."""
import json
import os
import shlex
from pathlib import Path


def is_locked():
    root = Path(os.environ.get("ITOPAZ_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent))
    try:
        data = json.loads((root / ".agent-operation-lock.json").read_text(encoding="utf-8"))
        return data.get("locked") is not False
    except (OSError, ValueError, AttributeError):
        return True


def require_unlocked():
    if is_locked():
        raise PermissionError("Operation locked: patching, writing, deletion and unrestricted commands require an operator to unlock .agent-operation-lock.json outside the agent.")


def check_command(command):
    if not is_locked():
        return
    if any(c in command for c in ";&|><`$\n\r"):
        raise PermissionError("Operation locked: shell composition is disabled.")
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise PermissionError("Operation locked: invalid command.") from exc
    if not tokens:
        raise PermissionError("Operation locked: empty command.")
    # Accept only narrow inspection commands; arbitrary interpreters/scripts can mutate files.
    executable, args = tokens[0], tokens[1:]
    allowed = executable in ("pwd", "whoami", "hostname") and not args
    if executable == "git":
        if args[:1] == ["-C"] and len(args) >= 3:
            args = args[2:]
        allowed = bool(args) and (
            args[0] in ("status", "log", "show", "diff", "rev-parse")
            or args == ["branch", "--show-current"]
        ) and not any(a.startswith(("--output", "--ext-diff", "--textconv", "--exec", "--config")) for a in args)
    if not allowed:
        raise PermissionError("Operation locked: command is outside the inspection allowlist; patch/delete commands and interpreters are blocked.")

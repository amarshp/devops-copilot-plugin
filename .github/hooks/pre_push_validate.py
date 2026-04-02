#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PUSH_PATTERN = re.compile(r"push_and_trigger\.py|git push", re.IGNORECASE)


def _emit(decision: str, reason: str | None = None) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
        }
    }
    if reason:
        payload["hookSpecificOutput"]["permissionDecisionReason"] = reason
    print(json.dumps(payload))


def _staged_yaml_files(cwd: Path) -> tuple[list[str] | None, str | None]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return None, f"Push detected, but git is unavailable for validation: {exc}"

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        return None, f"Push detected, but staged files could not be inspected: {stderr}"

    files = [line.strip() for line in result.stdout.splitlines() if re.search(r"\.(yml|yaml)$", line.strip(), re.IGNORECASE)]
    return files, None


def _validate_yaml_files(cwd: Path, files: list[str]) -> tuple[bool, str | None]:
    validator = cwd / ".github" / "skills" / "j2gl-migrate" / "scripts" / "validate_yaml.py"
    if not validator.exists():
        return False, f"Push detected, but {validator} was not found."

    for file_path in files:
        result = subprocess.run(
            [sys.executable, str(validator), file_path],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stdout or result.stderr).strip().splitlines()
            suffix = f" First message: {detail[0]}" if detail else ""
            return False, f"Validation failed for {file_path}.{suffix}"
    return True, None


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        _emit("allow")
        return 0

    if not PUSH_PATTERN.search(raw):
        _emit("allow")
        return 0

    cwd = Path.cwd()
    files, error = _staged_yaml_files(cwd)
    if error:
        _emit("ask", error)
        return 0
    if not files:
        _emit("allow")
        return 0

    valid, reason = _validate_yaml_files(cwd, files)
    if valid:
        _emit("allow")
    else:
        _emit("ask", reason or "Push detected. Run validate_yaml.py before pushing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
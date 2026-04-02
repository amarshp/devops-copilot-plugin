"""
winrm_explorer.py — Read-only WinRM utility for browsing a Windows runner.

The runner exposes WinRM on port 5985. Credentials are read from the project
.env file via the shared config loader (RUNNER_HOST, RUNNER_USER, RUNNER_PASS,
RUNNER_PORT). NEVER write, create, or delete anything on the remote host.

CLI:
    python winrm_explorer.py --path "C:\\Jenkins"
    python winrm_explorer.py --path "C:\\" --depth 2
    python winrm_explorer.py --cmd "Get-Process"
    python winrm_explorer.py --env WORKSPACE_HOME
    python winrm_explorer.py --exists "C:\\Jenkins\\workspace\\MyJob"
    python winrm_explorer.py --find "C:\\Jenkins" "*.log"

Python API:
    from winrm_explorer import ls, tree, run_cmd, exists, get_env, find
    print(ls("C:\\Jenkins\\workspace"))
    print(tree("C:\\", depth=2))
    print(run_cmd("where python"))
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "devops-setup" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import config

try:
    from dotenv import load_dotenv

    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
except ImportError:
    pass


RUNNER_HOST_RESOLVED = config.RUNNER_HOST or os.environ.get("RUNNER_HOST") or os.environ.get("EC2_HOST", "")
RUNNER_USER_RESOLVED = config.RUNNER_USER or os.environ.get("RUNNER_USER") or os.environ.get("EC2_USER", "")
RUNNER_PASS_RESOLVED = config.RUNNER_PASS or os.environ.get("RUNNER_PASS") or os.environ.get("EC2_PASS", "")
RUNNER_PORT_RESOLVED = int(config.RUNNER_PORT or os.environ.get("RUNNER_PORT") or os.environ.get("EC2_PORT", "5985"))
RUNNER_TRANSPORT = os.environ.get("EC2_TRANSPORT", "ntlm")


def _get_session():
    """Return a pywinrm Session connected to the configured runner host."""
    try:
        import winrm
    except ImportError:
        print(
            "[winrm_explorer] pywinrm is not installed.\n"
            "  Install it with:  pip install pywinrm\n"
            "  Or:               pip install -r .github/requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    return winrm.Session(
        target=f"http://{RUNNER_HOST_RESOLVED}:{RUNNER_PORT_RESOLVED}/wsman",
        auth=(RUNNER_USER_RESOLVED, RUNNER_PASS_RESOLVED),
        transport=RUNNER_TRANSPORT,
        read_timeout_sec=30,
        operation_timeout_sec=25,
    )


def _run_remote(cmd: str) -> tuple[str, str, int]:
    """Execute a PowerShell *cmd* on the remote server via WinRM.

    Returns (stdout, stderr, exit_code).
    The command is run inside a PowerShell session so both PS cmdlets
    and legacy cmd.exe constructs (via cmd /c) are supported.
    """
    session = _get_session()
    result = session.run_ps(cmd)
    stdout = result.std_out.decode(errors="replace")
    # Filter out benign WinRM PowerShell session initialisation noise
    stderr_lines = [
        ln for ln in result.std_err.decode(errors="replace").splitlines()
        if "InitializeDefaultDrives" not in ln
    ]
    stderr = "\n".join(stderr_lines)
    return stdout, stderr, result.status_code


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_cmd(cmd: str, *, silent: bool = False) -> str:
    """Run any read-only command on the remote runner and return its stdout.

    Raises RuntimeError if the command exits non-zero (unless *silent* is True).
    """
    out, err, code = _run_remote(cmd)
    if code != 0 and not silent:
        raise RuntimeError(
            f"Remote command failed (exit {code}):\n  cmd : {cmd}\n  stderr: {err.strip()}"
        )
    return out


def ls(path: str) -> str:
    """List the immediate children of *path* on the remote runner."""
    cmd = f'Get-ChildItem -LiteralPath "{path}" -Name -ErrorAction Stop'
    out, err, code = _run_remote(cmd)
    if code != 0:
        return f"[ls ERROR] path={path!r}  stderr={err.strip()!r}"
    return out.strip() or "(empty directory)"


def tree(path: str, *, depth: int = 2) -> str:
    """Return an ASCII-tree of *path* up to *depth* levels deep."""
    if depth == 1:
        return f"{path}\n" + "\n".join(
            f"  {line}" for line in ls(path).splitlines()
        )

    # PowerShell recursive listing filtered by depth
    cmd = (
        f'Get-ChildItem -LiteralPath "{path}" -Recurse -ErrorAction SilentlyContinue'
        f' | Select-Object -ExpandProperty FullName'
    )
    out, err, code = _run_remote(cmd)
    if code != 0:
        return f"[tree ERROR] path={path!r}  stderr={err.strip()!r}"

    base_depth = path.replace("/", "\\").rstrip("\\").count("\\")
    lines = [path]
    for entry in out.splitlines():
        entry = entry.strip()
        if not entry:
            continue
        entry_depth = entry.replace("/", "\\").rstrip("\\").count("\\")
        if entry_depth <= base_depth + depth:
            indent = "  " * (entry_depth - base_depth)
            lines.append(f"{indent}{os.path.basename(entry)}")
    return "\n".join(lines)


def exists(path: str) -> bool:
    """Return True if *path* exists on the remote runner (file or directory)."""
    cmd = f'Test-Path -LiteralPath "{path}"'
    out, _err, _code = _run_remote(cmd)
    return "True" in out


def find(root: str, pattern: str) -> str:
    """Find files/dirs under *root* matching *pattern*."""
    cmd = (
        f'Get-ChildItem -LiteralPath "{root}" -Recurse -Filter "{pattern}"'
        f' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName'
    )
    out, err, code = _run_remote(cmd)
    if code != 0 or not out.strip():
        return f"(no matches for {pattern!r} under {root!r})"
    return out.strip()


def env_all() -> dict[str, str]:
    """Return all environment variables visible on the remote runner."""
    cmd = 'Get-ChildItem Env: | ForEach-Object { $_.Name + "=" + $_.Value }'
    out, _err, _code = _run_remote(cmd)
    result: dict[str, str] = {}
    for line in out.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def get_env(var: str) -> str:
    """Return the value of a single environment variable from the remote runner."""
    cmd = f'$env:{var}'
    out, _err, _code = _run_remote(cmd)
    return out.strip()


# Backward-compat aliases (existing callers may use ec2_* names)
ec2_run = run_cmd
ec2_ls = ls
ec2_tree = tree
ec2_exists = exists
ec2_find = find
ec2_env = env_all
ec2_get_env = get_env


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only WinRM explorer for a Windows runner (port 5985).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              python winrm_explorer.py --path "C:\\Jenkins\\workspace"
              python winrm_explorer.py --path "C:\\" --depth 2
              python winrm_explorer.py --cmd "Get-Process"
              python winrm_explorer.py --env WORKSPACE_HOME
              python winrm_explorer.py --exists "C:\\Jenkins\\workspace\\MyJob"
            """
        ),
    )
    parser.add_argument("--path", metavar="PATH", help="Directory to list on the runner")
    parser.add_argument("--depth", type=int, default=1, help="Tree depth (default 1, list only)")
    parser.add_argument("--cmd", metavar="COMMAND", help="Run an arbitrary read-only command")
    parser.add_argument("--env", metavar="VAR", help="Print value of an env variable (or all if VAR='*')")
    parser.add_argument("--exists", metavar="PATH", help="Check whether a path exists")
    parser.add_argument("--find", nargs=2, metavar=("ROOT", "PATTERN"), help="Find files matching PATTERN under ROOT")
    args = parser.parse_args()

    if args.path:
        if args.depth > 1:
            print(tree(args.path, depth=args.depth))
        else:
            print(ls(args.path))

    elif args.cmd:
        out, err, code = _run_remote(args.cmd)
        if out:
            print(out)
        if err:
            print("[stderr]", err, file=sys.stderr)
        sys.exit(code)

    elif args.env:
        if args.env == "*":
            for k, v in sorted(env_all().items()):
                print(f"{k}={v}")
        else:
            print(get_env(args.env))

    elif args.exists:
        found = exists(args.exists)
        print("EXISTS" if found else "NOT FOUND")
        sys.exit(0 if found else 1)

    elif args.find:
        root, pattern = args.find
        print(find(root, pattern))

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()

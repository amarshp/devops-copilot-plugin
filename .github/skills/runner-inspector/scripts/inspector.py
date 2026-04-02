#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "devops-setup" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import config  # noqa: E402


def _impl_module():
    protocol = (config.RUNNER_PROTOCOL or "winrm").lower()
    if protocol == "ssh":
        return importlib.import_module("ssh_explorer")
    return importlib.import_module("winrm_explorer")


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified runner inspector")
    parser.add_argument("--cmd")
    parser.add_argument("--path")
    parser.add_argument("--exists")
    parser.add_argument("--find", nargs=2, metavar=("ROOT", "PATTERN"))
    parser.add_argument("--env")
    args = parser.parse_args()

    impl = _impl_module()

    if args.cmd:
        out, err, code = impl.run_cmd(args.cmd) if hasattr(impl, "run_cmd") else impl._run_remote(args.cmd)
        if out:
            print(out)
        if err:
            print(err, file=sys.stderr)
        return code

    if args.path:
        print(impl.ls(args.path)); return 0
    if args.exists:
        ok = impl.exists(args.exists)
        print("EXISTS" if ok else "NOT FOUND")
        return 0 if ok else 1
    if args.find:
        root, pattern = args.find
        print(impl.find(root, pattern))
        return 0
    if args.env:
        print(impl.get_env(args.env))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

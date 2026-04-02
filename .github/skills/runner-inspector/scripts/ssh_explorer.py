#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import paramiko

_SHARED = Path(__file__).resolve().parents[2] / "devops-setup" / "scripts"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import config  # noqa: E402


def _connect() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=config.RUNNER_HOST,
        port=config.RUNNER_PORT,
        username=config.RUNNER_USER,
        password=config.RUNNER_PASS,
        timeout=20,
    )
    return client


def run_cmd(cmd: str) -> tuple[str, str, int]:
    client = _connect()
    try:
        _in, out, err = client.exec_command(cmd)
        code = out.channel.recv_exit_status()
        return out.read().decode(errors="replace"), err.read().decode(errors="replace"), code
    finally:
        client.close()


def ls(path: str) -> str:
    out, err, code = run_cmd(f'ls -la "{path}"')
    return out if code == 0 else err


def exists(path: str) -> bool:
    _out, _err, code = run_cmd(f'test -e "{path}"')
    return code == 0


def find(root: str, pattern: str) -> str:
    out, err, code = run_cmd(f'find "{root}" -name "{pattern}"')
    return out if code == 0 else err


def get_env(var: str) -> str:
    out, err, code = run_cmd(f'printenv "{var}"')
    return out if code == 0 else err


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only SSH explorer")
    parser.add_argument("--cmd")
    parser.add_argument("--path")
    parser.add_argument("--exists")
    parser.add_argument("--find", nargs=2, metavar=("ROOT", "PATTERN"))
    parser.add_argument("--env")
    args = parser.parse_args()

    if args.cmd:
        out, err, code = run_cmd(args.cmd)
        if out:
            print(out)
        if err:
            print(err, file=sys.stderr)
        return code
    if args.path:
        print(ls(args.path)); return 0
    if args.exists:
        ok = exists(args.exists); print("EXISTS" if ok else "NOT FOUND"); return 0 if ok else 1
    if args.find:
        print(find(args.find[0], args.find[1])); return 0
    if args.env:
        print(get_env(args.env)); return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

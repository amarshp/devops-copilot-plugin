#!/usr/bin/env python3
"""
setup_wizard.py — Interactive setup for the DevOps Copilot Plugin.

Prompts for all required credentials, tests each connection, and writes
a .env file to the project root.  Run once per project, then teammates
can clone the .github/ folder and point to the same .env.

Usage:
    python setup_wizard.py [--env-path PATH]
    python setup_wizard.py --check        # Test existing .env without re-prompting
    python setup_wizard.py --help
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ask(label: str, default: str = "", secret: bool = False) -> str:
    prompt = f"  {label}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "
    if secret:
        value = getpass.getpass(prompt).strip()
    else:
        value = input(prompt).strip()
    return value or default


def _header(text: str) -> None:
    width = 60
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)


def _ok(msg: str) -> None:
    print(f"  [OK]  {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def _skip(msg: str) -> None:
    print(f"  [SKIP] {msg}")


# ---------------------------------------------------------------------------
# Connection tests
# ---------------------------------------------------------------------------

def _test_gitlab(url: str, token: str, project_id: str) -> bool:
    try:
        import requests
        r = requests.get(
            f"{url.rstrip('/')}/api/v4/projects/{project_id}",
            headers={"PRIVATE-TOKEN": token},
            timeout=15,
            verify=False,
        )
        if r.status_code == 200:
            name = r.json().get("name_with_namespace", project_id)
            _ok(f"GitLab project: {name}")
            return True
        _fail(f"GitLab API returned HTTP {r.status_code}: {r.text[:200]}")
        return False
    except Exception as exc:
        _fail(f"GitLab connection error: {exc}")
        return False


def _test_jenkins(url: str, user: str, token: str) -> bool:
    if not url:
        _skip("Jenkins URL not provided — skipping Jenkins test")
        return True
    try:
        import requests
        r = requests.head(
            f"{url.rstrip('/')}/api/json",
            auth=(user, token),
            timeout=15,
            verify=False,
        )
        if r.status_code in (200, 403):  # 403 means auth failed but server is reachable
            if r.status_code == 200:
                _ok(f"Jenkins reachable and authenticated at {url}")
                return True
            _fail(f"Jenkins reachable but authentication failed (HTTP 403). Check JENKINS_USER / JENKINS_TOKEN.")
            return False
        _fail(f"Jenkins returned HTTP {r.status_code}")
        return False
    except Exception as exc:
        _fail(f"Jenkins connection error: {exc}")
        return False


def _test_runner(host: str, user: str, password: str, port: int, protocol: str) -> bool:
    if not host:
        _skip("RUNNER_HOST not provided — skipping runner test")
        return True
    if protocol == "winrm":
        try:
            import winrm  # type: ignore[import]
            session = winrm.Session(
                f"http://{host}:{port}/wsman",
                auth=(user, password),
                transport="ntlm",
            )
            result = session.run_cmd("echo ok")
            if b"ok" in result.std_out:
                _ok(f"WinRM runner reachable at {host}:{port}")
                return True
            _fail(f"WinRM runner returned unexpected output: {result.std_out!r}")
            return False
        except ImportError:
            _skip("pywinrm not installed — skipping WinRM runner test (pip install pywinrm)")
            return True
        except Exception as exc:
            _fail(f"WinRM runner error: {exc}")
            return False
    elif protocol == "ssh":
        try:
            import paramiko  # type: ignore[import]
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host, port=port, username=user, password=password, timeout=15)
            _, stdout, _ = client.exec_command("echo ok")
            out = stdout.read().decode().strip()
            client.close()
            if "ok" in out:
                _ok(f"SSH runner reachable at {host}:{port}")
                return True
            _fail(f"SSH runner returned unexpected output: {out!r}")
            return False
        except ImportError:
            _skip("paramiko not installed — skipping SSH runner test (pip install paramiko)")
            return True
        except Exception as exc:
            _fail(f"SSH runner error: {exc}")
            return False
    _skip(f"Unknown protocol '{protocol}' — skipping runner test")
    return True


def _test_llm(token: str, model: str, url: str) -> bool:
    if not token:
        _skip("COPILOT_TOKEN not provided — skipping LLM test")
        return True
    try:
        import requests
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "Say OK"}]},
            timeout=30,
        )
        if r.status_code == 200:
            _ok(f"LLM endpoint reachable, model: {model}")
            return True
        _fail(f"LLM endpoint returned HTTP {r.status_code}: {r.text[:200]}")
        return False
    except Exception as exc:
        _fail(f"LLM connection error: {exc}")
        return False


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------

def run_wizard(env_path: Path) -> dict[str, str]:
    existing: dict[str, str] = {}
    if env_path.exists():
        print(f"\nFound existing .env at {env_path} — pre-filling defaults from it.")
        from dotenv import dotenv_values
        existing = dict(dotenv_values(env_path))  # type: ignore[arg-type]

    def _e(key: str) -> str:
        return existing.get(key, "")

    _header("DevOps Copilot Plugin — Setup Wizard")
    print("\nPress Enter to keep the current value shown in [brackets].")
    print("Tokens and passwords are entered silently.\n")

    values: dict[str, str] = {}

    # GitLab
    _header("1 / 4 — GitLab")
    values["GITLAB_URL"] = _ask("GitLab base URL", _e("GITLAB_URL") or "https://gitlab.com")
    values["GITLAB_TOKEN"] = _ask("GitLab Personal Access Token (api scope)", _e("GITLAB_TOKEN"), secret=True)
    values["GITLAB_PROJECT_ID"] = _ask("GitLab project ID or namespace/project", _e("GITLAB_PROJECT_ID"))
    values["GITLAB_BRANCH"] = _ask("Default branch to push/trigger", _e("GITLAB_BRANCH") or "main")

    # Jenkins
    _header("2 / 4 — Jenkins (leave blank to skip)")
    values["JENKINS_ROOT_URL"] = _ask("Root pipeline job URL", _e("JENKINS_ROOT_URL"))
    values["JENKINS_USER"] = _ask("Jenkins username", _e("JENKINS_USER"))
    values["JENKINS_TOKEN"] = _ask("Jenkins API token", _e("JENKINS_TOKEN"), secret=True)
    # Derive JENKINS_URL from ROOT_URL (scheme + host + port only)
    if values["JENKINS_ROOT_URL"]:
        from urllib.parse import urlparse as _urlparse
        _p = _urlparse(values["JENKINS_ROOT_URL"])
        values["JENKINS_URL"] = f"{_p.scheme}://{_p.netloc}"
    else:
        values["JENKINS_URL"] = ""

    # Runner
    _header("3 / 4 — Build Runner (leave blank to skip)")
    values["RUNNER_HOST"] = _ask("Runner host / IP", _e("RUNNER_HOST") or _e("EC2_HOST"))
    values["RUNNER_USER"] = _ask("Runner username", _e("RUNNER_USER") or _e("EC2_USER"))
    values["RUNNER_PASS"] = _ask("Runner password", _e("RUNNER_PASS") or _e("EC2_PASS"), secret=True)
    values["RUNNER_PROTOCOL"] = _ask("Protocol [winrm/ssh]", _e("RUNNER_PROTOCOL") or "winrm")
    default_port = "5985" if values["RUNNER_PROTOCOL"] == "winrm" else "22"
    values["RUNNER_PORT"] = _ask(
        f"Runner port",
        _e("RUNNER_PORT") or _e("EC2_PORT") or default_port,
    )

    # LLM
    _header("4 / 4 — GitHub Copilot LLM")
    values["COPILOT_TOKEN"] = _ask("Copilot API token (ghp_...)", _e("COPILOT_TOKEN"), secret=True)
    values["COPILOT_MODEL"] = _ask("Model name", _e("COPILOT_MODEL") or "gpt-4.1")
    values["COPILOT_CHAT_URL"] = _ask(
        "Chat completions URL",
        _e("COPILOT_CHAT_URL") or "https://api.business.githubcopilot.com/chat/completions",
    )

    return values


# ---------------------------------------------------------------------------
# Connection verification
# ---------------------------------------------------------------------------

def verify(values: dict[str, str]) -> bool:
    _header("Testing connections…")
    all_ok = True

    missing_gitlab = [
        key for key in ("GITLAB_URL", "GITLAB_TOKEN", "GITLAB_PROJECT_ID")
        if not (values.get(key) or "").strip()
    ]
    if missing_gitlab:
        _fail(
            "Missing required GitLab settings in .env: "
            + ", ".join(missing_gitlab)
        )
        all_ok = False
    else:
        all_ok &= _test_gitlab(
            values.get("GITLAB_URL", ""),
            values.get("GITLAB_TOKEN", ""),
            values.get("GITLAB_PROJECT_ID", ""),
        )
    # Auto-derive JENKINS_URL from JENKINS_ROOT_URL if not explicitly set
    jenkins_url = values.get("JENKINS_URL") or ""
    if not jenkins_url:
        root_url = values.get("JENKINS_ROOT_URL") or ""
        if root_url:
            from urllib.parse import urlparse as _urlparse
            _p = _urlparse(root_url)
            jenkins_url = f"{_p.scheme}://{_p.netloc}"
    all_ok &= _test_jenkins(
        jenkins_url,
        values.get("JENKINS_USER") or "",
        values.get("JENKINS_TOKEN") or "",
    )
    all_ok &= _test_runner(
        values.get("RUNNER_HOST") or "",
        values.get("RUNNER_USER") or "",
        values.get("RUNNER_PASS") or "",
        int(values.get("RUNNER_PORT") or "5985"),
        values.get("RUNNER_PROTOCOL") or "winrm",
    )
    all_ok &= _test_llm(
        values.get("COPILOT_TOKEN") or "",
        values.get("COPILOT_MODEL") or "gpt-4.1",
        values.get("COPILOT_CHAT_URL") or "https://api.business.githubcopilot.com/chat/completions",
    )
    return all_ok


# ---------------------------------------------------------------------------
# Write .env
# ---------------------------------------------------------------------------

def write_env(values: dict[str, str], env_path: Path) -> None:
    lines = [
        "# DevOps Copilot Plugin — generated by setup_wizard.py",
        "# DO NOT commit this file to version control.",
        "",
        "# GitLab",
        f'GITLAB_URL={values["GITLAB_URL"]}',
        f'GITLAB_TOKEN={values["GITLAB_TOKEN"]}',
        f'GITLAB_PROJECT_ID={values["GITLAB_PROJECT_ID"]}',
        f'GITLAB_BRANCH={values["GITLAB_BRANCH"]}',
        "",
        "# Jenkins (optional)",
        f'JENKINS_URL={values.get("JENKINS_URL", "")}',
        f'JENKINS_ROOT_URL={values.get("JENKINS_ROOT_URL", "")}',
        f'JENKINS_USER={values.get("JENKINS_USER", "")}',
        f'JENKINS_TOKEN={values.get("JENKINS_TOKEN", "")}',
        "",
        "# Build runner (optional)",
        f'RUNNER_HOST={values.get("RUNNER_HOST", "")}',
        f'RUNNER_USER={values.get("RUNNER_USER", "")}',
        f'RUNNER_PASS={values.get("RUNNER_PASS", "")}',
        f'RUNNER_PORT={values.get("RUNNER_PORT", "5985")}',
        f'RUNNER_PROTOCOL={values.get("RUNNER_PROTOCOL", "winrm")}',
        "",
        "# GitHub Copilot LLM",
        f'COPILOT_TOKEN={values.get("COPILOT_TOKEN", "")}',
        f'COPILOT_MODEL={values.get("COPILOT_MODEL", "gpt-4.1")}',
        f'COPILOT_CHAT_URL={values.get("COPILOT_CHAT_URL", "")}',
    ]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n  .env written to: {env_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="DevOps Copilot Plugin setup wizard.")
    parser.add_argument(
        "--env-path",
        default=None,
        help="Path to write the .env file (default: project root, searching up from this script).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Test connections using existing .env without re-prompting.",
    )
    args = parser.parse_args()

    # Determine .env path
    if args.env_path:
        env_path = Path(args.env_path)
    else:
        # Write to first folder containing a .env, else project root (4 levels up from scripts/)
        from pathlib import Path as _P
        here = _P(__file__).resolve().parent
        env_path = here.parent.parent.parent.parent / ".env"
        for parent in [here] + list(here.parents):
            if (parent / ".env").exists():
                env_path = parent / ".env"
                break

    if args.check:
        if not env_path.exists():
            print(f"No .env found at {env_path}. Run without --check to create one.")
            return 1
        try:
            from dotenv import dotenv_values
            values = {
                key: (value or "")
                for key, value in dict(dotenv_values(env_path)).items()
            }
        except ImportError:
            print("python-dotenv not installed. Run: pip install python-dotenv")
            return 1
        all_ok = verify(values)
    else:
        values = run_wizard(env_path)
        write_env(values, env_path)
        all_ok = verify(values)

    print()
    if all_ok:
        print("Setup complete. You are ready to use the DevOps Copilot Plugin.")
        _run_post_setup_fetches(values, env_path)
    else:
        print("Setup complete with some failures. Fix the issues above and re-run with --check.")
    return 0 if all_ok else 1


def _run_post_setup_fetches(values: dict, env_path: "Path") -> None:
    """After a successful setup, automatically fetch Jenkins configs and GitLab snapshot.
    On failure the user is prompted to retry or skip — the fetch loop does not advance
    to the next item until the current one succeeds or is explicitly skipped.
    """
    import subprocess

    scripts_dir = Path(__file__).resolve().parent
    project_root = env_path.parent
    python = sys.executable

    def _run_with_retry(label: str, cmd: list, skip_hint: str) -> bool:
        """Run a command. On failure, ask the user to fix and retry or skip."""
        while True:
            result = subprocess.run(cmd, cwd=str(project_root))
            if result.returncode == 0:
                return True
            _fail(f"{label} failed.")
            print(f"\n  Fix the issue, then choose:")
            print(f"    [r] Retry")
            print(f"    [s] Skip  ({skip_hint})")
            choice = input("  Your choice [r/s]: ").strip().lower()
            if choice == "s":
                _skip(f"{label} skipped by user.")
                return False
            # Any other input (including 'r' or Enter) retries
            print()

    # --- Jenkins: fetch config XMLs ---
    jenkins_root = values.get("JENKINS_ROOT_URL", "").strip()
    if jenkins_root:
        _header("Fetching Jenkins config XMLs…")
        _run_with_retry(
            "Jenkins config fetch",
            [python, str(scripts_dir / "fetch_jenkins_configs.py")],
            skip_hint="you can run fetch_jenkins_configs.py later",
        )
    else:
        _skip("JENKINS_ROOT_URL not set — skipping Jenkins config fetch.")

    # --- GitLab: fetch CI snapshot ---
    gitlab_token = values.get("GITLAB_TOKEN", "").strip()
    gitlab_project = values.get("GITLAB_PROJECT_ID", "").strip()
    if gitlab_token and gitlab_project:
        _header("Fetching GitLab CI snapshot…")
        _run_with_retry(
            "GitLab config fetch",
            [python, str(scripts_dir / "fetch_gitlab_config.py"),
             "--output-dir", str(project_root / "gitlab_config")],
            skip_hint="you can run fetch_gitlab_config.py later",
        )
    else:
        _skip("GITLAB credentials not set — skipping GitLab config fetch.")

    print()
    print("Next step: open Copilot Chat and run /explore-pipeline to analyse your pipeline.")


if __name__ == "__main__":
    sys.exit(main())

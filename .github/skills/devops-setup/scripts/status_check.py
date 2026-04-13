#!/usr/bin/env python3
"""
status_check.py — Check the current state of the DevOps Copilot Plugin.

Inspects the project root for artifact files produced by each plugin step and
prints a structured summary of what is done, what is partial, and what is
still missing.  Designed to be run at plugin startup so the user is presented
with only the actions that are still needed.

Usage:
    python .github/skills/devops-setup/scripts/status_check.py
    python .github/skills/devops-setup/scripts/status_check.py --json
    python .github/skills/devops-setup/scripts/status_check.py --root /path/to/project
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Status levels
# ---------------------------------------------------------------------------

DONE    = "done"
PARTIAL = "partial"
MISSING = "missing"

STATUS_ICON = {
    DONE:    "[+]",
    PARTIAL: "[~]",
    MISSING: "[ ]",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_project_root(start: Path) -> Path:
    """Walk up from *start* until we find a directory that contains a .env or
    a .github folder.  Falls back to *start* itself."""
    for candidate in [start] + list(start.parents):
        if (candidate / ".env").exists() or (candidate / ".github").exists():
            return candidate
    return start


def _env_values(env_path: Path) -> dict[str, str]:
    try:
        from dotenv import dotenv_values  # type: ignore
        return {k: (v or "") for k, v in dotenv_values(env_path).items()}
    except ImportError:
        # Minimal fallback: parse KEY=VALUE lines ourselves
        values: dict[str, str] = {}
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                values[k.strip()] = v.strip()
        return values


def _count_files(directory: Path, pattern: str = "*") -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for _ in directory.glob(pattern))


# ---------------------------------------------------------------------------
# Individual step checks
# ---------------------------------------------------------------------------

def check_env(root: Path) -> dict[str, Any]:
    env_path = root / ".env"
    if not env_path.exists():
        return {
            "step": "credentials",
            "label": "Setup & Credentials (.env)",
            "status": MISSING,
            "detail": ".env file not found",
            "action": "Run: uv run python .github/skills/devops-setup/scripts/setup_wizard.py",
        }

    values = _env_values(env_path)

    required_gitlab = ["GITLAB_URL", "GITLAB_TOKEN", "GITLAB_PROJECT_ID"]
    missing = [k for k in required_gitlab if not values.get(k, "").strip()]

    has_jenkins = bool(values.get("JENKINS_ROOT_URL", "").strip())
    has_runner  = bool(values.get("RUNNER_HOST", "").strip())
    has_llm     = bool(values.get("COPILOT_TOKEN", "").strip())

    if missing:
        return {
            "step": "credentials",
            "label": "Setup & Credentials (.env)",
            "status": PARTIAL,
            "detail": f"Missing required keys: {', '.join(missing)}",
            "action": "Run: uv run python .github/skills/devops-setup/scripts/setup_wizard.py --check",
            "extras": {"jenkins": has_jenkins, "runner": has_runner, "llm": has_llm},
        }

    extras = []
    if has_jenkins: extras.append("Jenkins")
    if has_runner:  extras.append("runner")
    if has_llm:     extras.append("LLM")

    gitlab_proj = values.get("GITLAB_PROJECT_ID", "?")
    detail = f"GitLab project: {gitlab_proj}"
    if extras:
        detail += f"  |  optional: {', '.join(extras)}"

    return {
        "step": "credentials",
        "label": "Setup & Credentials (.env)",
        "status": DONE,
        "detail": detail,
        "action": "Run: uv run python .github/skills/devops-setup/scripts/setup_wizard.py --check  (to re-test)",
        "extras": {"jenkins": has_jenkins, "runner": has_runner, "llm": has_llm},
        "values": values,   # carry forward for downstream checks
    }


def check_jenkins_configs(root: Path, env_status: dict) -> dict[str, Any]:
    # Skip if Jenkins was never configured
    has_jenkins = (env_status.get("extras") or {}).get("jenkins", False)
    if not has_jenkins:
        return {
            "step": "jenkins_configs",
            "label": "Jenkins Config Fetch",
            "status": DONE,
            "detail": "JENKINS_ROOT_URL not set — skipped (not needed)",
            "action": None,
            "skipped": True,
        }

    # Standard plugin path: fetch_xml/jenkins_graph_xml.json
    # Also look for it in legacy workspace locations
    candidates = [
        root / "fetch_xml" / "jenkins_graph_xml.json",
        root / "UFT-One-Migration" / "UFT One Migration 3" / "fetch_xml" / "jenkins_graph_xml.json",
    ]
    graph_file = next((p for p in candidates if p.exists()), None)

    config_xml_candidates = [
        root / "fetch_xml" / "config_xml",
        root / "UFT-One-Migration" / "UFT One Migration 3" / "fetch_xml" / "config_xml",
    ]
    config_xml_dir = next((p for p in config_xml_candidates if p.is_dir()), None)
    xml_count = _count_files(config_xml_dir, "*.xml") if config_xml_dir else 0

    if graph_file and xml_count > 0:
        return {
            "step": "jenkins_configs",
            "label": "Jenkins Config Fetch",
            "status": DONE,
            "detail": f"Graph registry found  |  {xml_count} config XMLs at {graph_file.parent.parent.name}/config_xml/",
            "action": None,
        }
    if graph_file and xml_count == 0:
        return {
            "step": "jenkins_configs",
            "label": "Jenkins Config Fetch",
            "status": PARTIAL,
            "detail": "jenkins_graph_xml.json found but config_xml/ is empty",
            "action": "Run: uv run python .github/skills/devops-setup/scripts/fetch_jenkins_configs.py",
        }
    return {
        "step": "jenkins_configs",
        "label": "Jenkins Config Fetch",
        "status": MISSING,
        "detail": "jenkins_graph_xml.json not found",
        "action": "Run: uv run python .github/skills/devops-setup/scripts/fetch_jenkins_configs.py",
    }


def check_jenkins_logs(root: Path, env_status: dict) -> dict[str, Any]:
    has_jenkins = (env_status.get("extras") or {}).get("jenkins", False)
    if not has_jenkins:
        return {
            "step": "jenkins_logs",
            "label": "Jenkins Build Logs (optional)",
            "status": DONE,
            "detail": "JENKINS_ROOT_URL not set — skipped",
            "action": None,
            "skipped": True,
        }

    candidates = [
        root / "fetch_xml" / "build_logs",
        root / "UFT-One-Migration" / "UFT One Migration 3" / "fetch_xml" / "build_logs",
    ]
    log_dir = next((p for p in candidates if p.is_dir()), None)
    log_count = _count_files(log_dir, "*.log") if log_dir else 0
    manifest = (log_dir / "manifest.json") if log_dir else None

    if log_count > 0:
        return {
            "step": "jenkins_logs",
            "label": "Jenkins Build Logs (optional)",
            "status": DONE,
            "detail": f"{log_count} build logs downloaded",
            "action": None,
        }
    return {
        "step": "jenkins_logs",
        "label": "Jenkins Build Logs (optional)",
        "status": MISSING,
        "detail": "No build logs found",
        "action": "Run: uv run python .github/skills/devops-setup/scripts/fetch_jenkins_logs.py",
    }


def check_gitlab_snapshot(root: Path) -> dict[str, Any]:
    candidates = [
        root / "gitlab_config",
        root / "UFT-One-Migration" / "UFT One Migration 3" / "gitlab_config",
    ]
    cfg_dir = next((p for p in candidates if p.is_dir()), None)

    if cfg_dir:
        file_count = _count_files(cfg_dir)
        return {
            "step": "gitlab_snapshot",
            "label": "GitLab CI Snapshot",
            "status": DONE,
            "detail": f"{file_count} files in {cfg_dir.name}/",
            "action": None,
        }
    return {
        "step": "gitlab_snapshot",
        "label": "GitLab CI Snapshot",
        "status": MISSING,
        "detail": "gitlab_config/ not found",
        "action": "Run: uv run python .github/skills/devops-setup/scripts/fetch_gitlab_config.py --output-dir gitlab_config",
    }


def check_stage_dict(root: Path) -> dict[str, Any]:
    candidates = [
        root / "plugin_artifacts" / "stage_dict.json",
        root / "UFT-One-Migration" / "UFT One Migration 3" / "gitlab_pipeline" / "stage_dict_pilot.json",
        root / "stage_dict.json",
    ]
    sd_file = next((p for p in candidates if p.exists()), None)

    # Also look for any stage_dict*.json anywhere under the root (broad search)
    if not sd_file:
        found = sorted(root.rglob("stage_dict*.json"))
        if found:
            sd_file = found[0]

    if sd_file:
        try:
            data = json.loads(sd_file.read_text(encoding="utf-8"))
            job_count = len(data) if isinstance(data, dict) else "?"
        except Exception:
            job_count = "?"
        return {
            "step": "stage_dict",
            "label": "Stage Dictionary",
            "status": DONE,
            "detail": f"{job_count} jobs indexed  —  {sd_file.relative_to(root)}",
            "action": None,
        }
    return {
        "step": "stage_dict",
        "label": "Stage Dictionary",
        "status": MISSING,
        "detail": "stage_dict.json not found",
        "action": (
            "Run: uv run python .github/skills/j2gl-migrate/scripts/build_stage_dict.py "
            "--graph fetch_xml/jenkins_graph_xml.json "
            "--output plugin_artifacts/stage_dict.json"
        ),
    }


def check_migrated_yamls(root: Path) -> dict[str, Any]:
    candidates = [
        root / "migrated_yamls",
        root / "UFT-One-Migration" / "UFT One Migration 3" / "gitlab_pipeline" / "migrated_yamls",
    ]
    yml_dir = next((p for p in candidates if p.is_dir()), None)

    if not yml_dir:
        return {
            "step": "migrated_yamls",
            "label": "Migrated YAML Files",
            "status": MISSING,
            "detail": "migrated_yamls/ directory not found",
            "action": "Use migration-planner agent then run /migrate-job",
        }

    # Count all .yml/.yaml files recursively
    yaml_files = list(yml_dir.rglob("*.yml")) + list(yml_dir.rglob("*.yaml"))
    count = len(yaml_files)

    if count == 0:
        return {
            "step": "migrated_yamls",
            "label": "Migrated YAML Files",
            "status": PARTIAL,
            "detail": f"migrated_yamls/ exists but is empty",
            "action": "Run /migrate-job to start converting jobs",
        }

    return {
        "step": "migrated_yamls",
        "label": "Migrated YAML Files",
        "status": DONE,
        "detail": f"{count} YAML file(s) in {yml_dir.relative_to(root)}/",
        "action": None,
    }


def check_qc_reports(root: Path) -> dict[str, Any]:
    candidates = [
        root / "qc_reports",
        root / "UFT-One-Migration" / "UFT One Migration 3" / "gitlab_pipeline" / "qc_reports",
    ]
    qc_dir = next((p for p in candidates if p.is_dir()), None)

    if not qc_dir:
        return {
            "step": "qc_reports",
            "label": "QC Reports",
            "status": MISSING,
            "detail": "qc_reports/ directory not found",
            "action": "Run /qc-job after migrating at least one job",
        }

    json_reports = list(qc_dir.glob("*.json"))
    txt_reports  = list(qc_dir.glob("*.txt")) + list(qc_dir.glob("*.md"))
    total = len(json_reports) + len(txt_reports)

    if total == 0:
        return {
            "step": "qc_reports",
            "label": "QC Reports",
            "status": PARTIAL,
            "detail": "qc_reports/ exists but contains no reports",
            "action": "Run /qc-job to generate a QC report",
        }

    # Peek at the most recent report for pass/fail status
    latest_status = _read_latest_qc_status(qc_dir)
    detail = f"{total} report(s) found"
    if latest_status:
        detail += f"  |  latest: {latest_status}"

    return {
        "step": "qc_reports",
        "label": "QC Reports",
        "status": DONE,
        "detail": detail,
        "action": None,
    }


def _read_latest_qc_status(qc_dir: Path) -> str:
    """Try to extract the QC_STATUS from the most recently modified report."""
    try:
        reports = sorted(
            qc_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if reports:
            data = json.loads(reports[0].read_text(encoding="utf-8", errors="replace"))
            return data.get("QC_STATUS") or data.get("status") or ""
        # fallback: plain text
        txt_reports = sorted(
            list(qc_dir.glob("*.txt")) + list(qc_dir.glob("*.md")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if txt_reports:
            text = txt_reports[0].read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                if "QC_STATUS" in line:
                    return line.strip()
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Full status report
# ---------------------------------------------------------------------------

def gather_status(root: Path) -> list[dict[str, Any]]:
    env_result = check_env(root)
    results = [env_result]
    results.append(check_jenkins_configs(root, env_result))
    results.append(check_jenkins_logs(root, env_result))
    results.append(check_gitlab_snapshot(root))
    results.append(check_stage_dict(root))
    results.append(check_migrated_yamls(root))
    results.append(check_qc_reports(root))
    return results


def format_report(results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 62)
    lines.append("  DevOps Copilot Plugin — Current Status")
    lines.append("=" * 62)

    pending_actions: list[str] = []

    for r in results:
        icon   = STATUS_ICON[r["status"]]
        label  = r["label"]
        detail = r.get("detail", "")
        lines.append(f"\n  {icon}  {label}")
        if detail:
            lines.append(f"       {detail}")
        if r["status"] != DONE and r.get("action"):
            pending_actions.append((r["label"], r["action"]))

    lines.append("")
    lines.append("  Legend:  [+] done   [~] partial   [ ] not started")
    lines.append("")

    if not pending_actions:
        lines.append("  All steps complete. Choose what you want to do:")
    else:
        lines.append("  Suggested next actions:")
        for label, action in pending_actions:
            lines.append(f"    • {label}")
            lines.append(f"      {action}")
            lines.append("")

    lines.append("=" * 62)
    lines.append("")
    return "\n".join(lines)


def interactive_menu(results: list[dict[str, Any]]) -> None:
    """Print the status report and present a numbered menu of next actions."""
    print(format_report(results))

    choices: list[dict[str, str]] = []

    # Build menu based on what is not done
    env_done = any(r["step"] == "credentials" and r["status"] == DONE for r in results)

    if not env_done:
        choices.append({
            "label": "Run setup wizard (create / update .env)",
            "cmd":   "uv run python .github/skills/devops-setup/scripts/setup_wizard.py",
        })

    for r in results:
        if r.get("skipped"):
            continue
        if r["status"] in (MISSING, PARTIAL) and r.get("action"):
            choices.append({"label": r["label"], "cmd": r["action"]})

    # Always-available actions
    choices.append({"label": "Re-test connections only",
                    "cmd": "uv run python .github/skills/devops-setup/scripts/setup_wizard.py --check"})
    choices.append({"label": "Explore pipeline  (/explore-pipeline)",
                    "cmd": "Use /explore-pipeline in Copilot Chat"})
    choices.append({"label": "Migrate a job  (/migrate-job)",
                    "cmd": "Use /migrate-job in Copilot Chat"})
    choices.append({"label": "QC a job  (/qc-job)",
                    "cmd": "Use /qc-job in Copilot Chat"})
    choices.append({"label": "Exit", "cmd": None})

    print("  What would you like to do?")
    for i, c in enumerate(choices, 1):
        print(f"    {i}) {c['label']}")
    print()

    raw = input("  Enter number (or press Enter to exit): ").strip()
    if not raw:
        return

    try:
        idx = int(raw) - 1
        chosen = choices[idx]
    except (ValueError, IndexError):
        print("  Invalid choice — exiting.")
        return

    if chosen["cmd"] is None:
        return

    cmd = chosen["cmd"]
    if cmd.startswith("Use "):
        print(f"\n  → {cmd}")
    else:
        print(f"\n  Running: {cmd}\n")
        import subprocess
        subprocess.run(cmd, shell=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check the current state of the DevOps Copilot Plugin."
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Project root directory (default: auto-detected from .env / .github)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the human table.",
    )
    parser.add_argument(
        "--no-menu",
        action="store_true",
        help="Print the status report and exit without showing the interactive menu.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else _find_project_root(Path.cwd())

    results = gather_status(root)

    if args.json:
        # Strip the 'values' key (contains secrets) before printing
        safe = [{k: v for k, v in r.items() if k != "values"} for r in results]
        print(json.dumps(safe, indent=2))
        return 0

    if args.no_menu:
        print(format_report(results))
        return 0

    interactive_menu(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())

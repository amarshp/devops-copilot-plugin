#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


def _detect_status(report_text: str) -> str:
    first = report_text.splitlines()[0].strip() if report_text.strip() else ""
    if first.startswith("QC_STATUS:"):
        return first.split(":", 1)[1].strip().upper()
    return "UNKNOWN"


def _extract_job_mapping(report_text: str, fallback_gitlab_job: str = "") -> tuple[str, str]:
    gitlab_job = fallback_gitlab_job
    jenkins_job = ""

    gitlab_match = re.search(r"GitLab job `([^`]+)`", report_text)
    if gitlab_match:
        gitlab_job = gitlab_match.group(1).strip()

    jenkins_match = re.search(r"Jenkins `([^`]+)`(?: job)?", report_text)
    if jenkins_match:
        jenkins_job = jenkins_match.group(1).strip()

    return gitlab_job, jenkins_job


def update_tree(tree_path: Path, job_name: str, status_tag: str) -> bool:
    if not tree_path.exists():
        return False
    lines = tree_path.read_text(encoding="utf-8", errors="replace").splitlines()
    changed = False
    for i, line in enumerate(lines):
        if job_name in line:
            base = line.split("[")[0].rstrip()
            lines[i] = f"{base} [{status_tag}]"
            changed = True
            break
    if changed:
        tree_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def append_history(history_path: Path, entry: str) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update QC tree and run history from QC report")
    parser.add_argument("--job", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--pipeline-id", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    report_path = Path(args.report)
    report_text = report_path.read_text(encoding="utf-8", errors="replace")
    status = _detect_status(report_text)
    gitlab_job, jenkins_job = _extract_job_mapping(report_text, fallback_gitlab_job=args.job)
    mapping = {"SUCCESS": "qc-pass", "FAIL": "qc-fail", "BLOCKED": "qc-blocked"}
    status_tag = mapping.get(status, "qc-unknown")

    tree_updated = update_tree(Path(args.tree), jenkins_job or args.job, status_tag)

    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"- {stamp} | job={args.job} | pipeline={args.pipeline_id or 'n/a'} | status={status} | tag={status_tag} | report={report_path.name}"
    if gitlab_job:
        entry += f" | gitlab_job={gitlab_job}"
    if jenkins_job:
        entry += f" | jenkins_job={jenkins_job}"
    if args.notes:
        entry += f" | notes={args.notes}"
    append_history(Path(args.history), entry)

    print(f"QC status: {status}")
    print(f"Tree updated: {tree_updated}")
    print(f"History appended: {args.history}")

    # Refresh migration dashboard after every QC update
    _update_dashboard(Path(args.history))

    return 0


def _update_dashboard(history_path: Path) -> None:
    try:
        import sys as _sys
        _here = Path(__file__).resolve().parent
        if str(_here) not in _sys.path:
            _sys.path.insert(0, str(_here))
        from migration_dashboard import render
        cwd = Path.cwd()
        render(
            tree_path    = cwd / "fetch_xml" / "pipeline_tree.txt",
            registry_path= cwd / "fetch_xml" / "jenkins_graph_xml.json",
            history_path = history_path,
            qc_dir       = cwd / "qc_reports",
            log_dir      = cwd / "pipeline_logs",
            migrated_dir = cwd / "migrated_yamls",
            output_path  = cwd / "MIGRATION_STATUS.md",
        )
    except Exception as exc:
        print(f"[dashboard] Could not update MIGRATION_STATUS.md: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())

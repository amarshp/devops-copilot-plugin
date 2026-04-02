#!/usr/bin/env python3
"""
migration_dashboard.py — Generate / update MIGRATION_STATUS.md

Produces a single Markdown file that shows:

  1. Header scoreboard  — total jobs, % migrated, % QC-passed, run count,
                          current active job, latest pipeline ID + status
  2. Pipeline tree       — every job annotated with its migration + QC state
                          using colour-coded badges
  3. Run log             — every pipeline run with per-job result table,
                          errors/warnings, and recommended fixes

Usage (standalone):
    python migration_dashboard.py \\
        --tree      fetch_xml/pipeline_tree.txt \\
        --history   QC_RUN_HISTORY.md \\
        --qc-dir    qc_reports \\
        --log-dir   pipeline_logs \\
        --output    MIGRATION_STATUS.md

Called automatically from push_and_trigger.py and qc_status_tracker.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# State loading helpers
# ---------------------------------------------------------------------------

def _load_tree_lines(tree_path: Path) -> list[str]:
    if not tree_path.exists():
        return []
    return tree_path.read_text(encoding="utf-8", errors="replace").splitlines()


def _load_registry_jobs(registry_path: Path) -> list[str]:
    if not registry_path.exists():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    jobs = data.get("jobs", {})
    if isinstance(jobs, dict):
        return list(jobs.keys())
    return []


def _load_migrated_jobs(migrated_dir: Path) -> set[str]:
    migrated: set[str] = set()
    if not migrated_dir.exists():
        return migrated

    reserved = {
        "stages",
        "variables",
        "include",
        "workflow",
        "default",
        "image",
        "services",
        "cache",
        "before_script",
        "after_script",
        "pages",
    }

    for path in migrated_dir.rglob("*.yml"):
        try:
            parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if not isinstance(parsed, dict):
            continue
        for key, value in parsed.items():
            if key in reserved or str(key).startswith(".") or not isinstance(value, dict):
                continue
            migrated.add(str(key))
    return migrated


def _parse_history(history_path: Path) -> list[dict]:
    """Parse QC_RUN_HISTORY.md into structured records."""
    records: list[dict] = []
    if not history_path.exists():
        return records
    for line in history_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip().lstrip("- ")
        if not line:
            continue
        rec: dict = {}
        for part in line.split("|"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                rec[k.strip()] = v.strip()
            elif re.match(r"\d{4}-\d{2}-\d{2}", part):
                rec["timestamp"] = part
        if rec:
            records.append(rec)
    return records


def _load_manifests(log_dir: Path) -> list[dict]:
    """Load all qc_manifest_*.json files, newest first."""
    if not log_dir.exists():
        return []
    manifests = sorted(
        log_dir.glob("qc_manifest_*.json"),
        key=lambda path: int(re.search(r"qc_manifest_(\d+)", path.name).group(1))
        if re.search(r"qc_manifest_(\d+)", path.name)
        else -1,
        reverse=True,
    )
    result = []
    for m in manifests:
        try:
            data = json.loads(m.read_text(encoding="utf-8"))
            data["_manifest_file"] = m.name
            result.append(data)
        except Exception:
            pass
    return result


def _load_qc_reports(qc_dir: Path) -> dict[str, dict]:
    """
    Returns {job_name: {status, summary, fixes}} for every QC report found.
    Uses the latest report per job (sorted by filename).
    """
    if not qc_dir.exists():
        return {}
    reports: dict[str, list[Path]] = {}
    for p in qc_dir.glob("*.md"):
        # filename pattern: <JOB_NAME>-run-<N>.md
        m = re.match(r"^(.+)-run-(\d+)\.md$", p.name)
        if m:
            reports.setdefault(m.group(1), []).append(p)
    result: dict[str, dict] = {}
    for job, paths in reports.items():
        latest = sorted(paths, key=lambda p: int(re.search(r"run-(\d+)", p.name).group(1)))[-1]
        text = latest.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        status = "UNKNOWN"
        if lines and lines[0].startswith("QC_STATUS:"):
            status = lines[0].split(":", 1)[1].strip().upper()
        gitlab_job, jenkins_job = _extract_job_mapping(text, fallback_gitlab_job=job)
        # Extract "Required Fix" section if present
        fixes = _extract_section(text, ["Required Fix", "Recommended Fix", "Fix Before"])
        summary = _extract_section(text, ["Assessment", "Summary"], max_lines=3)
        report_info = {
            "status": status,
            "fixes": fixes,
            "summary": summary,
            "report": latest.name,
            "gitlab_job": gitlab_job,
            "jenkins_job": jenkins_job,
        }
        result[gitlab_job or job] = report_info
        if job not in result:
            result[job] = report_info
    return result


def _extract_job_mapping(text: str, fallback_gitlab_job: str = "") -> tuple[str, str]:
    gitlab_job = fallback_gitlab_job
    jenkins_job = ""

    gitlab_match = re.search(r"GitLab job `([^`]+)`", text)
    if gitlab_match:
        gitlab_job = gitlab_match.group(1).strip()

    jenkins_match = re.search(r"Jenkins `([^`]+)`(?: job)?", text)
    if jenkins_match:
        jenkins_job = jenkins_match.group(1).strip()

    return gitlab_job, jenkins_job


def _extract_section(text: str, headings: list[str], max_lines: int = 10) -> str:
    lines = text.splitlines()
    in_section = False
    collected: list[str] = []
    for line in lines:
        lower = line.lower().strip("#").strip()
        if any(h.lower() in lower for h in headings):
            in_section = True
            continue
        if in_section:
            if line.startswith("#"):
                break
            if line.strip():
                collected.append(line.strip())
                if len(collected) >= max_lines:
                    break
    return " ".join(collected)


# ---------------------------------------------------------------------------
# Annotation helpers
# ---------------------------------------------------------------------------

_STATUS_BADGE = {
    "qc-pass":    "🟢 qc-pass",
    "qc-fail":    "🔴 qc-fail",
    "qc-blocked": "🟡 qc-blocked",
    "migrated":   "🔵 migrated",
    "pending":    "⚪ pending",
}

_QC_TO_TAG = {
    "SUCCESS": "qc-pass",
    "FAIL":    "qc-fail",
    "BLOCKED": "qc-blocked",
}


def _canonical_job_name(name: str, aliases: dict[str, str], known_jobs: set[str]) -> str:
    if not name:
        return ""
    if name in known_jobs or not known_jobs:
        return name
    alias = aliases.get(name, "")
    if alias in known_jobs:
        return alias
    return name


def _annotate_tree(tree_lines: list[str], qc_reports: dict[str, dict],
                   history: list[dict], known_jobs: set[str], migrated_jobs: set[str]) -> tuple[list[str], dict[str, str]]:
    """
    Return annotated tree lines and a {job_name: tag} status dict.
    Priority: qc status > migrated (history entry exists) > pending
    """
    aliases: dict[str, str] = {}
    for info in qc_reports.values():
        gitlab_job = info.get("gitlab_job", "")
        jenkins_job = info.get("jenkins_job", "")
        if gitlab_job and jenkins_job:
            aliases[gitlab_job] = jenkins_job

    # Build job → tag from history
    job_tags: dict[str, str] = {}
    for rec in history:
        job = rec.get("jenkins_job") or rec.get("gitlab_job") or rec.get("job", "")
        job = _canonical_job_name(job, aliases, known_jobs)
        tag = rec.get("tag", "")
        if job and tag and (not known_jobs or job in known_jobs):
            job_tags[job] = tag

    for job in migrated_jobs:
        canonical_job = _canonical_job_name(job, aliases, known_jobs)
        if canonical_job and canonical_job not in job_tags and (not known_jobs or canonical_job in known_jobs):
            job_tags[canonical_job] = "migrated"

    # Override with qc_reports (most authoritative)
    for job, info in qc_reports.items():
        tag = _QC_TO_TAG.get(info["status"], "migrated")
        canonical_job = _canonical_job_name(
            info.get("jenkins_job") or info.get("gitlab_job") or job,
            aliases,
            known_jobs,
        )
        if canonical_job and (not known_jobs or canonical_job in known_jobs):
            job_tags[canonical_job] = tag

    annotated: list[str] = []
    for line in tree_lines:
        # Remove any existing badge
        clean = re.sub(r"\s+[🟢🔴🟡🔵⚪]\s+\S.*$", "", line)
        # Find the job name on the line (last non-space word after tree connectors)
        match = re.search(r"([A-Za-z0-9_.‑-]+(?:\.[A-Za-z0-9_.‑-]+)+)\s*$", clean)
        if match:
            job = match.group(1)
            tag = job_tags.get(job, "pending")
            badge = _STATUS_BADGE.get(tag, f"[{tag}]")
            clean = clean.rstrip() + f"  {badge}"
        annotated.append(clean)

    return annotated, job_tags


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def _compute_stats(job_tags: dict[str, str], all_jobs: list[str],
                   history: list[dict], manifests: list[dict]) -> dict:
    total = len(all_jobs) if all_jobs else max(len(job_tags), 1)
    migrated = len([t for t in job_tags.values() if t in ("migrated", "qc-pass", "qc-fail", "qc-blocked")])
    qc_pass   = len([t for t in job_tags.values() if t == "qc-pass"])
    qc_fail   = len([t for t in job_tags.values() if t == "qc-fail"])
    run_count  = len(manifests)
    latest_pipeline = ""
    latest_status   = ""
    if manifests:
        first = manifests[0]
        latest_pipeline = str(first.get("pipeline_id", ""))
        if not latest_pipeline:
            m = re.search(r"qc_manifest_(\d+)", first.get("_manifest_file", ""))
            if m:
                latest_pipeline = m.group(1)
        latest_status = str(first.get("pipeline_status", "") or "")
        jobs_list = first.get("jobs", [])
        if isinstance(jobs_list, list):
            statuses = [j.get("status", "") for j in jobs_list if isinstance(j, dict)]
        elif isinstance(jobs_list, dict):
            statuses = [v.get("status", "") for v in jobs_list.values() if isinstance(v, dict)]
        else:
            statuses = []
        if not latest_status and statuses:
            latest_status = "failed" if "failed" in statuses else "success"

    current_job = ""
    if history:
        current_job = history[-1].get("jenkins_job") or history[-1].get("job", "")
    if not current_job and manifests:
        latest_jobs = manifests[0].get("jobs", [])
        if isinstance(latest_jobs, list) and latest_jobs:
            failed_jobs = [job for job in latest_jobs if isinstance(job, dict) and job.get("status") == "failed"]
            if failed_jobs:
                current_job = failed_jobs[0].get("job", "")
            else:
                current_job = latest_jobs[-1].get("job", "")

    return {
        "total":            total,
        "migrated":         migrated,
        "pct_migrated":     round(migrated / total * 100) if total else 0,
        "qc_pass":          qc_pass,
        "qc_fail":          qc_fail,
        "pct_qc_pass":      round(qc_pass / total * 100) if total else 0,
        "run_count":        run_count,
        "latest_pipeline":  latest_pipeline,
        "latest_status":    latest_status,
        "current_job":      current_job,
    }


# ---------------------------------------------------------------------------
# Run log section
# ---------------------------------------------------------------------------

def _build_run_log(manifests: list[dict], qc_reports: dict[str, dict]) -> str:
    if not manifests:
        return "_No pipeline runs recorded yet._\n"

    sections: list[str] = []
    for manifest in manifests:
        pid = str(manifest.get("pipeline_id", ""))
        if not pid:
            m = re.search(r"qc_manifest_(\d+)", manifest.get("_manifest_file", ""))
            pid = m.group(1) if m else "unknown"

        # Normalise jobs to a list of dicts with a 'job' key
        raw_jobs = manifest.get("jobs", [])
        if isinstance(raw_jobs, dict):
            jobs_list = [{"job": k, **v} for k, v in raw_jobs.items()]
        elif isinstance(raw_jobs, list):
            jobs_list = raw_jobs
        else:
            jobs_list = []

        failed_jobs  = [j["job"] for j in jobs_list if j.get("status") == "failed"]
        pipeline_status = str(manifest.get("pipeline_status", "") or "")
        if pipeline_status == "failed":
            overall = "❌ FAILED"
        elif pipeline_status == "success":
            overall = "✅ SUCCESS"
        elif failed_jobs:
            overall = "❌ FAILED"
        elif jobs_list:
            overall = "✅ SUCCESS"
        else:
            overall = "🔄 UNKNOWN"

        lines = [
            f"### Pipeline `{pid}` — {overall}",
            "",
            f"| Job | Status | Errors | Warnings | QC | Fix |",
            f"|-----|--------|--------|----------|----|-----|",
        ]
        for info in sorted(jobs_list, key=lambda x: x.get("job", "")):
            job = info.get("job", "")
            status_icon = "✅" if info.get("status") == "success" else "❌"
            errors   = info.get("msbuild_errors",   info.get("errors",   0))
            warnings = info.get("msbuild_warnings", info.get("warnings", 0))
            qc_info  = qc_reports.get(job, {})
            qc_badge = {"SUCCESS": "🟢", "FAIL": "🔴", "BLOCKED": "🟡"}.get(
                qc_info.get("status", ""), "⚪")
            fix_text = (qc_info.get("fixes", "") or "")[:80].replace("|", "/") or "—"
            lines.append(f"| `{job}` | {status_icon} {info.get('status','')} | {errors} | {warnings} | {qc_badge} | {fix_text} |")

        if failed_jobs:
            lines += ["", "**Failed jobs — recommended fixes:**", ""]
            for job in failed_jobs:
                qc_info = qc_reports.get(job, {})
                fix = qc_info.get("fixes") or qc_info.get("summary") or "_No QC report yet — run `/qc-job` for this job._"
                lines.append(f"- **`{job}`**: {fix}")

        sections.append("\n".join(lines))

    return "\n\n---\n\n".join(sections) + "\n"


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render(tree_path: Path, history_path: Path, qc_dir: Path,
           log_dir: Path, output_path: Path, registry_path: Path | None = None,
           migrated_dir: Path | None = None) -> None:

    tree_lines  = _load_tree_lines(tree_path)
    history     = _parse_history(history_path)
    manifests   = _load_manifests(log_dir)
    qc_reports  = _load_qc_reports(qc_dir)
    migrated_jobs = _load_migrated_jobs(migrated_dir) if migrated_dir else set()

    all_jobs = _load_registry_jobs(registry_path) if registry_path else []
    if not all_jobs:
        seen: set[str] = set()
        for line in tree_lines:
            m = re.search(r"([A-Za-z0-9_.‑-]+(?:\.[A-Za-z0-9_.‑-]+)+)\s*$", line)
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                all_jobs.append(m.group(1))

    annotated_tree, job_tags = _annotate_tree(tree_lines, qc_reports, history, set(all_jobs), migrated_jobs)
    stats = _compute_stats(job_tags, all_jobs, history, manifests)

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Section 1: Scoreboard ──────────────────────────────────────────────
    pipeline_line = ""
    if stats["latest_pipeline"]:
        icon = "✅" if stats["latest_status"] == "success" else "❌" if stats["latest_status"] == "failed" else "🔄"
        pipeline_line = f"| Latest Pipeline | `{stats['latest_pipeline']}` {icon} {stats['latest_status']} |"

    scoreboard = f"""# Migration Status Dashboard
_Last updated: {now}_

## Scoreboard

| Metric | Value |
|--------|-------|
| Total Jobs | {stats['total']} |
| Migrated | {stats['migrated']} / {stats['total']} ({stats['pct_migrated']}%) |
| QC Passed | {stats['qc_pass']} / {stats['total']} ({stats['pct_qc_pass']}%) |
| QC Failed | {stats['qc_fail']} |
| Pipeline Runs | {stats['run_count']} |
| Current Job | `{stats['current_job'] or '—'}` |
{pipeline_line}

**Progress:** `{'█' * (stats['pct_migrated'] // 5)}{'░' * (20 - stats['pct_migrated'] // 5)}` {stats['pct_migrated']}% migrated  
**QC:** `{'█' * (stats['pct_qc_pass'] // 5)}{'░' * (20 - stats['pct_qc_pass'] // 5)}` {stats['pct_qc_pass']}% QC passed

### Legend
| Badge | Meaning |
|-------|---------|
| 🟢 qc-pass | Migrated and QC confirmed equivalent |
| 🔴 qc-fail | Migrated but QC found a mismatch |
| 🟡 qc-blocked | QC could not run (infra/auth blocker) |
| 🔵 migrated | YAML pushed, QC not yet run |
| ⚪ pending | Not yet migrated |

---
"""

    # ── Section 2: Annotated pipeline tree ───────────────────────────────
    tree_section = "## Pipeline Tree — Migration Progress\n\n```\n"
    tree_section += "\n".join(annotated_tree) + "\n```\n\n---\n"

    # ── Section 3: Run log ────────────────────────────────────────────────
    run_log_section = "## Run Log\n\n" + _build_run_log(manifests, qc_reports)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        scoreboard + tree_section + run_log_section,
        encoding="utf-8",
    )
    print(f"Dashboard updated: {output_path}  "
          f"({stats['pct_migrated']}% migrated, {stats['pct_qc_pass']}% QC passed, "
          f"{stats['run_count']} run(s))")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate/update MIGRATION_STATUS.md")
    parser.add_argument("--tree",    default="fetch_xml/pipeline_tree.txt")
    parser.add_argument("--registry", default="fetch_xml/jenkins_graph_xml.json")
    parser.add_argument("--history", default="QC_RUN_HISTORY.md")
    parser.add_argument("--qc-dir",  default="qc_reports")
    parser.add_argument("--log-dir", default="pipeline_logs")
    parser.add_argument("--migrated-dir", default="migrated_yamls")
    parser.add_argument("--output",  default="MIGRATION_STATUS.md")
    args = parser.parse_args()

    render(
        tree_path    = Path(args.tree),
        history_path = Path(args.history),
        qc_dir       = Path(args.qc_dir),
        log_dir      = Path(args.log_dir),
        output_path  = Path(args.output),
        registry_path= Path(args.registry),
        migrated_dir = Path(args.migrated_dir),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

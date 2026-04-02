#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests

import config

ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _headers() -> dict[str, str]:
    return {"PRIVATE-TOKEN": config.GITLAB_TOKEN}


def _latest_pipeline_id() -> int:
    url = f"{config.GITLAB_URL.rstrip('/')}/api/v4/projects/{config.PROJECT_ID}/pipelines"
    response = requests.get(url, headers=_headers(), params={"ref": config.BRANCH, "per_page": 1}, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not data:
        raise RuntimeError("No pipelines found")
    return int(data[0]["id"])


def _fetch_jobs(pipeline_id: int) -> list[dict]:
    jobs = []
    page = 1
    while True:
        url = f"{config.GITLAB_URL.rstrip('/')}/api/v4/projects/{config.PROJECT_ID}/pipelines/{pipeline_id}/jobs"
        response = requests.get(url, headers=_headers(), params={"per_page": 100, "page": page}, timeout=30)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        jobs.extend(batch)
        page += 1
    return jobs


def _download_trace(job_id: int) -> str:
    url = f"{config.GITLAB_URL.rstrip('/')}/api/v4/projects/{config.PROJECT_ID}/jobs/{job_id}/trace"
    response = requests.get(url, headers=_headers(), timeout=120)
    response.raise_for_status()
    return ANSI_RE.sub("", response.text)


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def _extract_counts(text: str) -> tuple[int, int]:
    errors = 0
    warnings = 0
    for line in text.splitlines():
        error_match = re.search(r"(\d+) Error\(s\)", line)
        if error_match:
            errors = max(errors, int(error_match.group(1)))
        warning_match = re.search(r"(\d+) Warning\(s\)", line)
        if warning_match:
            warnings = max(warnings, int(warning_match.group(1)))
    return errors, warnings


def _resolve_pipeline_id(positional: str | None, option: str | None, latest: bool) -> int:
    if latest:
        return _latest_pipeline_id()
    value = option or positional or "latest"
    return _latest_pipeline_id() if str(value).lower() == "latest" else int(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="QC bulk log downloader")
    parser.add_argument("pipeline_id", nargs="?", help="Pipeline ID or 'latest'")
    parser.add_argument("--pipeline-id", dest="pipeline_id_option", help="Pipeline ID or 'latest'")
    parser.add_argument("--latest", action="store_true", help="Use the latest pipeline on GITLAB_BRANCH")
    parser.add_argument("--output-dir", "--out", default="pipeline_logs", help="Directory for downloaded logs")
    parser.add_argument("--pattern", "--include-pattern", dest="patterns", action="append", default=[], help="Regex pattern for job names; repeat as needed")
    parser.add_argument("--job", "--include-job", dest="jobs", action="append", default=[], help="Explicit job name to include; repeat as needed")
    parser.add_argument("--failed-only", action="store_true", help="Download only failed jobs")
    parser.add_argument("--manifest", "--summary-json", dest="manifest", help="Manifest output path")
    args = parser.parse_args()

    pid = _resolve_pipeline_id(args.pipeline_id, args.pipeline_id_option, args.latest)
    jobs = _fetch_jobs(pid)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest) if args.manifest else output_dir / f"qc_manifest_{pid}.json"

    patterns = [re.compile(pattern, re.IGNORECASE) for pattern in args.patterns]
    include_jobs = set(args.jobs)
    results = []

    for job in sorted(jobs, key=lambda item: (item.get("stage", ""), item.get("name", ""))):
        name = job.get("name", "")
        status = job.get("status", "")
        if args.failed_only and status != "failed":
            continue
        if include_jobs or patterns:
            if name not in include_jobs and not any(pattern.search(name) for pattern in patterns):
                continue
        elif status not in {"success", "failed"}:
            continue

        text = _download_trace(int(job["id"]))
        errors, warnings = _extract_counts(text)
        log_path = output_dir / f"p{pid}_{_safe(name)}.log"
        log_path.write_text(text, encoding="utf-8", errors="replace")
        results.append(
            {
                "job": name,
                "status": status,
                "duration": job.get("duration"),
                "msbuild_errors": errors,
                "msbuild_warnings": warnings,
                "log_path": str(log_path),
            }
        )
        print(f"{name}: {status} E={errors} W={warnings}")

    manifest = {"pipeline_id": pid, "total_jobs": len(results), "jobs": results}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved manifest to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

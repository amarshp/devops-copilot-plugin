#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def _fetch_jobs(pid: int) -> list[dict]:
    jobs = []
    page = 1
    while True:
        url = f"{config.GITLAB_URL.rstrip('/')}/api/v4/projects/{config.PROJECT_ID}/pipelines/{pid}/jobs"
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


def _resolve_pipeline_id(positional: str | None, option: str | None, latest: bool) -> int:
    if latest:
        return _latest_pipeline_id()
    value = option or positional or "latest"
    return _latest_pipeline_id() if str(value).lower() == "latest" else int(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download GitLab pipeline logs")
    parser.add_argument("pipeline_id", nargs="?", help="Pipeline ID or 'latest'")
    parser.add_argument("--pipeline-id", dest="pipeline_id_option", help="Pipeline ID or 'latest'")
    parser.add_argument("--latest", action="store_true", help="Use the latest pipeline on GITLAB_BRANCH")
    parser.add_argument("--output-dir", "--out", default="pipeline_logs", help="Directory for downloaded logs")
    parser.add_argument("--all", action="store_true", help="Download all jobs regardless of status")
    parser.add_argument("--failed-only", action="store_true", help="Download only failed jobs")
    parser.add_argument("--job", action="append", default=[], help="Download only the named job; repeat as needed")
    parser.add_argument("--pattern", action="append", default=[], help="Regex pattern for job names; repeat as needed")
    args = parser.parse_args()

    pid = _resolve_pipeline_id(args.pipeline_id, args.pipeline_id_option, args.latest)
    jobs = _fetch_jobs(pid)
    selected_jobs = set(args.job)
    patterns = [re.compile(pattern, re.IGNORECASE) for pattern in args.pattern]

    targets = []
    for job in jobs:
        name = job.get("name", "")
        status = job.get("status", "")
        if args.failed_only and status != "failed":
            continue
        if selected_jobs or patterns:
            if name not in selected_jobs and not any(pattern.search(name) for pattern in patterns):
                continue
        elif not args.all and status not in {"failed", "success"}:
            continue
        targets.append(job)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for job in sorted(targets, key=lambda item: (item.get("stage", ""), item.get("name", ""))):
        text = _download_trace(int(job["id"]))
        out_path = output_dir / f"p{pid}_{_safe(job['name'])}.log"
        out_path.write_text(text, encoding="utf-8", errors="replace")
        print(f"Saved {out_path}")

    print(f"Downloaded {len(targets)} logs from pipeline {pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

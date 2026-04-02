#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict

import requests

import config

TERMINAL = {"success", "failed", "canceled", "skipped"}
DISPLAY_ORDER = ["success", "running", "pending", "failed", "created", "manual", "canceled", "skipped", "unknown"]


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


def _resolve_pipeline_id(positional: str | None, option: str | None, latest: bool) -> int:
    if latest:
        return _latest_pipeline_id()
    value = option or positional or "latest"
    return _latest_pipeline_id() if str(value).lower() == "latest" else int(value)


def _job_entry(job: dict) -> dict[str, object]:
    return {
        "name": job.get("name", ""),
        "stage": job.get("stage", ""),
        "status": job.get("status", "unknown"),
        "duration": job.get("duration"),
        "web_url": job.get("web_url", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll GitLab pipeline status")
    parser.add_argument("pipeline_id", nargs="?", help="Pipeline ID or 'latest'")
    parser.add_argument("--pipeline-id", dest="pipeline_id_option", help="Pipeline ID or 'latest'")
    parser.add_argument("--latest", action="store_true", help="Use the latest pipeline on GITLAB_BRANCH")
    parser.add_argument("--quick", action="store_true", help="Print only status counts and terminal state")
    parser.add_argument("--detailed", action="store_true", help="Print stage and duration for each job")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    pid = _resolve_pipeline_id(args.pipeline_id, args.pipeline_id_option, args.latest)
    jobs = _fetch_jobs(pid)

    by_status: dict[str, list[dict[str, object]]] = defaultdict(list)
    for job in jobs:
        entry = _job_entry(job)
        by_status[str(entry["status"])].append(entry)

    counts = {state: len(by_status.get(state, [])) for state in DISPLAY_ORDER if by_status.get(state)}
    terminal = all(str(job.get("status")) in TERMINAL for job in jobs)
    payload: dict[str, object] = {
        "pipeline_id": pid,
        "job_count": len(jobs),
        "terminal": terminal,
        "counts": counts,
    }
    if not args.quick:
        payload["jobs_by_status"] = {
            state: sorted(by_status[state], key=lambda item: (str(item["stage"]), str(item["name"])))
            for state in DISPLAY_ORDER
            if by_status.get(state)
        }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Pipeline {pid}: {len(jobs)} jobs")
    for state in DISPLAY_ORDER:
        items = by_status.get(state, [])
        if not items:
            continue
        print(f"  {state}: {len(items)}")
        if args.quick:
            continue
        if args.detailed:
            for item in sorted(items, key=lambda entry: (str(entry["stage"]), str(entry["name"]))):
                duration = item.get("duration")
                duration_text = f"{duration:.1f}s" if isinstance(duration, (float, int)) else "n/a"
                print(f"    - {item['name']} | stage={item['stage']} | duration={duration_text}")
        else:
            for item in sorted(items, key=lambda entry: str(entry["name"])):
                print(f"    - {item['name']}")
    print(f"Terminal: {terminal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

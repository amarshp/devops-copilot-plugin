#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import time
from pathlib import Path

import requests

import config

TERMINAL = {"success", "failed", "canceled", "skipped"}


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch pipeline job transitions")
    parser.add_argument("pipeline_id", nargs="?", help="Pipeline ID or 'latest'")
    parser.add_argument("--pipeline-id", dest="pipeline_id_option", help="Pipeline ID or 'latest'")
    parser.add_argument("--latest", action="store_true", help="Use the latest pipeline on GITLAB_BRANCH")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--alerts-file")
    parser.add_argument("--status-file")
    args = parser.parse_args()

    pid = _resolve_pipeline_id(args.pipeline_id, args.pipeline_id_option, args.latest)
    alerts = Path(args.alerts_file) if args.alerts_file else Path(f"pipeline_logs/_alerts_{pid}.txt")
    status = Path(args.status_file) if args.status_file else Path(f"pipeline_logs/_status_{pid}.txt")
    alerts.parent.mkdir(parents=True, exist_ok=True)

    seen: dict[str, str] = {}
    print(f"Watching pipeline {pid} every {args.interval}s")

    while True:
        jobs = _fetch_jobs(pid)
        now = dt.datetime.now().strftime("%H:%M:%S")
        status_lines = [f"[{now}] pipeline={pid} jobs={len(jobs)}"]
        alerts_now = []
        all_done = True

        for job in sorted(jobs, key=lambda item: item.get("id", 0)):
            name = job.get("name", "")
            current_status = job.get("status", "unknown")
            previous_status = seen.get(name)
            if current_status != previous_status:
                if current_status in TERMINAL and previous_status not in TERMINAL:
                    alerts_now.append(f"[{now}] COMPLETED: {name} -> {current_status.upper()}")
                seen[name] = current_status
            status_lines.append(f"- {name}: {current_status}")
            if current_status not in TERMINAL:
                all_done = False

        status.write_text("\n".join(status_lines) + "\n", encoding="utf-8")
        if alerts_now:
            with alerts.open("a", encoding="utf-8") as handle:
                handle.write("\n".join(alerts_now) + "\n")
            for line in alerts_now:
                print(line)

        if all_done:
            with alerts.open("a", encoding="utf-8") as handle:
                handle.write(f"[{now}] PIPELINE DONE\n")
            print("All jobs terminal. Pipeline complete.")
            break

        time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

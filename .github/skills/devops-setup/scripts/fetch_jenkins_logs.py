#!/usr/bin/env python3
"""Fetch Jenkins last successful build console logs for discovered jobs."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REGISTRY = HERE / "jenkins_graph_xml.json"
OUT_DIR = HERE / "build_logs"


def _safe_filename(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", name) + ".log"


def _load_env() -> None:
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        env_file = candidate / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            break


def _auth() -> tuple[str, str]:
    user = os.environ.get("JENKINS_USER", "")
    token = os.environ.get("JENKINS_TOKEN", "")
    if not user or not token:
        raise RuntimeError("JENKINS_USER and/or JENKINS_TOKEN are not set in .env")
    return user, token


def _load_jobs(registry_path: Path) -> dict[str, dict]:
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    jobs = payload.get("jobs") or {}
    if not isinstance(jobs, dict):
        raise RuntimeError("Invalid registry format: jobs is not a dictionary")
    return jobs


def _fetch_console_text(session: requests.Session, auth: tuple[str, str], job_url: str) -> tuple[str | None, str | None]:
    url = job_url.rstrip("/") + "/lastSuccessfulBuild/consoleText"
    try:
        response = session.get(url, auth=auth, timeout=45)
        if response.status_code == 404:
            return None, "no_last_successful_build"
        response.raise_for_status()
        return response.text, None
    except requests.HTTPError as exc:
        return None, f"http_error:{exc.response.status_code if exc.response else 'unknown'}"
    except requests.RequestException as exc:
        return None, f"request_error:{exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Jenkins last successful build logs")
    parser.add_argument("--registry", default=str(REGISTRY), help=f"Job registry JSON (default: {REGISTRY})")
    parser.add_argument("--output-dir", default=str(OUT_DIR), help=f"Output directory (default: {OUT_DIR})")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for number of jobs to fetch")
    args = parser.parse_args()

    _load_env()
    auth = _auth()

    registry_path = Path(args.registry)
    output_dir = Path(args.output_dir)

    if not registry_path.exists():
        raise RuntimeError(f"Registry not found: {registry_path}")

    jobs = _load_jobs(registry_path)
    items = sorted(jobs.items(), key=lambda x: x[0].lower())
    if args.limit > 0:
        items = items[: args.limit]

    output_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    no_build = 0
    failed = 0

    manifest: list[dict[str, str]] = []
    session = requests.Session()

    for idx, (job_name, meta) in enumerate(items, start=1):
        job_url = (meta or {}).get("url", "")
        if not job_url:
            failed += 1
            manifest.append({"job": job_name, "status": "missing_url"})
            continue

        text, err = _fetch_console_text(session, auth, job_url)
        if text is None:
            if err == "no_last_successful_build":
                no_build += 1
            else:
                failed += 1
            manifest.append({"job": job_name, "status": err or "unknown_error", "url": job_url})
            print(f"[{idx}/{len(items)}] SKIP  {job_name}  ({err})")
            continue

        out_path = output_dir / _safe_filename(job_name)
        out_path.write_text(text, encoding="utf-8", errors="replace")
        success += 1
        manifest.append({"job": job_name, "status": "saved", "file": out_path.name, "url": job_url})
        print(f"[{idx}/{len(items)}] OK    {job_name}  ->  {out_path.name}")

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nSummary")
    print("-" * 60)
    print(f"Jobs requested                : {len(items)}")
    print(f"Logs saved                    : {success}")
    print(f"No last successful build      : {no_build}")
    print(f"Failed requests               : {failed}")
    print(f"Manifest                      : {manifest_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

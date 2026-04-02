#!/usr/bin/env python3
"""
fetch_gitlab_config.py — Fetch and snapshot a GitLab project's CI configuration.

Downloads:
  - .gitlab-ci.yml and all local includes
  - Project-level CI/CD variables (values masked if secret)
  - Runner list with tags and status
  - Pipeline schedules

Output:
  gitlab_config/
    gitlab-ci.yml             Root CI file
    includes/                 All local include files
    variables.json            Project variables (masked values shown as ***)
    runners.json              Available runners
    schedules.json            Pipeline schedules
    summary.txt               Human-readable summary

Usage:
    python fetch_gitlab_config.py
    python fetch_gitlab_config.py --output-dir my_snapshot
    python fetch_gitlab_config.py --branch develop
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

# Resolve config from devops-setup/scripts/
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import config

_SESSION = requests.Session()
_SESSION.verify = False
_SESSION.headers.update({"PRIVATE-TOKEN": config.GITLAB_TOKEN})

BASE_API = f"{config.GITLAB_URL.rstrip('/')}/api/v4/projects/{config.PROJECT_ID}"


def _get(path: str, **params) -> dict | list:
    r = _SESSION.get(f"{BASE_API}{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _get_all_pages(path: str, **params) -> list:
    results = []
    page = 1
    while True:
        r = _SESSION.get(
            f"{BASE_API}{path}",
            params={"per_page": 100, "page": page, **params},
            timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        results.extend(batch)
        page += 1
    return results


def _fetch_file(file_path: str, branch: str) -> str | None:
    """Fetch raw file content from GitLab repository."""
    encoded = file_path.replace("/", "%2F")
    r = _SESSION.get(
        f"{BASE_API}/repository/files/{encoded}/raw",
        params={"ref": branch},
        timeout=30,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.text


def _extract_local_includes(ci_content: str) -> list[str]:
    """Parse local include paths from CI YAML content."""
    try:
        import yaml
        doc = yaml.safe_load(ci_content) or {}
        includes = doc.get("include") or []
        if isinstance(includes, dict):
            includes = [includes]
        paths = []
        for item in includes:
            if isinstance(item, dict) and "local" in item:
                paths.append(item["local"].lstrip("/"))
        return paths
    except Exception:
        # Fallback: regex
        return re.findall(r"local:\s*['\"]?([^\s'\"]+)['\"]?", ci_content)


def fetch_ci_files(branch: str, output_dir: Path) -> list[str]:
    """Fetch .gitlab-ci.yml and all local includes recursively."""
    fetched: list[str] = []
    queue = [".gitlab-ci.yml"]
    seen: set[str] = set()

    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)

        content = _fetch_file(path, branch)
        if content is None:
            print(f"  [SKIP] Not found: {path}")
            continue

        # Save file
        dest = output_dir / ("gitlab-ci.yml" if path == ".gitlab-ci.yml" else f"includes/{path}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        fetched.append(path)
        print(f"  [SAVED] {path}  ->  {dest.relative_to(output_dir)}")

        # Enqueue new local includes
        for include_path in _extract_local_includes(content):
            if include_path not in seen:
                queue.append(include_path)

    return fetched


def fetch_variables(output_dir: Path) -> list[dict]:
    """Fetch project and group CI/CD variables."""
    try:
        variables = _get_all_pages("/variables")
    except requests.HTTPError as exc:
        print(f"  [WARN] Could not fetch variables: {exc}")
        return []

    # Mask sensitive values
    safe = []
    for v in variables:
        entry = {k: v[k] for k in ("key", "variable_type", "protected", "masked", "environment_scope") if k in v}
        entry["value"] = "***" if v.get("masked") else v.get("value", "")
        safe.append(entry)

    (output_dir / "variables.json").write_text(
        json.dumps(safe, indent=2), encoding="utf-8"
    )
    print(f"  [SAVED] variables.json ({len(safe)} variables)")
    return safe


def fetch_runners(output_dir: Path) -> list[dict]:
    """Fetch runners available to this project."""
    try:
        runners = _get_all_pages("/runners")
    except requests.HTTPError as exc:
        print(f"  [WARN] Could not fetch runners: {exc}")
        return []

    summary = []
    for r in runners:
        summary.append({
            "id": r.get("id"),
            "description": r.get("description"),
            "status": r.get("status"),
            "is_shared": r.get("is_shared"),
            "tag_list": r.get("tag_list", []),
            "platform": r.get("platform"),
            "architecture": r.get("architecture"),
        })

    (output_dir / "runners.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"  [SAVED] runners.json ({len(summary)} runners)")
    return summary


def fetch_schedules(output_dir: Path) -> list[dict]:
    """Fetch pipeline schedules."""
    try:
        schedules = _get_all_pages("/pipeline_schedules")
    except requests.HTTPError as exc:
        print(f"  [WARN] Could not fetch schedules: {exc}")
        return []

    (output_dir / "schedules.json").write_text(
        json.dumps(schedules, indent=2), encoding="utf-8"
    )
    print(f"  [SAVED] schedules.json ({len(schedules)} schedules)")
    return schedules


def write_summary(
    branch: str,
    ci_files: list[str],
    variables: list[dict],
    runners: list[dict],
    schedules: list[dict],
    output_dir: Path,
) -> None:
    lines = [
        "GitLab Project Configuration Snapshot",
        "=" * 50,
        f"Project ID : {config.PROJECT_ID}",
        f"GitLab URL : {config.GITLAB_URL}",
        f"Branch     : {branch}",
        "",
        f"CI Files   : {len(ci_files)}",
    ]
    for f in ci_files:
        lines.append(f"  - {f}")
    lines += [
        "",
        f"Variables  : {len(variables)} ({sum(1 for v in variables if v.get('masked'))} masked)",
        f"Runners    : {len(runners)}",
    ]
    for r in runners:
        tags = ", ".join(r.get("tag_list") or []) or "(no tags)"
        lines.append(f"  - {r.get('description', r.get('id'))} [{r.get('status')}] tags: {tags}")
    lines += [
        "",
        f"Schedules  : {len(schedules)}",
    ]
    for s in schedules:
        lines.append(f"  - {s.get('description', '?')} ({s.get('cron', '?')}) active={s.get('active')}")

    (output_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  [SAVED] summary.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and snapshot a GitLab project's CI configuration.")
    parser.add_argument("--output-dir", default="gitlab_config", help="Output directory (default: gitlab_config)")
    parser.add_argument("--branch", default=config.BRANCH, help=f"Branch to fetch from (default: {config.BRANCH})")
    args = parser.parse_args()

    config.require("GITLAB_TOKEN", "PROJECT_ID")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nFetching GitLab config for project {config.PROJECT_ID} @ {args.branch}…")
    print(f"Output: {output_dir.resolve()}\n")

    ci_files = fetch_ci_files(args.branch, output_dir)
    variables = fetch_variables(output_dir)
    runners = fetch_runners(output_dir)
    schedules = fetch_schedules(output_dir)
    write_summary(args.branch, ci_files, variables, runners, schedules, output_dir)

    print(f"\nDone. Snapshot written to: {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

RESERVED = {"stages", "variables", "include", "default", "workflow", "image", "services", "before_script", "after_script", "cache", "pages"}


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def _load_with_includes(root: Path) -> dict:
    merged: dict = {}
    base = _load_yaml(root)
    includes = base.get("include") or []
    if isinstance(includes, dict):
        includes = [includes]
    for k, v in base.items():
        if k != "include":
            merged[k] = v
    for item in includes:
        if not isinstance(item, dict) or "local" not in item:
            continue
        local_path = item["local"].lstrip("/")
        # Try direct relative path first, then the 'includes/' subdirectory
        # (fetch_gitlab_config.py saves includes under <output>/includes/<path>)
        candidates = [
            (root.parent / local_path).resolve(),
            (root.parent / "includes" / local_path).resolve(),
        ]
        p = next((c for c in candidates if c.exists()), None)
        if p is None:
            continue
        inc = _load_yaml(p)
        for k, v in inc.items():
            if k != "include":
                merged[k] = v
    return merged


def build_graph(ci_path: Path) -> dict:
    doc = _load_with_includes(ci_path)
    stages = doc.get("stages") or []
    jobs: dict[str, dict] = {}
    for name, cfg in doc.items():
        if name in RESERVED or str(name).startswith(".") or not isinstance(cfg, dict):
            continue
        stage = cfg.get("stage") or (stages[0] if stages else "build")
        needs = cfg.get("needs") or []
        need_names = []
        for n in needs:
            if isinstance(n, str):
                need_names.append(n)
            elif isinstance(n, dict) and n.get("job"):
                need_names.append(str(n["job"]))
        jobs[name] = {"stage": stage, "needs": need_names}

    adjacency = {j: [] for j in jobs}
    upstream = {j: [] for j in jobs}
    for job, meta in jobs.items():
        for dep in meta["needs"]:
            if dep in jobs:
                adjacency[dep].append(job)
                upstream[job].append(dep)

    return {
        "root": ci_path.name,
        "strategy": "gitlab-yaml",
        "stages": stages,
        "jobs": {
            name: {
                "stage": meta["stage"],
                "downstream_jobs": sorted(adjacency.get(name, [])),
                "upstream_jobs": sorted(upstream.get(name, [])),
                "level": -1,
            }
            for name, meta in jobs.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GitLab dependency graph from CI YAML")
    parser.add_argument("--ci", default=".gitlab-ci.yml")
    parser.add_argument("--output", default="gitlab_graph.json")
    args = parser.parse_args()

    graph = build_graph(Path(args.ci).resolve())
    Path(args.output).write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"Wrote graph to {args.output} with {len(graph['jobs'])} jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

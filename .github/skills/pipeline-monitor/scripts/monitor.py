#!/usr/bin/env python3
"""Monitor GitLab pipeline hierarchy (root + child + grandchild)."""

import argparse
import time
from collections import Counter

import gitlab

import config

TERMINAL = {"success", "failed", "canceled", "skipped"}


def snapshot_pipeline(project, pid: int, indent: str = ""):
    p = project.pipelines.get(pid)
    print(f"{indent}Pipeline {p.id}: status={p.status} source={p.attributes.get('source')} url={p.web_url}")

    jobs = p.jobs.list(get_all=True)
    bridges = p.bridges.list(get_all=True)

    if jobs:
        counts = Counter(j.status for j in jobs)
        print(f"{indent}  jobs: {dict(sorted(counts.items()))}")

        pending_jobs = [j for j in jobs if j.status == "pending"]
        for j in pending_jobs[:5]:
            jf = project.jobs.get(j.id)
            tags = jf.attributes.get("tag_list")
            stage = jf.attributes.get("stage")
            print(f"{indent}    pending job: {jf.name} (stage={stage}, tags={tags})")

    if bridges:
        counts = Counter(b.status for b in bridges)
        print(f"{indent}  bridges: {dict(sorted(counts.items()))}")

        for b in bridges[:12]:
            a = b.attributes
            d = a.get("downstream_pipeline") or {}
            print(
                f"{indent}    bridge {a.get('name')}: {a.get('status')} -> "
                f"child {d.get('id')} ({d.get('status')})"
            )

    child_ids = [
        (b.attributes.get("downstream_pipeline") or {}).get("id")
        for b in bridges
        if (b.attributes.get("downstream_pipeline") or {}).get("id")
    ]
    return p.status, child_ids


def resolve_root_pipeline(project, branch: str, explicit_id: int | None) -> int:
    if explicit_id:
        return explicit_id

    candidates = project.pipelines.list(ref=branch, order_by="id", sort="desc", per_page=10, get_all=False)
    if not candidates:
        raise SystemExit(f"No pipelines found on branch '{branch}'.")
    return candidates[0].id


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor GitLab migration pipeline hierarchy.")
    parser.add_argument("--pipeline-id", type=int, default=None, help="Root pipeline ID to monitor")
    parser.add_argument("--snapshots", type=int, default=12, help="Number of snapshots")
    parser.add_argument("--interval", type=int, default=20, help="Seconds between snapshots")
    args = parser.parse_args()

    gl = gitlab.Gitlab(config.GITLAB_URL, private_token=config.GITLAB_TOKEN)
    gl.auth()
    project = gl.projects.get(config.PROJECT_ID)

    root_id = resolve_root_pipeline(project, config.BRANCH, args.pipeline_id)
    print(f"Monitoring root pipeline {root_id} on branch '{config.BRANCH}'")

    for i in range(1, args.snapshots + 1):
        print("\n" + "=" * 90)
        print(f"Snapshot {i} @ {time.strftime('%H:%M:%S')}")

        root_status, child_ids = snapshot_pipeline(project, root_id)
        all_terminal = root_status in TERMINAL

        for cid in child_ids:
            child_status, gc_ids = snapshot_pipeline(project, cid, indent="  ")
            all_terminal = all_terminal and (child_status in TERMINAL)

            for gcid in gc_ids[:10]:
                gc_status, _ = snapshot_pipeline(project, gcid, indent="    ")
                all_terminal = all_terminal and (gc_status in TERMINAL)

        if all_terminal:
            print("\nAll observed pipelines are in terminal states. Stopping monitor.")
            break

        if i < args.snapshots:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()

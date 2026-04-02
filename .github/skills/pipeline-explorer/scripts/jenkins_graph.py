#!/usr/bin/env python3
"""
jenkins_graph.py
----------------
Build a dependency graph from Jenkins MultiJob config.xml files that shows
the true execution flow: which jobs run in parallel (same phase) versus
sequentially (different phases).

Unlike pipeline_tree.txt, which lists downstream jobs flat under a parent,
this graph groups jobs into their declared phases so the execution model is
visible at a glance.

Default output: plugin_artifacts/dependency_graph.txt

Usage:
        python .github/skills/pipeline-explorer/scripts/jenkins_graph.py fetch_xml/jenkins_graph_xml.json
        python .github/skills/pipeline-explorer/scripts/jenkins_graph.py fetch_xml/jenkins_graph_xml.json --config-dir fetch_xml/config_xml --output plugin_artifacts/dependency_graph.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

# ── Defaults ───────────────────────────────────────────────────────────────────
_DEFAULT_JSON = Path("fetch_xml") / "jenkins_graph_xml.json"
_DEFAULT_OUTPUT = Path("plugin_artifacts") / "dependency_graph.txt"

# ── Tree drawing chars ─────────────────────────────────────────────────────────
_PIPE  = "│   "
_TEE   = "├── "
_LAST  = "└── "
_BLANK = "    "


# ══════════════════════════════════════════════════════════════════════════════
# Unified step extraction from config.xml
# ══════════════════════════════════════════════════════════════════════════════

def _load_steps(job_name: str, known_jobs: set[str], config_dir: Path) -> list[dict] | None:
    """
    Parse a job's config.xml and return all execution steps in document order.

    Handles three trigger forms:
      - ``<com.tikal...MultiJobBuilder>``                  parallel phase (element-tag form)
      - ``<buildStep class="...MultiJobBuilder" ...>``     parallel phase (attribute-class form,
                                                           used inside SingleConditionalBuilder)
      - ``<projects>Job1, Job2</projects>``                sequential TriggerBuilder invocation

    Returns a list of step dicts, or None if no steps found:
      {"kind": "phase", "name": str,  "jobs": [str]}   – all jobs run in parallel
      {"kind": "seq",   "jobs": [str]}                  – jobs triggered sequentially
    """
    xml_path = config_dir / f"{job_name}.xml"
    if not xml_path.exists():
        return None
    try:
        raw = xml_path.read_text(encoding="utf-8", errors="replace")
        root_el = ET.fromstring(raw)
    except (OSError, ET.ParseError):
        return None

    ns = "com.tikal.jenkins.plugins.multijob"
    steps_with_pos: list[tuple[int, dict]] = []

    # ── Phase steps ──────────────────────────────────────────────────────────
    # Walk the full element tree in document order; for each MultiJobBuilder
    # (both the element-tag form and the buildStep-class-attr form), record a
    # "phase" step.  We find the raw-text position by searching for the
    # <phaseName> string so that duplicate phase names are handled correctly
    # (the search offset advances after each match).
    _pos_cursor = 0
    for el in root_el.iter():
        is_tag  = (el.tag == f"{ns}.MultiJobBuilder")
        is_attr = (el.tag == "buildStep" and
                   f"{ns}.MultiJobBuilder" in el.get("class", ""))
        if not (is_tag or is_attr):
            continue

        pname_el = el.find("phaseName")
        pname = (pname_el.text.strip()
                 if pname_el is not None and pname_el.text else "(unnamed phase)")

        jobs: list[str] = [
            pjc.findtext("jobName").strip()
            for pjc in el.iter(f"{ns}.PhaseJobsConfig")
            if pjc.findtext("jobName") and pjc.findtext("jobName").strip()
        ]
        if not jobs:
            continue

        # Locate in raw text (advancing cursor handles duplicate phase names)
        if is_tag:
            needle = f"<phaseName>{pname}</phaseName>"
        else:
            needle = f'class="{ns}.MultiJobBuilder"'
        pos = raw.find(needle, _pos_cursor)
        if pos < 0:
            pos = raw.find(needle)        # fallback without offset constraint
        if pos >= 0:
            _pos_cursor = pos + 1

        steps_with_pos.append((pos if pos >= 0 else len(raw),
                                {"kind": "phase", "name": pname, "jobs": jobs}))

    # ── Sequential steps: <projects> tags (TriggerBuilder / BuildTrigger) ────
    for m in re.finditer(r"<projects>\s*([^<]+?)\s*</projects>", raw):
        known = [j.strip() for j in m.group(1).split(",")
                 if j.strip() in known_jobs]
        if known:
            steps_with_pos.append((m.start(), {"kind": "seq", "jobs": known}))

    if not steps_with_pos:
        return None

    steps_with_pos.sort(key=lambda x: x[0])

    # Deduplicate seq steps (same job can appear in multiple TriggerBuilder
    # entries; keep only the first occurrence).
    seen_seq: set[str] = set()
    merged: list[dict] = []
    for _, step in steps_with_pos:
        if step["kind"] == "seq":
            fresh = [j for j in step["jobs"] if j not in seen_seq]
            seen_seq.update(fresh)
            if fresh:
                merged.append({"kind": "seq", "jobs": fresh})
        else:
            merged.append(step)

    return merged if merged else None


# ══════════════════════════════════════════════════════════════════════════════
# Recursive renderer
# ══════════════════════════════════════════════════════════════════════════════

def _render_job(
    job_name: str,
    all_jobs: dict,
    config_steps: dict[str, list[dict]],
    prefix: str,
    is_last: bool,
    seen_jobs: set[str],
    path: set[str],
    lines: list[str],
) -> None:
    """Recursively render a job and its children with phase/step grouping."""
    connector = _LAST if is_last else _TEE
    already   = job_name in seen_jobs
    suffix    = "" if already else " [new]"
    lines.append(f"{prefix}{connector}{job_name}{suffix}")

    # Cycle guard
    if job_name in path:
        return
    seen_jobs.add(job_name)

    child_prefix = prefix + (_BLANK if is_last else _PIPE)
    new_path = path | {job_name}

    steps = config_steps.get(job_name)
    if steps:
        _render_steps(steps, all_jobs, config_steps, child_prefix,
                      seen_jobs, new_path, lines)
        return

    # ── Fallback: use downstream_jobs from JSON ───────────────────────────
    downstream = all_jobs.get(job_name, {}).get("downstream_jobs", [])
    for di, djob in enumerate(downstream):
        djob_is_last = (di == len(downstream) - 1)
        _render_job(djob, all_jobs, config_steps,
                    child_prefix, djob_is_last, seen_jobs, new_path, lines)


def _render_steps(
    steps: list[dict],
    all_jobs: dict,
    config_steps: dict[str, list[dict]],
    child_prefix: str,
    seen_jobs: set[str],
    new_path: set[str],
    lines: list[str],
) -> None:
    """Render a step list (phases + sequential steps) under a parent job."""
    has_phases = any(s["kind"] == "phase" for s in steps)
    step_num = 0

    for si, step in enumerate(steps):
        step_is_last = (si == len(steps) - 1)

        if step["kind"] == "phase":
            step_num += 1
            jobs_in_phase = step["jobs"]
            parallel_label = " ⟳ parallel" if len(jobs_in_phase) > 1 else ""
            phase_connector = _LAST if step_is_last else _TEE
            phase_prefix    = child_prefix + (_BLANK if step_is_last else _PIPE)
            lines.append(f"{child_prefix}{phase_connector}"
                         f"[PHASE {step_num}: \"{step['name']}\"]{parallel_label}")
            for ji, pjob in enumerate(jobs_in_phase):
                job_is_last = (ji == len(jobs_in_phase) - 1)
                _render_job(pjob, all_jobs, config_steps,
                            phase_prefix, job_is_last, seen_jobs, new_path, lines)

        else:  # "seq"
            seq_jobs = step["jobs"]
            if has_phases:
                # Mixed context: wrap seq jobs under a numbered step group
                step_num += 1
                seq_connector = _LAST if step_is_last else _TEE
                seq_prefix    = child_prefix + (_BLANK if step_is_last else _PIPE)
                seq_label = " ⟳ parallel" if len(seq_jobs) > 1 else " sequential"
                lines.append(f"{child_prefix}{seq_connector}"
                             f"[STEP {step_num}: sequential{' (parallel triggers)' if len(seq_jobs) > 1 else ''}]")
                for ji, sjob in enumerate(seq_jobs):
                    job_is_last = (ji == len(seq_jobs) - 1)
                    _render_job(sjob, all_jobs, config_steps,
                                seq_prefix, job_is_last, seen_jobs, new_path, lines)
            else:
                # Pure-seq context: show jobs directly as flat children
                for ji, sjob in enumerate(seq_jobs):
                    job_is_last = step_is_last and (ji == len(seq_jobs) - 1)
                    _render_job(sjob, all_jobs, config_steps,
                                child_prefix, job_is_last, seen_jobs, new_path, lines)


# ══════════════════════════════════════════════════════════════════════════════
# Main builder
# ══════════════════════════════════════════════════════════════════════════════

def build_dependency_graph(data: dict, config_dir: Path | None = None) -> str:
    """Build the full dependency graph string from the JSON registry."""
    jobs: dict = data.get("jobs", {})
    known_jobs: set[str] = set(jobs.keys())

    # Pre-load unified step data for every job
    config_steps: dict[str, list[dict]] = {}
    if config_dir is not None:
        for jname in jobs:
            steps = _load_steps(jname, known_jobs, config_dir)
            if steps:
                config_steps[jname] = steps

    # Find root (level 0)
    root = next(
        (name for name, meta in jobs.items() if meta.get("level", -1) == 0),
        next(iter(jobs), None),
    )
    if root is None:
        return "(no jobs found)"

    lines: list[str] = []

    # Legend
    lines += [
        "DEPENDENCY GRAPH — Execution Flow",
        "=" * 60,
        "  [new]              : job not seen before in this traversal",
        "  [PHASE N: \"...\"]   : jobs inside run IN PARALLEL",
        "  [STEP N: sequential]: job(s) triggered sequentially",
        "  ⟳ parallel         : multiple jobs run simultaneously",
        "  (no step/phase)    : jobs triggered SEQUENTIALLY (fallback)",
        "=" * 60,
        "",
        root,
    ]

    # Render root's children
    seen_jobs: set[str] = {root}

    steps = config_steps.get(root)
    if steps:
        _render_steps(steps, jobs, config_steps, "", seen_jobs, {root}, lines)
    else:
        downstream = jobs.get(root, {}).get("downstream_jobs", [])
        for di, djob in enumerate(downstream):
            djob_is_last = (di == len(downstream) - 1)
            _render_job(djob, jobs, config_steps,
                        "", djob_is_last, seen_jobs, {root}, lines)

    return "\n".join(lines)


def write_dependency_graph(data: dict, output_path: Path, config_dir: Path | None = None) -> None:
    graph = build_dependency_graph(data, config_dir=config_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(graph, encoding="utf-8")
    print(f"  Dependency graph saved → {output_path}  ({graph.count(chr(10)) + 1} lines)")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Build Jenkins dependency graph from exported job JSON")
    parser.add_argument("json_path", nargs="?", default=str(_DEFAULT_JSON), help="Path to jenkins_graph_xml.json")
    parser.add_argument("--config-dir", help="Directory containing Jenkins config.xml files; defaults to <json_path parent>/config_xml")
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT), help="Output dependency graph text path")
    args = parser.parse_args()

    json_path = Path(args.json_path).resolve()
    if not json_path.exists():
        print(f"ERROR: JSON not found: {json_path}", file=sys.stderr)
        sys.exit(1)

    config_dir = Path(args.config_dir).resolve() if args.config_dir else (json_path.parent / "config_xml").resolve()
    if not config_dir.exists():
        print(f"WARNING: config directory not found: {config_dir}; falling back to downstream_jobs only", file=sys.stderr)
        config_dir = None

    data = json.loads(json_path.read_text(encoding="utf-8"))
    write_dependency_graph(data, Path(args.output), config_dir=config_dir)


if __name__ == "__main__":
    main()

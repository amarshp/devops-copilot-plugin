#!/usr/bin/env python3
"""Generate repetitive GitLab YAML jobs from a reusable JSON template model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def render_job(job_name: str, stage: str, template: dict, variables: dict, needs: list[dict]) -> dict:
    job = {
        "extends": template.get("extends", ".job-template"),
        "stage": stage,
        "variables": variables,
        "needs": needs,
    }
    if template.get("before_script"):
        job["before_script"] = template["before_script"]
    if template.get("script"):
        job["script"] = template["script"]
    return {job_name: job}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate repetitive stage YAML files from a template JSON")
    parser.add_argument("--spec", required=True, help="JSON spec containing groups/templates")
    parser.add_argument("--output-dir", required=True, help="Output directory for generated YAML files")
    args = parser.parse_args()

    import yaml

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    template = spec.get("template", {})
    groups = spec.get("groups", [])

    generated = 0
    for group in groups:
        file_name = group["file"]
        stage = group["stage"]
        base = group["job_prefix"]

        jobs_doc = {}
        for part in group.get("parts", []):
            job_name = f"{base}.{part['name']}"
            variables = part.get("variables", {})
            needs = part.get("needs", [])
            jobs_doc.update(render_job(job_name, stage, template, variables, needs))

        out_path = out_dir / file_name
        out_path.write_text(yaml.safe_dump(jobs_doc, sort_keys=False, allow_unicode=False), encoding="utf-8")
        print(f"Generated {out_path}")
        generated += 1

    print(f"Done. Generated {generated} YAML files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

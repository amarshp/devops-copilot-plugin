import argparse
import json
from pathlib import Path

from convert_job import DEFAULT_OUTPUT_DIR, DEFAULT_STAGE_DICT, convert_job, sanitize_job_name
from validate_yaml import validate_yaml_content


def load_stage_dict(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ordered_jobs(stage_dict: dict) -> list[tuple[int, str]]:
    jobs = stage_dict["jobs"]
    return sorted(((entry["level"], job_name) for job_name, entry in jobs.items()), reverse=True)


def write_root_pipeline(stage_dict: dict, output_dir: Path) -> None:
    root_pipeline_path = output_dir.parent.parent / ".gitlab-ci.yml"
    includes = []
    for _level, job_name in ordered_jobs(stage_dict):
        file_name = sanitize_job_name(job_name)
        if (output_dir / file_name).exists():
            includes.append(f"  - local: ci/stages/{file_name}")

    lines = ["stages:"]
    lines.extend([f"  - {stage}" for stage in stage_dict["stage_sequence"]])
    lines.append("")
    lines.append("include:")
    lines.extend(includes or ["  - local: ci/stages/placeholder.yml"])
    root_pipeline_path.parent.mkdir(parents=True, exist_ok=True)
    root_pipeline_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote root pipeline to {root_pipeline_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bottom-up orchestrator for generating GitLab YAML in dependency order.")
    parser.add_argument("--stage-dict", default=str(DEFAULT_STAGE_DICT), help="Path to the stage dictionary JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory where generated stage YAMLs are written.")
    parser.add_argument("--model", default="claude-sonnet-4.6", help="LLM model name.")
    parser.add_argument("--max-jobs", type=int, default=None, help="Optional job limit for dry runs.")
    parser.add_argument("--start-after", help="Optional job name after which generation should resume.")
    args = parser.parse_args()

    stage_dict = load_stage_dict(Path(args.stage_dict))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    started = args.start_after is None
    for _level, job_name in ordered_jobs(stage_dict):
        if not started:
            if job_name == args.start_after:
                started = True
            continue

        if args.max_jobs is not None and generated >= args.max_jobs:
            break

        output_path = output_dir / sanitize_job_name(job_name)
        yaml_str = convert_job(job_name, Path(args.stage_dict), output_dir, model=args.model)
        output_path.write_text(yaml_str, encoding="utf-8")
        generated += 1
        print(f"Generated {job_name} -> {output_path.name}")

        try:
            valid, errors, _payload = validate_yaml_content(yaml_str)
            print(f"  Lint valid: {valid}")
            if errors:
                for error in errors:
                    print(f"  - {error}")
        except Exception as exc:
            print(f"  Remote lint unavailable: {exc}")

    write_root_pipeline(stage_dict, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
import yaml

from fetch_jenkinsfile import fetch_jenkinsfile
from llm_call_template import DEFAULT_MODEL, call_llm
from prompts import build_messages


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_STAGE_DICT = Path("plugin_artifacts") / "stage_dict.json"
DEFAULT_OUTPUT_DIR = Path("migrated_yamls") / "ci" / "stages"

load_dotenv()


def sanitize_job_name(job_name: str) -> str:
    return job_name.replace("/", "_").replace(" ", "_") + ".yml"


def _tail_text(text: str, max_lines: int = 250) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[-max_lines:])


def load_stage_dict(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_downstream_yamls(stage_dict: dict, stage_dict_entry: dict, output_dir: Path) -> dict[str, dict[str, object]]:
    snippets: dict[str, dict[str, object]] = {}
    for job_name in stage_dict_entry.get("downstream_jobs", []):
        candidate = output_dir / sanitize_job_name(job_name)
        if candidate.exists():
            downstream_entry = stage_dict["jobs"].get(job_name, {})
            snippets[job_name] = {
                "file_path": str(candidate),
                "job_name": job_name,
                "default_stage": downstream_entry.get("default_stage"),
                "allowed_stages": downstream_entry.get("allowed_stages", []),
                "note": "Separate include file already exists; reference by exact job name only.",
            }
    return snippets


ROOT_LEVEL_RESERVED_KEYS = {
    "stages",
    "variables",
    "include",
    "workflow",
    "default",
    "image",
    "services",
    "cache",
    "before_script",
    "after_script",
}


def validate_job_isolation(job_name: str, yaml_str: str, stage_dict: dict) -> None:
    try:
        parsed = yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Generated YAML is not syntactically valid: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Generated YAML must parse to a mapping at the root.")

    visible_jobs = [
        key for key, value in parsed.items()
        if key not in ROOT_LEVEL_RESERVED_KEYS and not str(key).startswith(".") and isinstance(value, dict)
    ]
    downstream_jobs = set(stage_dict["jobs"][job_name].get("downstream_jobs", []))
    redefined = sorted(downstream_jobs.intersection(visible_jobs))
    if redefined:
        raise ValueError(
            "Generated file redefines downstream jobs that must stay in their own YAML files: "
            + ", ".join(redefined)
        )


def maybe_fetch_jenkinsfile(stage_dict_entry: dict) -> str | None:
    pipeline_scm = stage_dict_entry.get("pipeline_scm")
    if not pipeline_scm:
        return None

    xml_path = Path(stage_dict_entry["xml_path"])
    token = os.environ.get("GITLAB_USER_TOKEN") or os.environ.get("GITLAB_TOKEN")
    if not token:
        return None

    try:
        _metadata, content = fetch_jenkinsfile(xml_path, token)
        return content
    except Exception as exc:
        return f"# Jenkinsfile fetch failed; falling back to XML + logs\n# Reason: {exc}"


def convert_job(job_name: str, stage_dict_path: Path, output_dir: Path, model: str = DEFAULT_MODEL, lint_errors: list[str] | None = None) -> str:
    stage_dict = load_stage_dict(stage_dict_path)
    job_entry = stage_dict["jobs"][job_name]

    xml_content = Path(job_entry["xml_path"]).read_text(encoding="utf-8")
    log_path = Path(job_entry["log_path"])
    build_log = _tail_text(log_path.read_text(encoding="utf-8", errors="replace"), max_lines=250) if log_path.exists() else ""
    downstream_yamls = load_downstream_yamls(stage_dict, job_entry, output_dir)
    jenkinsfile_content = maybe_fetch_jenkinsfile(job_entry)

    retry_feedback = list(lint_errors or [])
    max_attempts = 3
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        messages = build_messages(
            job_name=job_name,
            xml_content=xml_content,
            build_log=build_log,
            stage_dict_entry=job_entry,
            downstream_yamls=downstream_yamls,
            jenkinsfile_content=jenkinsfile_content,
            lint_errors=retry_feedback,
        )
        yaml_str = call_llm(messages, model=model)
        try:
            validate_job_isolation(job_name, yaml_str, stage_dict)
            return yaml_str
        except ValueError as exc:
            last_error = exc
            retry_feedback.append(f"Structural isolation error from previous attempt {attempt}: {exc}")

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Failed to generate YAML for {job_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a single Jenkins job to GitLab CI YAML using the stage dictionary.")
    parser.add_argument("job_name", help="Jenkins job name to convert.")
    parser.add_argument("--stage-dict", default=str(DEFAULT_STAGE_DICT), help="Path to the stage dictionary JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory where generated YAML files are stored.")
    parser.add_argument("--output-file", help="Optional explicit output file.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model name.")
    parser.add_argument("--lint-error", action="append", default=[], help="Lint error message to feed back into regeneration. Can be specified multiple times.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_str = convert_job(
        args.job_name,
        Path(args.stage_dict),
        output_dir,
        model=args.model,
        lint_errors=args.lint_error,
    )

    if args.output_file:
        output_path = Path(args.output_file)
        output_path.write_text(yaml_str, encoding="utf-8")
        print(f"Wrote YAML to {output_path}")
    else:
        print(yaml_str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
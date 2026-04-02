import argparse
import json
from pathlib import Path

import requests
import yaml

import config


def validate_yaml_content(content: str) -> tuple[bool, list[str], dict]:
    if not config.GITLAB_TOKEN or not config.PROJECT_ID:
        raise RuntimeError("GITLAB_TOKEN and GITLAB_PROJECT_ID must be configured in the project .env file")

    url = f"{config.GITLAB_URL.rstrip('/')}/api/v4/projects/{config.PROJECT_ID}/ci/lint"
    response = requests.post(
        url,
        headers={
            "PRIVATE-TOKEN": config.GITLAB_TOKEN,
            "Content-Type": "application/json",
        },
        json={
            "content": content,
            "dry_run": False,
            "include_jobs": True,
        },
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    valid = bool(payload.get("valid"))
    errors = list(payload.get("errors") or [])
    if payload.get("warnings"):
        errors.extend([f"WARNING: {warning}" for warning in payload.get("warnings", [])])
    return valid, errors, payload


def validate_yaml_syntax_locally(content: str) -> tuple[bool, list[str]]:
    try:
        list(yaml.safe_load_all(content))
        return True, []
    except yaml.YAMLError as exc:
        return False, [f"Local YAML parse error: {exc}"]


def _load_content(path_or_yaml: str) -> tuple[str, str]:
    candidate = Path(path_or_yaml)
    if candidate.exists():
        return candidate.read_text(encoding="utf-8"), str(candidate)
    return path_or_yaml, "<inline-content>"


def _load_yaml_document(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded or {}


def expand_local_includes(root_path: Path) -> str:
    root_doc = _load_yaml_document(root_path)
    merged: dict = {}

    for key, value in root_doc.items():
        if key != "include":
            merged[key] = value

    includes = root_doc.get("include") or []
    if isinstance(includes, dict):
        includes = [includes]

    for include in includes:
        if not isinstance(include, dict) or "local" not in include:
            continue
        include_path = (root_path.parent / include["local"]).resolve()
        include_doc = _load_yaml_document(include_path)
        include_doc.pop("stages", None)
        include_doc.pop("include", None)
        for key, value in include_doc.items():
            merged[key] = value

    return yaml.safe_dump(merged, sort_keys=False, allow_unicode=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GitLab CI YAML against project CI Lint.")
    parser.add_argument("yaml_input", help="Path to YAML file or inline YAML content.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON response.")
    parser.add_argument("--expand-local-includes", action="store_true", help="If yaml_input is a root YAML file, inline local includes before linting.")
    args = parser.parse_args()

    candidate = Path(args.yaml_input)
    if args.expand_local_includes and candidate.exists():
        content = expand_local_includes(candidate)
        source = f"{candidate} (expanded local includes)"
    else:
        content, source = _load_content(args.yaml_input)

    try:
        valid, errors, payload = validate_yaml_content(content)
    except (requests.RequestException, RuntimeError) as exc:
        local_valid, local_errors = validate_yaml_syntax_locally(content)
        print(f"Source: {source}")
        print("Valid : False")
        print("Messages:")
        print(f"- Remote GitLab CI lint unavailable: {exc}")
        if local_valid:
            print("- Local YAML parse succeeded, so the blocker is configuration, connectivity, or auth rather than YAML syntax.")
        else:
            for error in local_errors:
                print(f"- {error}")
        print("- Manual step: fix .env credentials or GitLab access, then rerun validation.")
        return 2

    print(f"Source: {source}")
    print(f"Valid : {valid}")
    if errors:
        print("Messages:")
        for error in errors:
            print(f"- {error}")

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))

    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
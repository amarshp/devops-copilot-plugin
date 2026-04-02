#!/usr/bin/env python3
"""
Push a YAML tree to the configured GitLab project, then wait for the pipeline.

Required environment variables (set in the project .env file):
  GITLAB_TOKEN        Personal Access Token with `api` scope
  GITLAB_PROJECT_ID   Numeric project ID or "namespace/project"

Optional:
  GITLAB_URL          Default: https://gitlab.com
  GITLAB_BRANCH       Default: main
  POLL_INTERVAL       Seconds between status polls (default: 15)
  PIPELINE_TIMEOUT    Max seconds to wait for pipeline (default: 600)
"""

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

import gitlab
import gitlab.exceptions

import config

DEFAULT_SOURCE_DIR = Path("migrated_yamls")


def _safe_log_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def _extract_counts(text: str) -> tuple[int, int]:
    errors = 0
    warnings = 0
    for line in text.splitlines():
        error_match = re.search(r"(\d+) Error\(s\)", line)
        if error_match:
            errors = max(errors, int(error_match.group(1)))
        warning_match = re.search(r"(\d+) Warning\(s\)", line)
        if warning_match:
            warnings = max(warnings, int(warning_match.group(1)))
    return errors, warnings


def _require_env() -> None:
    required = {"GITLAB_TOKEN": "GITLAB_TOKEN", "PROJECT_ID": "GITLAB_PROJECT_ID"}
    missing = [env for attr, env in required.items() if not getattr(config, attr)]
    if missing:
        sys.exit(
            f"Error: the following environment variable(s) must be set: {', '.join(missing)}\n"
            "Create or update the project .env file and rerun."
        )


def _separator(char: str = "-", width: int = 60) -> str:
    return char * width


# -- Step 1: Connect -----------------------------------------------------------

def connect():
    _require_env()
    gl = gitlab.Gitlab(config.GITLAB_URL, private_token=config.GITLAB_TOKEN)
    gl.auth()
    project = gl.projects.get(config.PROJECT_ID)
    print(f"Connected  ->  {project.name_with_namespace}")
    print(f"Branch     ->  {config.BRANCH}")
    return gl, project


# -- Step 2: Load YAML files --------------------------------------------------

def load_yamls(source_dir: Path) -> dict[str, str]:
    """
    Walks a YAML source tree and maps each file to its repo path.
    e.g.  source/.gitlab-ci.yml             -> .gitlab-ci.yml
          source/ci/stages/build.yml        -> ci/stages/build.yml
    """
    if not source_dir.exists():
        sys.exit(f"Error: YAML source directory not found at {source_dir}")

    yamls: dict[str, str] = {}
    for path in sorted(source_dir.rglob("*.yml")):
        repo_path = path.relative_to(source_dir).as_posix()
        yamls[repo_path] = path.read_text(encoding="utf-8").replace("\r\n", "\n")

    # Also pick up .gitlab-ci.yml (starts with a dot – rglob catches it on most OSes,
    # but be explicit just in case)
    root_ci = source_dir / ".gitlab-ci.yml"
    if root_ci.exists():
        yamls[".gitlab-ci.yml"] = root_ci.read_text(encoding="utf-8").replace("\r\n", "\n")

    print(f"\nLoaded {len(yamls)} YAML file(s) from {source_dir}:")
    for p in sorted(yamls):
        print(f"  {p}")

    return yamls


# -- Step 3: Push to GitLab ---------------------------------------------------

def _ensure_branch_exists(project, branch: str) -> None:
    try:
        project.branches.get(branch)
    except gitlab.exceptions.GitlabGetError:
        default = project.default_branch or "main"
        print(f"Branch '{branch}' not found, creating from '{default}'...")
        project.branches.create({"branch": branch, "ref": default})
        print(f"Branch '{branch}' created.")


def _existing_paths(project, branch: str) -> set[str]:
    try:
        tree = project.repository_tree(ref=branch, recursive=True, get_all=True)
        return {item["path"] for item in tree}
    except gitlab.exceptions.GitlabGetError:
        return set()


def push_yamls(project, yamls: dict[str, str], branch: str, source_label: str, message: str = "") -> str | None:
    _ensure_branch_exists(project, branch)
    existing = _existing_paths(project, branch)

    actions = []
    for rel_path, content in yamls.items():
        actions.append(
            {
                "action": "update" if rel_path in existing else "create",
                "file_path": rel_path,
                "content": content,
                "encoding": "text",
            }
        )

    if not actions:
        print("No YAML files to push.")
        return None

    # Build a descriptive commit message so GitLab history is informative.
    # Callers should supply a short description via --message / -m.
    base = f"[ci-migration] {source_label} ({len(actions)} file(s))"
    commit_message = f"{base}\n\n{message.strip()}" if message.strip() else base

    commit = project.commits.create(
        {
            "branch": branch,
            "commit_message": commit_message,
            "actions": actions,
        }
    )
    print(f"\nPushed {len(actions)} file(s)  ->  commit {commit.id[:8]}")
    for action in actions:
        print(f"  [{action['action']:6s}]  {action['file_path']}")
    return commit.id


# -- Step 4: Detect/trigger pipeline ------------------------------------------

_AUTO_PIPELINE_WAIT = 30
_AUTO_PIPELINE_POLL = 3


def _find_pipeline_for_commit(project, commit_sha: str):
    pipelines = project.pipelines.list(sha=commit_sha, get_all=False)
    return pipelines[0] if pipelines else None


def get_or_trigger_pipeline(project, commit_sha: str | None, branch: str):
    if commit_sha:
        print(f"\nLooking for auto-created pipeline for commit {commit_sha[:8]}...")
        deadline = time.monotonic() + _AUTO_PIPELINE_WAIT
        while time.monotonic() < deadline:
            pipeline = _find_pipeline_for_commit(project, commit_sha)
            if pipeline:
                print(f"Found pipeline  ->  ID {pipeline.id}  status: {pipeline.status}")
                print(f"URL: {pipeline.web_url}")
                return pipeline
            remaining = int(deadline - time.monotonic())
            print(f"  No pipeline yet, waiting {_AUTO_PIPELINE_POLL}s ({remaining}s left)...")
            time.sleep(_AUTO_PIPELINE_POLL)
        print("No auto-created pipeline found after waiting, triggering manually...")
    else:
        print("\nNo new commit SHA available, triggering pipeline manually...")

    pipeline = project.pipelines.create({"ref": branch})
    print(f"Pipeline triggered  ->  ID {pipeline.id}")
    print(f"URL: {pipeline.web_url}")
    return pipeline


# -- Step 5: Wait for completion ----------------------------------------------

TERMINAL_STATUSES = {"success", "failed", "canceled", "skipped"}


def wait_for_pipeline(pipeline, timeout: int, poll_interval: int) -> str:
    print(f"\nPolling every {poll_interval}s (timeout {timeout}s)...")
    start = time.monotonic()
    while True:
        pipeline.refresh()
        status = pipeline.status
        elapsed = int(time.monotonic() - start)
        print(f"  [{elapsed:>4}s]  status: {status}")

        if status in TERMINAL_STATUSES:
            return status

        if time.monotonic() - start >= timeout:
            print(f"Timed out after {timeout}s.")
            return "timeout"

        time.sleep(poll_interval)


# -- Step 6: Fetch and print logs --------------------------------------------

def fetch_logs(project, pipeline) -> tuple[dict[str, str], list[dict[str, object]]]:
    pipeline = project.pipelines.get(pipeline.id)
    pipeline_jobs = pipeline.jobs.list(get_all=True)
    pipeline_bridges = pipeline.bridges.list(get_all=True)

    if not pipeline_jobs and pipeline_bridges:
        print("Pipeline has no runner jobs but has bridge/trigger jobs.")
        lines = [
            f"Pipeline ID : {pipeline.id}",
            f"Status      : {pipeline.status}",
            f"URL         : {pipeline.web_url}",
            "",
            "Bridge jobs:",
        ]
        for bridge in pipeline_bridges:
            attrs = bridge.attributes
            downstream = attrs.get("downstream_pipeline") or {}
            line = (
                f"- {attrs.get('name')} | status={attrs.get('status')}"
                f" | downstream_id={downstream.get('id')}"
                f" | downstream_status={downstream.get('status')}"
            )
            print(line)
            lines.append(line)
            if downstream.get("web_url"):
                lines.append(f"  downstream_url={downstream['web_url']}")
        return {"pipeline_bridges": "\n".join(lines)}, []

    if not pipeline_jobs:
        # Diagnostic: check YAML errors
        print("No jobs found for this pipeline.")
        diag = [
            f"Pipeline ID : {pipeline.id}",
            f"Status      : {pipeline.status}",
            f"URL         : {pipeline.web_url}",
            f"SHA         : {pipeline.sha}",
            "",
        ]
        yaml_errors = (pipeline.attributes.get("yaml_errors") or "").strip()
        if yaml_errors:
            diag += ["=== YAML Errors ===", yaml_errors]
            print(f"\n!! YAML errors:\n{yaml_errors}")
        else:
            try:
                lint = project.ci_lint.get(ref=pipeline.ref)
                if not lint.valid:
                    errors = "\n".join(lint.errors or [])
                    warnings = "\n".join(lint.warnings or [])
                    if errors:
                        diag += ["=== CI Lint Errors ===", errors]
                        print(f"\n!! CI lint errors:\n{errors}")
                    if warnings:
                        diag += ["=== CI Lint Warnings ===", warnings]
                        print(f"\n  Warnings:\n{warnings}")
                else:
                    diag.append("CI lint: config is valid (no YAML errors found)")
                    print("  CI lint reports config valid; no runner may be assigned.")
            except Exception as exc:
                diag.append(f"[CI lint unavailable: {exc}]")
                print(f"  CI lint unavailable: {exc}")
        return {"pipeline_diagnostic": "\n".join(diag)}, []

    logs: dict[str, str] = {}
    results: list[dict[str, object]] = []
    for pj in pipeline_jobs:
        job = project.jobs.get(pj.id)
        print(f"\n{_separator('=')}")
        print(f"  Job: {job.name}  |  Stage: {job.stage}  |  Status: {job.status}")
        print(_separator("="))
        try:
            raw = job.trace()
            log = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        except Exception as exc:
            log = f"[Could not retrieve log: {exc}]\n"
        logs[job.name] = log
        errors, warnings = _extract_counts(log)
        results.append(
            {
                "job": job.name,
                "status": job.status,
                "duration": getattr(job, "duration", None) or job.attributes.get("duration"),
                "msbuild_errors": errors,
                "msbuild_warnings": warnings,
            }
        )
        print(log)

    return logs, results


# -- Step 7: Save logs --------------------------------------------------------

def save_logs(logs: dict[str, str], job_results: list[dict[str, object]], output_dir: Path, pipeline_id: int, pipeline_status: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: dict[str, str] = {}
    for job_name, log in logs.items():
        safe = _safe_log_name(job_name)
        out = output_dir / f"p{pipeline_id}_{safe}.log"
        out.write_text(log, encoding="utf-8")
        saved_paths[job_name] = str(out)

    manifest_jobs = []
    for result in job_results:
        job_name = str(result.get("job", ""))
        manifest_jobs.append(
            {
                **result,
                "log_path": saved_paths.get(job_name, str(output_dir / f"p{pipeline_id}_{_safe_log_name(job_name)}.log")),
            }
        )

    manifest_path = output_dir / f"qc_manifest_{pipeline_id}.json"
    manifest_path.write_text(
        json.dumps(
            {
                "pipeline_id": pipeline_id,
                "pipeline_status": pipeline_status,
                "total_jobs": len(manifest_jobs),
                "jobs": manifest_jobs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nLogs saved to: {output_dir.resolve()}")
    print(f"Manifest saved to: {manifest_path.resolve()}")


# -- Main ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Push a YAML tree to GitLab and wait for the pipeline.")
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_SOURCE_DIR),
        help="Directory containing .gitlab-ci.yml and included YAML files",
    )
    parser.add_argument(
        "--logs-dir",
        default=str(Path("pipeline_logs")),
        help="Directory where fetched pipeline logs will be written",
    )
    parser.add_argument(
        "-m", "--message",
        required=True,
        help="Short description of the change (appended to the commit message body). "
             "Example: 'fix: BomCheck - use Workspace_Home in prereq Maven'",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    logs_dir = Path(args.logs_dir).resolve()

    # 1. Connect
    _gl, project = connect()

    # 2. Load YAMLs
    print(f"\n{_separator()}")
    yamls = load_yamls(source_dir)
    if not yamls:
        sys.exit(f"No YAML files found in {source_dir}")

    # 3. Push
    print(f"\n{_separator()}")
    commit_sha = push_yamls(project, yamls, config.BRANCH, source_dir.name, args.message)

    # 4. Detect auto-created pipeline or trigger manually
    print(f"\n{_separator()}")
    pipeline = get_or_trigger_pipeline(project, commit_sha, config.BRANCH)

    # 5. Wait
    print(f"\n{_separator()}")
    final_status = wait_for_pipeline(pipeline, config.PIPELINE_TIMEOUT, config.POLL_INTERVAL)
    print(f"\nPipeline finished  ->  {final_status.upper()}")

    # 6. Fetch logs
    print(f"\n{_separator()}")
    print("Fetching job logs...")
    logs, job_results = fetch_logs(project, pipeline)

    # 7. Save logs
    if logs:
        save_logs(logs, job_results, logs_dir, pipeline.id, final_status)

    # 8. Update migration dashboard
    _update_dashboard(pipeline.id)

    if final_status != "success":
        sys.exit(1)


def _update_dashboard(pipeline_id=None) -> None:
    """Refresh MIGRATION_STATUS.md after a push/run cycle."""
    try:
        cwd = Path.cwd()
        dashboard_path = Path(__file__).resolve().parents[2] / "j2gl-qc" / "scripts" / "migration_dashboard.py"
        spec = importlib.util.spec_from_file_location("migration_dashboard", dashboard_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load dashboard module from {dashboard_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.render(
            tree_path    = cwd / "fetch_xml" / "pipeline_tree.txt",
            registry_path= cwd / "fetch_xml" / "jenkins_graph_xml.json",
            history_path = cwd / "QC_RUN_HISTORY.md",
            qc_dir       = cwd / "qc_reports",
            log_dir      = cwd / "pipeline_logs",
            migrated_dir = cwd / "migrated_yamls",
            output_path  = cwd / "MIGRATION_STATUS.md",
        )
    except Exception as exc:
        print(f"[dashboard] Could not update MIGRATION_STATUS.md: {exc}")


if __name__ == "__main__":
    main()

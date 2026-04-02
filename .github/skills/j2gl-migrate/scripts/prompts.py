import json
from typing import Any


PLUGIN_MAPPING_TABLE = """
Jenkins feature -> GitLab approach
- parameterized-trigger -> variables + needs
- copyartifact -> artifacts + needs
- envinject -> variables / dotenv artifacts / before_script
- MultiJob parallel phase -> same stage or parallel:matrix where the job shape is identical
- MultiJob sequential phase -> later stage + explicit needs
- ws-cleanup -> PowerShell cleanup in before_script
- nodelabelparameter -> tags
- throttle-concurrents / build-blocker-plugin -> resource_group where needed
- BatchFile / Shell -> PowerShell script
- SystemGroovy display-name logic -> log output or # UNMIGRATABLE comment
""".strip()


SYSTEM_PROMPT = """
You convert Jenkins jobs into GitLab CI YAML for a Windows-first migration.

Hard rules:
- Output ONLY valid GitLab CI YAML. No markdown fences.
- All scripts must be PowerShell.
- Do not use when: manual.
- Do not use allow_failure: true.
- Prefer simple, functionally compatible implementations over 1:1 Jenkins emulation.
- Use the Jenkins XML structure as the primary source of orchestration.
- Use only stage names provided by the migration context. Do not invent new stage names unless they already appear in the supplied stage sequence.
- If Jenkinsfile content is available, use it as a primary source for pipeline jobs.
- If Jenkinsfile content is unavailable, use XML metadata plus logs.
- Logs are the behavior oracle: optimize for equivalent outcomes, artifacts, and ordering.
- Prefer hidden template jobs with extends: for reuse.
- Use parallel:matrix only when the same logical job is repeated with different parameters and matrix keeps the YAML clearer.
- For CopyArtifact patterns, create or consume real downstream-compatible artifacts using artifacts: and needs:.
- Do not place job-only keys like resource_group, tags, timeout, script, trigger, or needs at the YAML root.
- Hidden templates must start with a dot and non-template jobs must contain script:, run:, or valid trigger: syntax.
- Do not use trigger: to point at another job in the same pipeline. Model those cases as ordinary jobs with rules: and needs:.
- Avoid PowerShell here-strings (`@"` / `"@`) inside YAML block scalars because they frequently break YAML indentation. Prefer arrays, concatenated strings, or single-line assignments instead.
- For script:, every list item must be a string or block scalar only. Do not place YAML comments between script items.
- If a script line contains `:` followed by a space, prefer a block scalar (`- |`) instead of a plain inline scalar to avoid YAML parsing ambiguity.
- For the primary externally-referenced GitLab job that represents a Jenkins job, use the exact Jenkins job name as the job key.
- If a Jenkins job needs multiple helper jobs in one file, keep helper names unique and add a final exact-match aggregator job that depends on the helpers.
- If a downstream Jenkins job already exists as its own generated YAML/include file, do not copy it, wrap it, alias it, or re-implement it in the current file.
- Downstream Jenkins jobs that already have their own YAML files must be referenced only by exact downstream job name via needs:, stage ordering, and variables.
- Helper jobs in the current file are allowed only for build logic intrinsic to the current Jenkins job itself. Do not create helper jobs that stand in for downstream phase jobs that already exist separately.
- If functionality cannot be faithfully reproduced, emit a YAML comment in the closest relevant location in this form:
  # UNMIGRATABLE: <reason>

Plugin mapping:
{plugin_mapping}
""".strip()


def build_user_prompt(
    *,
    job_name: str,
    xml_content: str,
    build_log: str,
    stage_dict_entry: dict[str, Any],
    downstream_yamls: dict[str, Any] | None = None,
    jenkinsfile_content: str | None = None,
    lint_errors: list[str] | None = None,
) -> str:
    downstream_yamls = downstream_yamls or {}
    lint_errors = lint_errors or []

    sections = [
        f"Job name: {job_name}",
        "Stage dictionary entry:",
        json.dumps(stage_dict_entry, indent=2, sort_keys=True),
        "Allowed stage sequence for this migration:",
        json.dumps(stage_dict_entry.get("allowed_stage_sequence", []), indent=2),
        "Jenkins XML:",
        xml_content,
    ]

    if jenkinsfile_content:
        sections.extend([
            "Fetched Jenkinsfile content:",
            jenkinsfile_content,
        ])

    if build_log:
        sections.extend([
            "Jenkins build log:",
            build_log,
        ])

    if downstream_yamls:
        sections.extend([
            "Already converted downstream jobs available as separate included files:",
            json.dumps(downstream_yamls, indent=2, sort_keys=True),
        ])

    if lint_errors:
        sections.extend([
            "Previous GitLab CI lint errors to fix:",
            "\n".join(lint_errors),
        ])

    sections.extend([
        "Generation guidance:",
        "- Preserve logical flow and artifact contracts.",
        "- For compatibility or temporary placeholder behavior, emit small PowerShell steps that surface expected state.",
        "- If the job is repeated with different parameter sets, prefer extends or matrix instead of duplicating boilerplate.",
        "- If a downstream job listed above already exists as a separate include file, reference it by exact job name only and do not inline or wrap its implementation here.",
        "- The only visible non-hidden jobs allowed in this file are the exact current job and any intrinsic helpers for the current job. Downstream child jobs must never appear as job keys here.",
    ])

    return "\n\n".join(sections)


def build_messages(**kwargs: Any) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(plugin_mapping=PLUGIN_MAPPING_TABLE),
        },
        {
            "role": "user",
            "content": build_user_prompt(**kwargs),
        },
    ]
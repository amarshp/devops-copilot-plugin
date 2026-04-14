---
name: migrate-job
description: Migrate one Jenkins job to GitLab YAML with validation-ready output.
argument-hint: exact Jenkins job name
agent: "agent"
---

Before starting migration work:

1. Read `DEVOPS_PROJECT_CONTEXT.md` from the repository root.
2. If it is missing or does not clearly define the migration goal, Jenkins/GitLab scope, writable paths, and read-only boundaries, ask focused clarifying questions first.
3. Create or update `DEVOPS_PROJECT_CONTEXT.md` with the clarified migration scope before proceeding.
4. Keep `.github/` read-only unless the user explicitly asked to modify the plugin itself.
5. Treat scripts and commands documented under `.github/skills/` as reference templates; only run them if the current repo proves they are the correct runnable assets here.

Migrate this Jenkins job: ${input:jobName:Exact Jenkins job name}

Optional context:
- Jenkins XML path: ${input:jenkinsXmlPath:Path to XML config (optional)}
- Stage dict path: ${input:stageDictPath:plugin_artifacts/stage_dict.json}
- Output file: ${input:outputFile:migrated_yamls/ci/stages/<job>.yml}

Use these skills:
- [../skills/j2gl-migrate/SKILL.md](../skills/j2gl-migrate/SKILL.md)
- [../skills/runner-inspector/SKILL.md](../skills/runner-inspector/SKILL.md)
- [../skills/j2gl-qc/SKILL.md](../skills/j2gl-qc/SKILL.md)

Required behavior:
1. Preserve exact external job names and boundaries.
2. Validate YAML before any push.
3. If runner path/tool/env is involved, inspect runner first.
4. If pushing, include a specific -m change summary.
5. End with next QC action.

If the exact Jenkins job, XML source, stage mapping, or output location is ambiguous, stop and ask before writing YAML.

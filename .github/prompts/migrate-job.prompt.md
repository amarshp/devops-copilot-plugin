---
name: migrate-job
description: Migrate one Jenkins job to GitLab YAML with validation-ready output.
argument-hint: exact Jenkins job name
agent: "agent"
---

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

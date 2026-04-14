---
name: pipeline-status
description: Check current GitLab pipeline state, monitor hierarchy, and fetch logs.
argument-hint: pipeline id or latest
agent: "agent"
---

Before checking pipeline status:

1. Read `DEVOPS_PROJECT_CONTEXT.md` from the repository root.
2. If the file is missing or does not clearly define the monitoring use case, CI platform, in-scope project, and read-only boundaries, ask concise clarifying questions first.
3. Create or update `DEVOPS_PROJECT_CONTEXT.md` with the clarified monitoring scope before proceeding.
4. Keep `.github/` read-only unless the user explicitly asked to modify the plugin itself.
5. Treat scripts and commands documented under `.github/skills/` as reference templates; only run them if the current repo proves they are the correct runnable assets here.

Check pipeline status for: ${input:pipelineId:latest}

Use:
- [../skills/pipeline-monitor/SKILL.md](../skills/pipeline-monitor/SKILL.md)

Provide:
1. project context summary and monitoring target
2. overall status
3. grouped job counts by state
4. failed/pending jobs
5. exact command for next monitoring step

If the repo does not yet establish which GitLab project or pipeline hierarchy is in scope, stop and ask before monitoring.

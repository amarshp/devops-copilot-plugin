---
name: resume-loop
description: Resume the next safe migration or QC step from current evidence files and pipeline state.
argument-hint: optional focus job or subtree
agent: "agent"
---

Before resuming the loop:

1. Read `DEVOPS_PROJECT_CONTEXT.md` from the repository root.
2. If it is missing or does not clearly define the current migration/QC objective, evidence scope, and read-only boundaries, ask focused clarifying questions first.
3. Create or update `DEVOPS_PROJECT_CONTEXT.md` with the clarified resume scope before proceeding.
4. Keep `.github/` read-only unless the user explicitly asked to modify the plugin itself.
5. Treat scripts and commands documented under `.github/skills/` as reference templates; only run them if the current repo proves they are the correct runnable assets here.

Resume migration loop.
Scope: ${input:focus:optional job/subtree}

Use:
- [../skills/j2gl-migrate/SKILL.md](../skills/j2gl-migrate/SKILL.md)
- [../skills/j2gl-qc/SKILL.md](../skills/j2gl-qc/SKILL.md)
- [../skills/pipeline-monitor/SKILL.md](../skills/pipeline-monitor/SKILL.md)

Produce:
1. project context summary and resume scope
2. current state bullets
3. next runnable step or explicit blocker
4. exact commands to run next
5. evidence files to update after run

If the current loop state cannot be derived from repo evidence, stop and ask before resuming.

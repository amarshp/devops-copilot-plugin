---
name: resume-loop
description: Resume the next safe migration or QC step from current evidence files and pipeline state.
argument-hint: optional focus job or subtree
agent: "agent"
---

Resume migration loop.
Scope: ${input:focus:optional job/subtree}

Use:
- [../skills/j2gl-migrate/SKILL.md](../skills/j2gl-migrate/SKILL.md)
- [../skills/j2gl-qc/SKILL.md](../skills/j2gl-qc/SKILL.md)
- [../skills/pipeline-monitor/SKILL.md](../skills/pipeline-monitor/SKILL.md)

Produce:
1. current state bullets
2. next runnable step or explicit blocker
3. exact commands to run next
4. evidence files to update after run

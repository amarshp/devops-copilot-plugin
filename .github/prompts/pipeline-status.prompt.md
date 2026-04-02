---
name: pipeline-status
description: Check current GitLab pipeline state, monitor hierarchy, and fetch logs.
argument-hint: pipeline id or latest
agent: "agent"
---

Check pipeline status for: ${input:pipelineId:latest}

Use:
- [../skills/pipeline-monitor/SKILL.md](../skills/pipeline-monitor/SKILL.md)

Provide:
1. overall status
2. grouped job counts by state
3. failed/pending jobs
4. exact command for next monitoring step

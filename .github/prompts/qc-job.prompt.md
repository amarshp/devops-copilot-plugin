---
name: qc-job
description: Produce a QC decision for one migrated job using Jenkins and GitLab evidence.
argument-hint: local job name and relevant log paths
agent: "agent"
---

Review one migrated job using plugin QC rules.

Inputs:
- Local job name: ${input:jobName:Local GitLab job name}
- Jenkins job name: ${input:jenkinsJobName:Exact Jenkins job name}
- Jenkins log path: ${input:jenkinsLogPath:Path to the Jenkins log file}
- GitLab log path: ${input:gitlabLogPath:Path to the GitLab log file}
- Mapping notes: ${input:mappingNotes:Short explanation of how the jobs map}

Use:
- [../skills/j2gl-qc/SKILL.md](../skills/j2gl-qc/SKILL.md)

Output format:
1. First line: QC_STATUS: SUCCESS, QC_STATUS: FAIL, or QC_STATUS: BLOCKED.
2. Findings ordered by severity.
3. Short verdict on qc-pass eligibility.
4. Exact status update actions.

Do not treat infrastructure or permission blockers as functional success.

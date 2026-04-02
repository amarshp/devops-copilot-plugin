---
name: setup-project
description: Initialize DevOps plugin by collecting credentials and validating connectivity to Jenkins, GitLab, or both — only the platforms your project uses.
argument-hint: ci platform focus (jenkins, gitlab, both)
agent: "agent"
---

Initialize plugin setup for: ${input:ciPlatform:both}

Run setup workflow using:
- [../skills/devops-setup/SKILL.md](../skills/devops-setup/SKILL.md)

Required output:
1. .env values collected
2. connection-test results
3. missing permissions/tokens if any
4. exact next command to proceed

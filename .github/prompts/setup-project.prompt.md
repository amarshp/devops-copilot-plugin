---
name: setup-project
description: Initialize DevOps plugin by collecting credentials and validating connectivity to Jenkins, GitLab, or both — only the platforms your project uses.
argument-hint: ci platform focus (jenkins, gitlab, both)
agent: "agent"
---

Before doing setup work:

1. Read `DEVOPS_PROJECT_CONTEXT.md` from the repository root.
2. If it is missing or does not clearly define the user's use case and CI platforms, ask concise clarifying questions first. Only ask about specific paths if the repo already has multiple visible pipeline areas to choose between — do not ask about paths or read-only constraints generically. `.github/` is always read-only by default.
3. Create or update `DEVOPS_PROJECT_CONTEXT.md` with the clarified setup scope before proceeding.
4. Keep `.github/` read-only unless the user explicitly asked to modify the plugin itself.
5. Treat scripts and commands documented under `.github/skills/` as reference templates; only run them if the current repo proves they are the correct runnable assets here.

Initialize plugin setup for: ${input:ciPlatform:both}

Run setup workflow using:
- [../skills/devops-setup/SKILL.md](../skills/devops-setup/SKILL.md)

Required output:
1. project context summary and setup scope
1. .env values collected
2. connection-test results
3. missing permissions/tokens if any
4. exact next command to proceed

---
name: yaml-conventions
description: Rules for CI YAML editing, include composition, job isolation, and lint validation.
applyTo: "**/*.{yml,yaml}"
---

# YAML Conventions

- Preserve UTF-8 without BOM.
- Use forward slashes in GitLab include paths.
- Validate changed YAML before push or trigger.
- Keep parent and downstream jobs isolated across files.
- Preserve exact job names that are externally referenced by needs.
- Do not add allow_failure: true as a default migration strategy.
- For skip-ahead decoupling, mark cross-phase needs as optional: true where required.
- Prefer minimal root-cause fixes over broad refactors.

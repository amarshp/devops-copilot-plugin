---
name: runner-inspector
description: 'Inspect remote CI runners (WinRM or SSH) to verify real paths, tools, and environment variables before editing pipeline YAML. Use when: path not found, tool missing, env var incorrect, drive letter uncertainty, network share unavailable, before adding tool paths to YAML.'
argument-hint: 'describe the path/tool/env to inspect'
---

# Runner Inspector

Read-only remote inspection of CI build runners. Verify actual machine state before changing YAML to avoid guessing. Supports both Windows (WinRM) and Linux (SSH) runners — auto-detected from `RUNNER_PROTOCOL` in `.env`.

## Project Context And Execution Model
- Read `DEVOPS_PROJECT_CONTEXT.md` before running this skill.
- If the file is missing or does not define the inspection goal, runner scope, and read-only boundaries, ask clarifying questions first and update it.
- Keep `.github/` read-only during normal plugin usage unless the user explicitly asked to modify the plugin itself.
- Commands and scripts under `.github/skills/` are reference implementations and templates. Only run them if this repo proves they are the correct runnable assets here.
- If the repo needs custom inspection automation, create or adapt project-local scripts outside `.github/`.

## When to Use
- GitLab job fails with "path not found" or "tool not found"
- Environment variable missing or has wrong value
- Network share or drive letter uncertain
- Before adding hard-coded paths to YAML (always verify first)
- Checking what software is installed on the runner

## Prerequisites
- `RUNNER_HOST`, `RUNNER_USER`, `RUNNER_PASS`, `RUNNER_PROTOCOL` set in `.env`
- Reference environment setup pattern: `pip install -r .github/requirements.txt`

## Commands

All commands use the unified `inspector.py` which auto-selects WinRM or SSH:

Treat these as reference commands. Verify that the current repo uses this runner-inspection entry point before executing it unchanged.

```powershell
# Check if a path exists
python .github/skills/runner-inspector/scripts/inspector.py --exists "C:\Jenkins\workspace"

# Find a tool on PATH
python .github/skills/runner-inspector/scripts/inspector.py --cmd "where python"

# Get an environment variable
python .github/skills/runner-inspector/scripts/inspector.py --env WORKSPACE_HOME

# List a directory
python .github/skills/runner-inspector/scripts/inspector.py --path "C:\Jenkins"

# Find files matching a pattern
python .github/skills/runner-inspector/scripts/inspector.py --find "C:\" "*.log"

# Run an arbitrary command
python .github/skills/runner-inspector/scripts/inspector.py --cmd "Get-Process"
```

## Interpretation Rules
- **Path does not exist** → YAML fix cannot reference that path; it is an infrastructure blocker, not a YAML bug
- **Tool not on PATH** → add explicit full path in YAML (after verifying the full path with `--find`), OR record as external blocker if not installed
- **Env var missing** → verify the correct variable name first; if the variable genuinely isn't set, it's an infrastructure blocker
- **Network share not accessible** → record as external blocker; do not paper over with `allow_failure: true`

## Safety Rules
- NEVER write, create, or delete files on the remote runner through this tool
- Use only for observation — any changes to runner state require human intervention via the proper channel
- If runner is unreachable → check `RUNNER_HOST`, `RUNNER_PORT`, network/firewall rules

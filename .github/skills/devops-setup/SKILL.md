---
name: devops-setup
description: 'Set up the DevOps Copilot Plugin for a new project. Use when: initializing credentials, testing connections to Jenkins or GitLab, creating .env, fetching Jenkins job XML configs and build logs, fetching GitLab CI files and project variables. First step before any other skill.'
argument-hint: 'Describe what to set up: "initialize project", "fetch Jenkins configs", "fetch GitLab YAML"'
---

# DevOps Setup

The entry point for every new project. Run this first — all other skills depend on the `.env` credentials written here.

## When to Use
- Starting on a new project (first-time setup)
- Adding Jenkins or runner credentials after initial setup
- Fetching the Jenkins pipeline XML configs for migration analysis
- Fetching the GitLab CI file tree and project variables
- Testing that all connections work after a credential rotation

## Prerequisites
```
pip install -r .github/requirements.txt
```

## Procedure

### Step 1: Create / Update .env
Run the interactive wizard. It tests every connection and writes `.env` to the project root.

```powershell
python .github/skills/devops-setup/scripts/setup_wizard.py
```

To test an existing `.env` without re-prompting:
```powershell
python .github/skills/devops-setup/scripts/setup_wizard.py --check
```

The wizard collects:
| Key | Purpose |
|-----|---------|
| `GITLAB_URL` | Base URL of your GitLab instance |
| `GITLAB_TOKEN` | Personal access token (`api` scope) |
| `GITLAB_PROJECT_ID` | Numeric ID or `namespace/project` |
| `GITLAB_BRANCH` | Branch to push to / trigger pipelines on |
| `JENKINS_ROOT_URL` | Root pipeline job URL (base URL is auto-derived from this) |
| `JENKINS_USER` / `JENKINS_TOKEN` | Jenkins credentials |
| `RUNNER_HOST` | Build runner IP or hostname |
| `RUNNER_USER` / `RUNNER_PASS` | Runner credentials |
| `RUNNER_PORT` | 5985 (WinRM) or 22 (SSH) |
| `RUNNER_PROTOCOL` | `winrm` or `ssh` |
| `COPILOT_TOKEN` | GitHub Copilot API token (`ghp_…`) |
| `COPILOT_MODEL` | LLM model name (default: `claude-sonnet-4.6`) |

### Steps 2–3: Automatic post-setup fetches
After all connections pass, the wizard **automatically** runs:
- **Jenkins config fetch** (if `JENKINS_ROOT_URL` is set) — BFS-crawls Jenkins from the root job, downloads every `config.xml`, and writes:
  - `fetch_xml/config_xml/` — one XML per job
  - `fetch_xml/jenkins_graph_xml.json` — job registry
  - `fetch_xml/levels_xml.txt` — jobs by BFS depth
- **GitLab CI snapshot** (if GitLab credentials are set) — downloads `.gitlab-ci.yml`, all includes, variables, and runners to `gitlab_config/`

No manual action required. If a fetch fails, re-run it individually:

```powershell
# Jenkins configs only
python .github/skills/devops-setup/scripts/fetch_jenkins_configs.py

# GitLab snapshot only
python .github/skills/devops-setup/scripts/fetch_gitlab_config.py --output-dir gitlab_config
```

### Step 4: Fetch Jenkins Build Logs (optional)
Download the last successful console log for each discovered job.

```powershell
python .github/skills/devops-setup/scripts/fetch_jenkins_logs.py
# With options:
python .github/skills/devops-setup/scripts/fetch_jenkins_logs.py --registry fetch_xml/jenkins_graph_xml.json --output-dir fetch_xml/build_logs --limit 50
```

Output:
- `build_logs/` — `.log` file per job
- `build_logs/manifest.json` — download status per job

## Stop Conditions
- HTTP 401 / 403 from Jenkins or GitLab → check token scopes and permissions
- WinRM / SSH connection refused → verify `RUNNER_HOST`, `RUNNER_PORT`, firewall rules
- `COPILOT_TOKEN` rejected → token may have expired; generate a new one
- `ModuleNotFoundError: No module named 'tree'` → `tree.py` is required alongside the scripts folder; verify `skills/devops-setup/tree.py` exists
- Unicode print errors on Windows → scripts use `→` characters; run with `py -W ignore` or set `PYTHONUTF8=1`
- `COPILOT_MODEL` not set or invalid → add `COPILOT_MODEL=claude-sonnet-4.6` to `.env` (use `py` to query `/models` endpoint if unsure)

## Output Shape
After this skill completes, the project root has a `.env` and the working directory has fetched evidence files ready for [pipeline-explorer](../pipeline-explorer/SKILL.md), [j2gl-migrate](../j2gl-migrate/SKILL.md), and [pipeline-monitor](../pipeline-monitor/SKILL.md).

---
name: devops-setup
description: 'Set up the DevOps Copilot Plugin for a new project. Use when: initializing credentials, testing connections to Jenkins or GitLab, creating .env, fetching Jenkins job XML configs and build logs, fetching GitLab CI files and project variables. First step before any other skill.'
argument-hint: 'Describe what to set up: "initialize project", "fetch Jenkins configs", "fetch GitLab YAML"'
---

# DevOps Setup

Use this after the repo's use case is established in `DEVOPS_PROJECT_CONTEXT.md`. All other external-platform skills depend on the `.env` credentials written here.

## Project Context And Execution Model
- Read `DEVOPS_PROJECT_CONTEXT.md` before running this skill.
- If the file is missing or does not define the setup goal, CI platforms in scope, and read-only boundaries, ask clarifying questions first and update it.
- Keep `.github/` read-only during normal plugin usage unless the user explicitly asked to modify the plugin itself.
- Commands and scripts under `.github/skills/` are reference implementations and templates. Only run them if this repo proves they are the correct runnable assets here.
- If the current repo needs custom automation, create or adapt project-local scripts outside `.github/`.

## When to Use
- Starting on a new project (first-time setup)
- Adding Jenkins or runner credentials after initial setup
- Fetching the Jenkins pipeline XML configs for migration analysis
- Fetching the GitLab CI file tree and project variables
- Testing that all connections work after a credential rotation

## Prerequisites
Reference environment setup pattern:
```
pip install -r .github/requirements.txt
```

## Procedure

### Step 0: Check Current Status (always run first)
See what is already done before re-running anything:

Treat this as a reference command. Do not assume the plugin's bundled status script is the right runnable asset unless this repo actually uses it.

```powershell
uv run python .github/skills/devops-setup/scripts/status_check.py
```

Flags:
- `--no-menu` — print the status table and exit (no interactive prompt)
- `--json` — machine-readable output for scripting
- `--root PATH` — override the project root if auto-detection fails

Steps already marked `[+]` are complete and should not be re-run.  
Steps marked `[~]` (partial) or `[ ]` (missing) need attention.

### Step 1: Create / Update .env
Run the interactive wizard. It tests every connection and writes `.env` to the project root.  
Post-setup fetches (Jenkins XMLs, GitLab snapshot) are **automatically skipped** if their output already exists.

Treat these commands as reference patterns. If the repo has project-local setup automation, prefer that over blindly running the plugin copies.

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
| `COPILOT_TOKEN` | GitHub Copilot / GitHub OAuth access token (`gho_…` or `ghp_…`) |
| `COPILOT_MODEL` | LLM model name (default: `claude-sonnet-4.6`) |

### If you do not already have `COPILOT_TOKEN`
If your environment uses the VS Code GitHub device flow for Copilot access, use the following reference steps to obtain an OAuth token.

Do not paste the token into source-controlled files. Store it only in `.env` as `COPILOT_TOKEN=<token>`.

1. Open PowerShell and request a device code:

```powershell
curl -X POST https://github.com/login/device/code -H "Accept: application/json" -d "client_id=01ab8ac9400c4e429b23&scope=user:email"
```

Expected response shape:

```json
{"device_code":"<device_code>","user_code":"<user_code>","verification_uri":"https://github.com/login/device","expires_in":899,"interval":5}
```

2. Open the `verification_uri` from the response:

```text
https://github.com/login/device
```

3. Enter the returned `user_code` and authorize the request in GitHub.

4. Exchange the `device_code` for an access token:

```powershell
curl -X POST https://github.com/login/oauth/access_token -H "Accept: application/json" -d "client_id=01ab8ac9400c4e429b23&device_code=<DEVICE_CODE_FROM_STEP_1>&grant_type=urn:ietf:params:oauth:grant-type:device_code"
```

Expected response shape:

```json
{"access_token":"<oauth_access_token>","token_type":"bearer","scope":"user:email"}
```

5. Copy the returned `access_token` value into your repo-root `.env` file:

```text
COPILOT_TOKEN=<oauth_access_token>
```

6. Re-run the setup wizard or the setup check to validate the token.

### Steps 2–3: Automatic post-setup fetches
After all connections pass, the wizard **automatically** runs:
- **Jenkins config fetch** (if `JENKINS_ROOT_URL` is set) — BFS-crawls Jenkins from the root job, downloads every `config.xml`, and writes:
  - `fetch_xml/config_xml/` — one XML per job
  - `fetch_xml/jenkins_graph_xml.json` — job registry
  - `fetch_xml/levels_xml.txt` — jobs by BFS depth
- **GitLab CI snapshot** (if GitLab credentials are set) — downloads `.gitlab-ci.yml`, all includes, variables, and runners to `gitlab_config/`

No manual action required. If a fetch fails, re-run it individually:

These are reference commands; verify they are the correct runnable assets for the current repo before executing them unchanged.

```powershell
# Jenkins configs only
python .github/skills/devops-setup/scripts/fetch_jenkins_configs.py

# GitLab snapshot only
python .github/skills/devops-setup/scripts/fetch_gitlab_config.py --output-dir gitlab_config
```

### Step 4: Fetch Jenkins Build Logs (optional)
Download the last successful console log for each discovered job.

Treat this as a reference command. Use or adapt it only if the current repo has adopted the plugin's fetch flow.

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
- `COPILOT_TOKEN` rejected → token may have expired or been copied incorrectly; generate a new one using the device-flow steps above
- `ModuleNotFoundError: No module named 'tree'` → `tree.py` is required alongside the scripts folder; verify `skills/devops-setup/tree.py` exists
- Unicode print errors on Windows → scripts use `→` characters; run with `py -W ignore` or set `PYTHONUTF8=1`
- `COPILOT_MODEL` not set or invalid → add `COPILOT_MODEL=claude-sonnet-4.6` to `.env` (use `py` to query `/models` endpoint if unsure)

## Output Shape
After this skill completes, the project root has a `.env` and the working directory has fetched evidence files ready for [pipeline-explorer](../pipeline-explorer/SKILL.md), [j2gl-migrate](../j2gl-migrate/SKILL.md), and [pipeline-monitor](../pipeline-monitor/SKILL.md).

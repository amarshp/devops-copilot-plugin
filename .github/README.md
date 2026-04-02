# DevOps Copilot Plugin

A general-purpose DevOps assistant built as reusable Copilot workspace customizations. Not just a migration tool — it covers four pillars of CI/CD work: **Setup & Debug**, **Understand**, **Migrate**, and **Optimize**.

## Four Pillars

| # | Pillar | What it does | Key skills |
|---|--------|-------------|------------|
| 1 | **Setup & Debug** | Connect to GitLab, Jenkins, or both. Browse logs, inspect runners, diagnose failures. | `devops-setup`, `runner-inspector`, `pipeline-monitor` |
| 2 | **Understand the Pipeline** | Graph any Jenkins or GitLab pipeline, generate diagrams, find bottlenecks. No migration needed. | `pipeline-explorer` |
| 3 | **Migrate (Jenkins → GitLab)** | Self-healing loop: plan → convert → validate → push → run → QC → fix → repeat. Retries on failures, resumes from interruptions. | `j2gl-migrate`, `j2gl-qc` |
| 4 | **Optimize Existing Pipelines** | Decouple, parallelize, improve caching, remove bottlenecks in GitLab CI/CD. | `pipeline-decoupler` |

## What Is Included

- `copilot-instructions.md` — workspace-wide operating rules, four-pillar scope, and HITL stop conditions
- `agents/` — focused DevOps personas with scoped HITL enforcement
- `prompts/` — slash commands for setup, exploration, migration, QC, monitoring, resume, and welcome
- `skills/` — workflow bundles with Python scripts
- `hooks/` — pre-push YAML validation guard

## Quick Start

### 1. Install dependencies
```powershell
py -m pip install -r .github/requirements.txt
```

### 2. Run the setup wizard
Connects to **GitLab**, **Jenkins**, or **both** — only fill in the credentials you need.
```powershell
py .github/skills/devops-setup/scripts/setup_wizard.py
```

To validate an existing `.env` without re-prompting:
```powershell
py .github/skills/devops-setup/scripts/setup_wizard.py --check
```

### 3. Fetch evidence (only the sources you use)
```powershell
# Jenkins (skip if you only use GitLab):
py .github/skills/devops-setup/scripts/fetch_jenkins_configs.py
py .github/skills/devops-setup/scripts/fetch_jenkins_logs.py --registry fetch_xml/jenkins_graph_xml.json --output-dir fetch_xml/build_logs --limit 50

# GitLab (skip if you only use Jenkins):
py -W ignore .github/skills/devops-setup/scripts/fetch_gitlab_config.py
```

### 4. Open Copilot Chat and start
```
/start-plugin
```
This is the welcome entry point — explains all commands in plain language and routes you to the right next step.

## Slash Commands

| Command | Pillar | What it does |
|---------|--------|-------------|
| `/start-plugin` | — | Welcome guide — explains the plugin for first-time users, checks setup status |
| `/setup-project` | 1 Setup | Initialize credentials and test all connections (GitLab, Jenkins, or both) |
| `/explore-pipeline` | 2 Understand | Graph and summarize Jenkins or GitLab pipeline |
| `/pipeline-status` | 1 Setup | Poll latest pipeline run, download logs, diagnose failures |
| `/migrate-job` | 3 Migrate | Convert a Jenkins job to GitLab CI YAML |
| `/qc-job` | 3 Migrate | Compare Jenkins vs GitLab evidence, produce QC report |
| `/resume-loop` | 3 Migrate | Resume an interrupted migration or QC workflow |

## Custom Agents (agent picker)

Use the `@` agent picker in Copilot Chat.

| Agent | Pillar | Scope | Use for |
|-------|--------|-------|---------|
| `migration-planner` | 3 Migrate | Read-only | Ordered migration plan, blocker identification |
| `migration-implementer` | 3 Migrate | Write + execute | YAML authoring, script execution, push |
| `qc-reviewer` | 3 Migrate | Read-only | Jenkins vs GitLab log comparison, QC verdict |
| `pipeline-optimizer` | 4 Optimize | Write + execute | Parallelization, decoupling, cache strategy |

All agents enforce **HITL stop conditions** — they halt and ask for human input the moment they encounter an out-of-scope action, auth failure, missing artifact, or destructive operation.

## Recommended Workflows

### Any project (Pillar 1 + 2)
```
1. /start-plugin          → Welcome, status check
2. /setup-project         → Credentials + connectivity (GitLab, Jenkins, or both)
3. /explore-pipeline      → Graph + summary + bottlenecks
4. /pipeline-status       → Monitor current pipeline, download logs
```

### Migration project (adds Pillar 3)
```
5. fetch_jenkins_configs  → Download all job XMLs
6. fetch_jenkins_logs     → Download build logs
7. migration-planner      → Ordered plan (bottom-up, blockers flagged)
8. /migrate-job           → Convert one job at a time
9. /qc-job                → QC each migrated job
10. MIGRATION_STATUS.md   → Auto-updated after every push + QC run
```

### Optimization (Pillar 4)
```
11. pipeline-optimizer    → Analyze + decouple + parallelize existing GitLab CI
```

## Project-Root Files Created by the Plugin

| File / Folder | Created by | Contents |
|---------------|-----------|---------|
| `.env` | `setup_wizard.py` | Credentials and connection settings |
| `fetch_xml/` | `fetch_jenkins_configs.py` | Job registry, config XMLs, pipeline tree |
| `fetch_xml/build_logs/` | `fetch_jenkins_logs.py` | Jenkins build logs per job |
| `gitlab_config/` | `fetch_gitlab_config.py` | GitLab CI YAML snapshot, runners, variables |
| `plugin_artifacts/` | `pipeline-explorer` scripts | Dependency graphs, diagrams, summary |
| `migrated_yamls/` | `migration-implementer` / `/migrate-job` | Generated GitLab CI YAML files |
| `pipeline_logs/` | `qc_bulk_download.py` | GitLab job logs per pipeline run |
| `qc_reports/` | `qc_compare_logs.py` | Per-job QC reports with status + fixes |
| `QC_RUN_HISTORY.md` | `qc_status_tracker.py` | Timestamped QC event log |
| `MIGRATION_STATUS.md` | `migration_dashboard.py` | Live dashboard: tree, scoreboard, run log |

## HITL — Human-In-The-Loop Safety

Every agent and prompt in this plugin will **stop and ask before proceeding** when it encounters:
- Auth failures (HTTP 401 / 403)
- Missing `.env` keys
- Jenkins jobs not found on the server
- Missing runner tags
- YAML lint failures after 3 retries
- Missing `needs:` job references
- Destructive git operations
- Circular dependency cycles
- Out-of-scope requests (e.g. asking a read-only agent to write files)

Stop format used by all agents:
```
⛔ STOP — Human input required
Reason: …
What I need: …
How to get it: …
Next step after you provide it: …
```

## Verification Checklist

```powershell
py .github/skills/devops-setup/scripts/setup_wizard.py --check
py -W ignore .github/skills/pipeline-explorer/scripts/gitlab_graph.py --ci gitlab_config/gitlab-ci.yml --output plugin_artifacts/gitlab_graph.json
py -W ignore .github/skills/j2gl-qc/scripts/qc_bulk_download.py --latest
py -W ignore .github/skills/j2gl-qc/scripts/migration_dashboard.py
```

## Notes

- Use `py` (Python Launcher) on Windows; on Linux/macOS use `python3`.
- `.env` is always gitignored — never commit credentials.
- `tree.py` (in `skills/devops-setup/`) is required by `fetch_jenkins_configs.py` — do not remove it.
- YAML files must be UTF-8 without BOM.
- The pre-push hook validates staged YAML through `validate_yaml.py` before any push operation.
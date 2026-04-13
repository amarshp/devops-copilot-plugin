# DevOps Copilot Plugin — Internal Reference

This file is for plugin developers and Copilot itself. It describes how all the layers work, how routing decisions are made, and what safety rules apply.

For the user-facing guide, see [README.md](README.md).

---

## How Each Layer is Triggered

| Layer | Triggered by | User needs to know? |
|---|---|---|
| `copilot-instructions.md` | Always loaded automatically | No |
| `instructions/` | Auto-applied to matching files via `applyTo` pattern | No |
| `hooks/` | Git lifecycle events (e.g. pre-push) | No |
| `skills/` | Copilot, based on detected user intent | No |
| `prompts/` | Copilot via intent routing; optionally via `/command` shortcut | No — `/command` is optional |
| `agents/` | **Must be explicitly invoked** via `@agent-name` — never auto-triggered | Only when hard safety boundaries are needed |

### Prompts vs Skills — Parallel Paths

Prompts and skills are **not** a call chain. They are two doors into the same room:

```
User types anything
        │
        ▼
copilot-instructions.md (always loaded)
        │
        ├─ intent routing → skill SKILL.md procedure followed directly
        │
        └─ /command typed → prompt file loaded → same workflow steps

@agent-name typed explicitly
        │
        ▼
Agent mode activated (hard permissions enforced)
        └─ follows its own skill procedure with scoped HITL
```

A prompt file does not call a skill file. The prompt describes the same workflow steps the skill would follow — they are kept in sync by convention, not by code.

### Why Keep Both?

| | Value |
|---|---|
| `skills/` | Single source of truth for workflow logic; used by both paths |
| `prompts/` | Versioned, slash-invokable entry point; ensures consistent step order; discoverable via `/` menu |
| `agents/` | Hard permission boundaries (read-only vs write); stricter HITL that plain instructions cannot structurally enforce |

---

## Intent Routing Table

When a user describes their goal, Copilot matches it to the right skill using this table from `copilot-instructions.md`:

| If the user says anything like… | Automatically follow | Notes |
|---|---|---|
| set up, connect, credentials, `.env`, Jenkins URL, GitLab token, test connection | `devops-setup` skill | Run setup wizard flow |
| show me the pipeline, explain the pipeline, graph, diagram, bottlenecks | `pipeline-explorer` skill | Works on Jenkins XML or GitLab CI YAML |
| monitor, check status, latest run, pipeline failed, download logs, what went wrong | `pipeline-monitor` skill | Fetch + diagnose latest pipeline |
| inspect runners, what runners do we have, runner tags, runner capacity | `runner-inspector` skill | Read-only |
| migrate, convert Jenkins job, Jenkins to GitLab, write the YAML for this job | `j2gl-migrate` skill → `migration-implementer` agent | Confirm job name first if ambiguous |
| QC, quality check, compare Jenkins vs GitLab, did the migration pass | `j2gl-qc` skill → `qc-reviewer` agent | Read-only; never edits files |
| resume, pick up where we left off, migration was interrupted | `j2gl-migrate` skill, resume-loop procedure | Check `MIGRATION_STATUS.md` first |
| optimize, parallelize, decouple, speed up pipeline, reduce rerun time | `pipeline-decoupler` skill → `pipeline-optimizer` agent | |
| fast pipeline, skip compilation, resume from phase | `pipeline-phase-resumer` skill → `phase-resumer` agent | Ask for reference build number if not provided |

**Routing rules:**
- Match intent, not exact wording.
- If intent is ambiguous between two pillars, ask one clarifying question before proceeding.
- Skills, agents, hooks, and instructions all run in the background. The user never needs to name them.

---

## Journey Awareness

Beyond intent routing, Copilot must also guide users who don't know the full process. This behaviour is defined in `copilot-instructions.md` and applies to every interaction.

### Onboarding detection
If the user's first message is vague or exploratory (e.g. "where do I start", "help me with CI/CD", "I want to move to GitLab"), do **not** jump into a skill. Instead:
1. Give a two-sentence plain-language summary of what the plugin does.
2. Ask one question to identify their goal: migrate, understand/debug, or optimize.
3. Show them the full ordered journey for that goal and ask which step to start from.

### Setup gate
Before any skill that calls GitLab or Jenkins APIs, check that `.env` exists and has the required keys. If not, run setup first, then resume the original task automatically.

### Post-step nudges
After every major step (setup, fetch, plan, migrate a job, QC a job, optimize), always end with:
- One-line summary of what was just accomplished
- The logical next step
- An offer to proceed: "Ready to move to [next step]? Just say yes."

Never end a step silently.

### Journey maps

**Migrate from Jenkins to GitLab:**
Setup → Fetch configs/logs → Plan → Migrate (per-job loop) → QC → Dashboard

**Understand or debug:**
Setup → Explore → Monitor

**Optimize existing GitLab pipeline:**
Setup → Explore → Optimize → (optional) Fast resume

---

## Directory Layout

```text
.github/
├─ README.md                        ← user-facing guide
├─ PLUGIN_REFERENCE.md              ← this file
├─ requirements.txt
├─ copilot-instructions.md          ← always loaded; intent routing + core rules
├─ agents/
│  ├─ migration-implementer.agent.md
│  ├─ migration-planner.agent.md
│  ├─ phase-resumer.agent.md
│  ├─ pipeline-optimizer.agent.md
│  └─ qc-reviewer.agent.md
├─ prompts/
│  ├─ explore-pipeline.prompt.md
│  ├─ migrate-job.prompt.md
│  ├─ pipeline-status.prompt.md
│  ├─ qc-job.prompt.md
│  ├─ resume-loop.prompt.md
│  ├─ setup-project.prompt.md
│  └─ start-plugin.prompt.md
├─ skills/
│  ├─ devops-setup/
│  ├─ j2gl-migrate/
│  ├─ j2gl-qc/
│  ├─ pipeline-decoupler/
│  ├─ pipeline-explorer/
│  ├─ pipeline-monitor/
│  ├─ pipeline-phase-resumer/
│  └─ runner-inspector/
├─ instructions/
│  ├─ config-security.instructions.md
│  └─ yaml-conventions.instructions.md
└─ hooks/
   ├─ pre-push-validate.json
   └─ pre_push_validate.py
```

---

## Project-Root Files Created by the Plugin

| File / Folder | Created by | Contents |
|---|---|---|
| `.env` | `setup_wizard.py` | Credentials and connection settings |
| `fetch_xml/` | `fetch_jenkins_configs.py` | Job registry, config XMLs, pipeline tree |
| `fetch_xml/build_logs/` | `fetch_jenkins_logs.py` | Jenkins build logs per job |
| `gitlab_config/` | `fetch_gitlab_config.py` | GitLab CI YAML snapshot, runners, variables |
| `plugin_artifacts/` | `pipeline-explorer` scripts | Dependency graphs, diagrams, summary |
| `migrated_yamls/` | `migration-implementer` | Generated GitLab CI YAML files |
| `pipeline_logs/` | `qc_bulk_download.py` | GitLab job logs per pipeline run |
| `qc_excerpts/` | `log_excerpt.py` | Per-job signal excerpts fed to LLM |
| `qc_reports/` | `qc_compare_logs.py` | Per-job QC reports with status + fixes |
| `QC_RUN_HISTORY.md` | `qc_status_tracker.py` | Timestamped QC event log |
| `MIGRATION_STATUS.md` | `migration_dashboard.py` | Live dashboard: tree, scoreboard, run log |

---

## HITL — Human-In-The-Loop Stop Conditions

Every agent and prompt MUST stop immediately and ask the human when it encounters:

- HTTP 401 / 403 from Jenkins or GitLab — do not retry or assume credentials are cached
- A required `.env` key is missing or empty — list exactly which keys are needed
- A Jenkins job referenced in a migration plan is not found on the server
- A GitLab runner tag required by a job is not present in `runners.json`
- Generated YAML fails lint after 3 retries — show errors, ask for clarification
- A `needs:` reference points to a job not in the current pipeline scope
- Any destructive action (file deletion, git reset, branch force-push)
- Circular dependency detected in the job graph
- QC report cannot be generated because Jenkins reference log is unavailable
- Agent is asked to act outside its defined scope

**Stop format:**
```
⛔ STOP — Human input required

Reason: <one sentence>
What I need: <exact list>
How to get it: <concrete steps>
Next step after you provide it: <what happens next>
```

---

## Core Rules

- Start with `devops-setup` before running any other skill.
- Validate YAML before any push or pipeline trigger.
- Keep job boundaries isolated across files; do not duplicate downstream job implementations.
- Preserve exact externally referenced job names for `needs` stability.
- Use UTF-8 without BOM for YAML files.
- Treat runner inspection as read-only.
- A successful pipeline run is not a QC pass. QC pass requires `QC_STATUS: SUCCESS` in the report.
- Do not mask infrastructure blockers with `allow_failure` unless explicitly approved.

---

## Verification Checklist

```powershell
py .github/skills/devops-setup/scripts/setup_wizard.py --check
py -W ignore .github/skills/pipeline-explorer/scripts/gitlab_graph.py --ci gitlab_config/gitlab-ci.yml --output plugin_artifacts/gitlab_graph.json
py -W ignore .github/skills/j2gl-qc/scripts/qc_bulk_download.py --latest
py -W ignore .github/skills/j2gl-qc/scripts/log_excerpt.py --log pipeline_logs/<job>.log --output qc_excerpts/<job>.excerpt.log
py -W ignore .github/skills/j2gl-qc/scripts/migration_dashboard.py
```

---

## Notes

- Use `py` (Python Launcher) on Windows; on Linux/macOS use `python3`.
- `.env` is always gitignored — never commit credentials.
- `tree.py` (in `skills/devops-setup/`) is required by `fetch_jenkins_configs.py` — do not remove it.
- YAML files must be UTF-8 without BOM.
- The pre-push hook validates staged YAML through `validate_yaml.py` before any push.

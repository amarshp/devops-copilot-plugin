# DevOps Copilot Plugin Workspace Instructions

This workspace hosts a reusable DevOps plugin under `.github/` with agents, prompts, skills, tools, and hooks. It is a general-purpose **DevOps assistant** built around four pillars — not just a migration tool.

## Four Pillars

### 1. Setup & Debug
Connect the plugin to **GitLab**, **Jenkins**, or both — whichever your project uses. Once connected you can browse build logs, inspect runners, and use the agent to help diagnose and fix pipeline failures.

Skills: `devops-setup`, `runner-inspector`, `pipeline-monitor`

### 2. Understand the Pipeline
Explore any Jenkins or GitLab pipeline: generate dependency graphs, Mermaid diagrams, phase/bottleneck summaries, and LLM-powered explanations. No migration required — useful for anyone who needs to understand what a pipeline does.

Skills: `pipeline-explorer`

### 3. Migrate (Jenkins → GitLab)
Full-featured Jenkins-to-GitLab migration built as a **self-healing loop**: plan → convert → validate → push → run → QC → diagnose → fix → repeat. Each stage feeds evidence to the next. The LLM retries on lint failures with error context. QC failures produce specific fix instructions the agent acts on. `/resume-loop` picks up from wherever the loop was interrupted. The dashboard tracks state so the agent always knows where it is. HITL stops only fire on genuine blockers (auth, infra) — fixable issues are handled automatically.

Skills: `j2gl-migrate`, `j2gl-qc`

### 4. Optimize Existing Pipelines
Analyze and decouple GitLab CI/CD pipelines for skip-ahead execution, parallelization, cache strategy improvements, and bottleneck removal — independent of any migration.

Skills: `pipeline-decoupler`

## Core Rules

- Start with setup workflow in `.github/skills/devops-setup/` before running any other skill.
- Validate YAML before any push or pipeline trigger.
- Keep job boundaries isolated across files; do not duplicate downstream job implementations.
- Preserve exact externally referenced job names for `needs` stability.
- Use UTF-8 without BOM for YAML files.
- Treat runner inspection as read-only.
- A successful pipeline is not a QC pass by itself.
- QC pass requires explicit report outcome: `QC_STATUS: SUCCESS`.

## Safety And Blockers

- Stop and report external blockers: auth failures, missing secrets, runner infra gaps, inaccessible shares.
- Do not mask infrastructure blockers with `allow_failure` unless explicitly approved.
- Do not run destructive git commands unless explicitly requested.

## Human-In-The-Loop (HITL) — Mandatory Stop Conditions

Any agent or prompt MUST stop immediately and ask the human for input when it encounters any of the following. Do not guess, assume, or work around these situations.

**Always stop and ask when:**
- HTTP 401 / 403 returned from Jenkins or GitLab — do not retry or assume credentials are cached.
- A required `.env` key is missing or empty — list exactly which keys are needed and how to obtain them.
- A Jenkins job referenced in a migration plan is not found on the server — confirm whether it was renamed, decommissioned, or is in a different folder path.
- A GitLab runner tag required by a job is not present in `runners.json` — report the missing tag and ask whether to proceed with a substitute tag or stop.
- Generated YAML fails lint validation after 3 retries — stop, show the lint errors, and ask the human to clarify the job's intended behavior before retrying.
- A `needs:` reference points to a job that does not exist in the current pipeline scope — list the missing jobs and ask whether to stub, remove, or add the dependency.
- Any destructive action is about to run (file deletion, git reset, branch force-push, drop table) — state what will be destroyed and wait for explicit approval.
- The migration planner detects a circular dependency in the job graph — show the cycle and ask which edge to break.
- A QC report cannot be generated because the Jenkins reference log is unavailable — record status as `BLOCKED`, explain what log is needed and where to find it, and stop.
- The agent reaches the boundary of its defined scope (e.g. `migration-planner` is asked to write YAML, `qc-reviewer` is asked to edit files) — state the scope boundary, name the correct agent or prompt to use instead, and stop.

**HITL response format — always use this structure:**
```
⛔ STOP — Human input required

Reason: <one sentence explaining what was encountered>
What I need: <exact list of inputs, files, or decisions needed>
How to get it: <concrete steps the human can take>
Next step after you provide it: <what the agent will do next>
```

## Primitive Usage

- Prompts: one-shot workflows via slash commands
- Agents: multi-turn planning, implementation, review, optimization
- Skills: procedures and scripts invoked by agents/prompts
- Hooks: deterministic enforcement (pre-push validation)

Avoid overlapping entry points for the same task unless explicitly needed.